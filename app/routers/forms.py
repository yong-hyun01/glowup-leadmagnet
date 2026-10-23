from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_operator
from app.models import Campaign, DistributionLink, Form, HtmlTemplate, Lead
from app.schemas import FormCreate, FormOut, FormUpdate, LeadOut, LinkCreate, LinkOut

router = APIRouter(prefix="/admin/api/forms", tags=["forms"], dependencies=[Depends(get_current_operator)])


def public_url(slug: str) -> str:
    return f"{get_settings().public_base_url.rstrip('/')}/f/{slug}"


def link_url(token: str) -> str:
    return f"{get_settings().public_base_url.rstrip('/')}/l/{token}"


def form_out(f: Form) -> FormOut:
    return FormOut(id=f.id, campaign_id=f.campaign_id, template_id=f.template_id, name=f.name, slug=f.slug,
                   success_message=f.success_message, is_active=f.is_active, created_at=f.created_at,
                   public_url=public_url(f.slug))


def link_out(link: DistributionLink) -> LinkOut:
    return LinkOut(id=link.id, form_id=link.form_id, channel=link.channel, token=link.token,
                   created_at=link.created_at, url=link_url(link.token))


def _get(db: Session, form_id: int) -> Form:
    f = db.get(Form, form_id)
    if f is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="폼을 찾을 수 없습니다.")
    return f


@router.get("", response_model=list[FormOut])
def list_forms(campaign_id: int | None = None, db: Session = Depends(get_db)):
    q = select(Form).order_by(Form.id.desc())
    if campaign_id is not None:
        q = q.where(Form.campaign_id == campaign_id)
    return [form_out(f) for f in db.scalars(q)]


@router.post("", response_model=FormOut, status_code=status.HTTP_201_CREATED)
def create_form(body: FormCreate, db: Session = Depends(get_db)):
    if db.get(Campaign, body.campaign_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="캠페인을 찾을 수 없습니다.")
    if db.get(HtmlTemplate, body.template_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="템플릿을 찾을 수 없습니다.")
    f = Form(campaign_id=body.campaign_id, template_id=body.template_id, name=body.name.strip())
    if body.success_message:
        f.success_message = body.success_message
    db.add(f)
    db.commit()
    db.refresh(f)
    return form_out(f)


@router.get("/{form_id}", response_model=FormOut)
def get_form(form_id: int, db: Session = Depends(get_db)):
    return form_out(_get(db, form_id))


@router.patch("/{form_id}", response_model=FormOut)
def update_form(form_id: int, body: FormUpdate, db: Session = Depends(get_db)):
    f = _get(db, form_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(f, k, v)
    db.commit()
    db.refresh(f)
    return form_out(f)


@router.delete("/{form_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_form(form_id: int, db: Session = Depends(get_db)):
    db.delete(_get(db, form_id))
    db.commit()


# ---- 배포 링크 ---------------------------------------------------------------

@router.get("/{form_id}/links", response_model=list[LinkOut], tags=["links"])
def list_links(form_id: int, db: Session = Depends(get_db)):
    return [link_out(l) for l in _get(db, form_id).links]


@router.post("/{form_id}/links", response_model=LinkOut, status_code=status.HTTP_201_CREATED, tags=["links"])
def create_link(form_id: int, body: LinkCreate, db: Session = Depends(get_db)):
    """채널(instagram/x/youtube/threads)별 배포 링크 생성. 같은 채널은 기존 링크를 재사용한다."""
    f = _get(db, form_id)
    existing = next((l for l in f.links if l.channel == body.channel), None)
    if existing:
        return link_out(existing)
    link = DistributionLink(form_id=f.id, channel=body.channel)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link_out(link)


@router.get("/{form_id}/leads", response_model=list[LeadOut])
def list_form_leads(form_id: int, db: Session = Depends(get_db)):
    _get(db, form_id)
    return list(db.scalars(select(Lead).where(Lead.form_id == form_id).order_by(Lead.id.desc())))
