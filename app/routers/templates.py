from fastapi import APIRouter, Depends, File, Form as FormField, HTTPException, UploadFile, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_operator
from app.models import HtmlTemplate, Operator
from app.schemas import TemplateOut
from app.services.html import validate_uploaded_html

router = APIRouter(prefix="/admin/api/templates", tags=["templates"], dependencies=[Depends(get_current_operator)])


@router.get("", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db)):
    return list(db.scalars(select(HtmlTemplate).order_by(HtmlTemplate.id.desc())))


@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
async def upload_template(
    file: UploadFile = File(...),
    name: str | None = FormField(default=None),
    db: Session = Depends(get_db),
    operator: Operator = Depends(get_current_operator),
):
    raw = await file.read()
    content = validate_uploaded_html(file.filename or "", raw, get_settings().max_html_bytes)
    tpl = HtmlTemplate(
        operator_id=operator.id,
        name=(name or file.filename or "untitled").strip()[:200],
        original_filename=file.filename or "untitled.html",
        content=content,
        size_bytes=len(raw),
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.get("/{template_id}", response_model=TemplateOut)
def get_template(template_id: int, db: Session = Depends(get_db)):
    tpl = db.get(HtmlTemplate, template_id)
    if tpl is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="템플릿을 찾을 수 없습니다.")
    return tpl


@router.get("/{template_id}/preview", response_class=HTMLResponse)
def preview_template(template_id: int, db: Session = Depends(get_db)):
    """관리자 미리보기. 반드시 sandbox iframe 안에서만 열리도록 CSP 로 강제한다."""
    tpl = db.get(HtmlTemplate, template_id)
    if tpl is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="템플릿을 찾을 수 없습니다.")
    headers = {
        "Content-Security-Policy": "sandbox allow-scripts allow-forms; frame-ancestors 'self'",
        "X-Content-Type-Options": "nosniff",
    }
    return HTMLResponse(tpl.content, headers=headers)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    tpl = db.get(HtmlTemplate, template_id)
    if tpl is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="템플릿을 찾을 수 없습니다.")
    if tpl.forms:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="이 템플릿을 사용하는 폼이 있어 삭제할 수 없습니다.")
    db.delete(tpl)
    db.commit()
