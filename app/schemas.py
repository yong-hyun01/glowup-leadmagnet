from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import Channel


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class OperatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    original_filename: str
    size_bytes: int
    created_at: datetime


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None
    created_at: datetime


class FormCreate(BaseModel):
    campaign_id: int
    template_id: int
    name: str = Field(min_length=1, max_length=200)
    success_message: str | None = Field(default=None, max_length=500)


class FormUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    success_message: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class FormOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    campaign_id: int
    template_id: int
    name: str
    slug: str
    success_message: str
    is_active: bool
    public_url: str
    created_at: datetime


class LinkCreate(BaseModel):
    channel: Channel


class LinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    form_id: int
    channel: Channel
    token: str
    url: str
    created_at: datetime


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    form_id: int
    channel: str
    visitor_id: str | None
    data: dict[str, Any]
    created_at: datetime


class Metrics(BaseModel):
    visits: int
    visitors: int
    submissions: int
    conversion_rate: float  # submissions / visitors, 0~1


class ChannelMetrics(Metrics):
    channel: str


class CampaignStats(Metrics):
    campaign_id: int
    campaign_name: str
    channels: list[ChannelMetrics]


class SubmissionIn(BaseModel):
    link_token: str | None = None
    visitor_id: str | None = Field(default=None, max_length=64)
    fields: dict[str, Any]


class SubmissionOut(BaseModel):
    ok: bool
    lead_id: int
    message: str
