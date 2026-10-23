from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_operator
from app.models import Campaign, Form, Lead, Operator
from app.schemas import CampaignCreate, CampaignOut, CampaignStats, ChannelMetrics, LeadOut
from app.services.stats import campaign_stats, channel_metrics

router = APIRouter(prefix="/admin/api/campaigns", tags=["campaigns"], dependencies=[Depends(get_current_operator)])


def _get(db: Session, campaign_id: int) -> Campaign:
    c = db.get(Campaign, campaign_id)
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="캠페인을 찾을 수 없습니다.")
    return c


@router.get("", response_model=list[CampaignOut])
def list_campaigns(db: Session = Depends(get_db)):
    return list(db.scalars(select(Campaign).order_by(Campaign.id.desc())))


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
def create_campaign(body: CampaignCreate, db: Session = Depends(get_db), operator: Operator = Depends(get_current_operator)):
    c = Campaign(operator_id=operator.id, name=body.name.strip(), description=body.description)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    return _get(db, campaign_id)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(campaign_id: int, db: Session = Depends(get_db)):
    db.delete(_get(db, campaign_id))
    db.commit()


@router.get("/{campaign_id}/stats", response_model=CampaignStats, tags=["stats"])
def get_campaign_stats(campaign_id: int, db: Session = Depends(get_db)):
    """캠페인별 방문·방문자·신청·전환율 + 채널별 성과."""
    return campaign_stats(db, _get(db, campaign_id))


@router.get("/{campaign_id}/leads", response_model=list[LeadOut])
def list_campaign_leads(campaign_id: int, db: Session = Depends(get_db)):
    _get(db, campaign_id)
    q = select(Lead).join(Form).where(Form.campaign_id == campaign_id).order_by(Lead.id.desc())
    return list(db.scalars(q))


stats_router = APIRouter(prefix="/admin/api/stats", tags=["stats"], dependencies=[Depends(get_current_operator)])


@stats_router.get("/channels", response_model=list[ChannelMetrics])
def all_channel_stats(db: Session = Depends(get_db)):
    """전체 캠페인 합산 채널별 성과."""
    return channel_metrics(db, None)
