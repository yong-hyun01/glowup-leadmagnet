"""캠페인별·채널별 성과 집계."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Campaign, Form, Lead, Visit
from app.schemas import CampaignStats, ChannelMetrics, Metrics


def _rate(submissions: int, visitors: int) -> float:
    return round(submissions / visitors, 4) if visitors else 0.0


def _form_ids(db: Session, campaign_id: int) -> list[int]:
    return list(db.scalars(select(Form.id).where(Form.campaign_id == campaign_id)))


def campaign_metrics(db: Session, campaign_id: int) -> Metrics:
    form_ids = _form_ids(db, campaign_id)
    if not form_ids:
        return Metrics(visits=0, visitors=0, submissions=0, conversion_rate=0.0)
    visits = db.scalar(select(func.count(Visit.id)).where(Visit.form_id.in_(form_ids))) or 0
    visitors = db.scalar(select(func.count(func.distinct(Visit.visitor_id))).where(Visit.form_id.in_(form_ids))) or 0
    submissions = db.scalar(select(func.count(Lead.id)).where(Lead.form_id.in_(form_ids))) or 0
    return Metrics(visits=visits, visitors=visitors, submissions=submissions, conversion_rate=_rate(submissions, visitors))


def channel_metrics(db: Session, campaign_id: int | None = None) -> list[ChannelMetrics]:
    """campaign_id 가 None 이면 전체 캠페인 기준 채널별 성과."""
    v_q = select(Visit.channel, func.count(Visit.id), func.count(func.distinct(Visit.visitor_id)))
    l_q = select(Lead.channel, func.count(Lead.id))
    if campaign_id is not None:
        form_ids = _form_ids(db, campaign_id)
        if not form_ids:
            return []
        v_q = v_q.where(Visit.form_id.in_(form_ids))
        l_q = l_q.where(Lead.form_id.in_(form_ids))
    visits = {ch: (v, u) for ch, v, u in db.execute(v_q.group_by(Visit.channel))}
    leads = {ch: n for ch, n in db.execute(l_q.group_by(Lead.channel))}
    out = []
    for ch in sorted(set(visits) | set(leads)):
        v, u = visits.get(ch, (0, 0))
        s = leads.get(ch, 0)
        out.append(ChannelMetrics(channel=ch, visits=v, visitors=u, submissions=s, conversion_rate=_rate(s, u)))
    return out


def campaign_stats(db: Session, campaign: Campaign) -> CampaignStats:
    m = campaign_metrics(db, campaign.id)
    return CampaignStats(
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        channels=channel_metrics(db, campaign.id),
        **m.model_dump(),
    )
