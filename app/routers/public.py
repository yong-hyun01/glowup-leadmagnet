"""공개 영역: 배포 링크 리다이렉트, 공개 폼 셸·프레임, 제출 API.

- /l/{token}      : 채널별 배포 링크 → /f/{slug}?l={token} 로 302
- /f/{slug}       : 셸 페이지. 방문 기록 + visitor 쿠키 발급 + sandbox iframe
- /f/{slug}/frame : 운영자 HTML + 제출 브리지 스크립트 (opaque origin 으로 격리)
- /public/api/forms/{slug}/submissions : 제출 저장 (CRM 명단)
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import DistributionLink, Form, Lead, Visit
from app.schemas import SubmissionIn, SubmissionOut
from app.security import VISITOR_COOKIE
from app.services.html import inject_bridge

router = APIRouter(tags=["public"])

MAX_FIELDS = 50
MAX_VALUE_LEN = 2000
VISITOR_COOKIE_MAX_AGE = 60 * 60 * 24 * 365


def _active_form(db: Session, slug: str) -> Form:
    f = db.scalar(select(Form).where(Form.slug == slug))
    if f is None or not f.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="폼을 찾을 수 없거나 비활성화되었습니다.")
    return f


def _resolve_link(db: Session, form: Form, token: str | None) -> DistributionLink | None:
    if not token:
        return None
    link = db.scalar(select(DistributionLink).where(DistributionLink.token == token))
    return link if link and link.form_id == form.id else None


def _frame_csp() -> str:
    base = get_settings().public_base_url.rstrip("/")
    return (
        "default-src 'none'; "
        "script-src 'unsafe-inline' https:; "
        "style-src 'unsafe-inline' https:; "
        "img-src https: data:; font-src https: data:; media-src https:; "
        f"connect-src 'self' {base}; "
        "form-action 'none'; frame-ancestors 'self'; base-uri 'none'"
    )


@router.get("/l/{token}", include_in_schema=True, summary="배포 링크 리다이렉트")
def follow_link(token: str, db: Session = Depends(get_db)):
    link = db.scalar(select(DistributionLink).where(DistributionLink.token == token))
    if link is None or not link.form.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="링크를 찾을 수 없습니다.")
    return RedirectResponse(url=f"/f/{link.form.slug}?l={token}", status_code=302)


@router.get("/f/{slug}", response_class=HTMLResponse, summary="공개 폼 페이지(셸)")
def public_form_shell(slug: str, request: Request, l: str | None = None, db: Session = Depends(get_db)):
    form = _active_form(db, slug)
    link = _resolve_link(db, form, l)
    channel = link.channel.value if link else "direct"

    visitor_id = request.cookies.get(VISITOR_COOKIE)
    if not visitor_id or len(visitor_id) > 64:
        visitor_id = uuid.uuid4().hex

    db.add(Visit(
        form_id=form.id,
        link_id=link.id if link else None,
        channel=channel,
        visitor_id=visitor_id,
        user_agent=(request.headers.get("user-agent") or "")[:500],
    ))
    db.commit()

    frame_src = f"/f/{slug}/frame?v={visitor_id}" + (f"&l={link.token}" if link else "")
    html = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{form.name}</title>
<style>html,body{{margin:0;height:100%;background:#fff}}iframe{{border:0;width:100%;height:100%;display:block}}</style>
</head><body>
<iframe sandbox="allow-scripts allow-forms" referrerpolicy="no-referrer" src="{frame_src}" title="{form.name}"></iframe>
</body></html>"""
    resp = HTMLResponse(html, headers={
        "Content-Security-Policy": "default-src 'self'; style-src 'unsafe-inline'; frame-src 'self'; object-src 'none'",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
    })
    resp.set_cookie(VISITOR_COOKIE, visitor_id, max_age=VISITOR_COOKIE_MAX_AGE, path="/f", httponly=True, samesite="lax")
    return resp


@router.get("/f/{slug}/frame", response_class=HTMLResponse, summary="공개 폼 프레임(운영자 HTML)")
def public_form_frame(slug: str, v: str = "", l: str | None = None, db: Session = Depends(get_db)):
    form = _active_form(db, slug)
    link = _resolve_link(db, form, l)
    visitor_id = v[:64] if v else ""
    html = inject_bridge(
        form.template.content,
        submit_url=f"{get_settings().public_base_url.rstrip('/')}/public/api/forms/{slug}/submissions",
        link_token=link.token if link else None,
        visitor_id=visitor_id,
    )
    return HTMLResponse(html, headers={
        "Content-Security-Policy": _frame_csp(),
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "no-store",
    })


@router.options("/public/api/forms/{slug}/submissions", include_in_schema=False)
def submit_preflight():
    return Response(status_code=204, headers=_cors_headers())


def _cors_headers() -> dict[str, str]:
    # sandbox iframe 은 origin 이 "null" 이므로 공개 제출 API 는 자격증명 없는 CORS 를 허용한다.
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }


@router.post("/public/api/forms/{slug}/submissions", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED,
             summary="공개 폼 제출")
def submit_form(slug: str, body: SubmissionIn, response: Response, db: Session = Depends(get_db)):
    for k, v in _cors_headers().items():
        response.headers[k] = v
    form = _active_form(db, slug)

    fields = {str(k)[:100]: v for k, v in body.fields.items() if str(k).strip()}
    cleaned = {}
    for k, v in fields.items():
        if isinstance(v, list):
            v = [str(x)[:MAX_VALUE_LEN] for x in v][:20]
        elif v is None:
            continue
        else:
            v = str(v)[:MAX_VALUE_LEN]
        cleaned[k] = v
    if not cleaned or not any((x if isinstance(x, list) else [x]) and str(x).strip() for x in cleaned.values()):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="입력된 내용이 없습니다.")
    if len(cleaned) > MAX_FIELDS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="필드가 너무 많습니다.")

    link = _resolve_link(db, form, body.link_token)
    lead = Lead(
        form_id=form.id,
        link_id=link.id if link else None,
        channel=link.channel.value if link else "direct",
        visitor_id=(body.visitor_id or None),
        data=cleaned,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return SubmissionOut(ok=True, lead_id=lead.id, message=form.success_message)
