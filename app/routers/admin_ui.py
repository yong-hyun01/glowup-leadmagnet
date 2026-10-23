"""관리자 화면. 서버 렌더링 페이지 + 작은 fetch 스크립트로 /admin/api 를 호출한다."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_optional_operator
from app.models import Campaign, Form, HtmlTemplate, Lead, Operator
from app.routers.forms import form_out, link_out
from app.services.stats import campaign_metrics, campaign_stats, channel_metrics

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

KST = timezone(timedelta(hours=9))


def _kst(dt: datetime | None) -> str:
    """DB 의 UTC 시각을 한국 시간으로 표시. SQLite 는 naive 로 돌려주므로 UTC 로 간주한다."""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M")


templates.env.filters["kst"] = _kst


def _render(request: Request, name: str, operator: Operator | None, **ctx):
    return templates.TemplateResponse(request, name, {"operator": operator, **ctx})


def _require(request: Request, operator: Operator | None):
    if operator is None:
        return RedirectResponse(url="/admin/login", status_code=302)
    return None


@router.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse(url="/admin", status_code=302)


@router.get("/admin/login", response_class=HTMLResponse)
def login_page(request: Request, operator: Operator | None = Depends(get_optional_operator)):
    if operator:
        return RedirectResponse(url="/admin", status_code=302)
    return _render(request, "login.html", None)


@router.get("/admin", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db), operator: Operator | None = Depends(get_optional_operator)):
    if r := _require(request, operator):
        return r
    campaigns = list(db.scalars(select(Campaign).order_by(Campaign.id.desc())))
    rows = [(c, campaign_metrics(db, c.id)) for c in campaigns]
    return _render(request, "dashboard.html", operator, rows=rows, channels=channel_metrics(db, None))


@router.get("/admin/templates", response_class=HTMLResponse)
def templates_page(request: Request, db: Session = Depends(get_db), operator: Operator | None = Depends(get_optional_operator)):
    if r := _require(request, operator):
        return r
    items = list(db.scalars(select(HtmlTemplate).order_by(HtmlTemplate.id.desc())))
    return _render(request, "templates.html", operator, items=items)


@router.get("/admin/campaigns/{campaign_id}", response_class=HTMLResponse)
def campaign_page(campaign_id: int, request: Request, db: Session = Depends(get_db),
                  operator: Operator | None = Depends(get_optional_operator)):
    if r := _require(request, operator):
        return r
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        return _render(request, "not_found.html", operator)
    forms = [(form_out(f), [link_out(l) for l in f.links]) for f in
             db.scalars(select(Form).where(Form.campaign_id == campaign_id).order_by(Form.id.desc()))]
    tpls = list(db.scalars(select(HtmlTemplate).order_by(HtmlTemplate.id.desc())))
    leads = list(db.scalars(select(Lead).join(Form).where(Form.campaign_id == campaign_id).order_by(Lead.id.desc()).limit(200)))
    form_names = {f.id: f.name for f, _ in forms}
    return _render(request, "campaign.html", operator, campaign=campaign, stats=campaign_stats(db, campaign),
                   forms=forms, tpls=tpls, leads=leads, form_names=form_names,
                   channels=["instagram", "x", "youtube", "threads"])
