import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_token() -> str:
    return uuid.uuid4().hex[:12]


class Channel(str, enum.Enum):
    instagram = "instagram"
    x = "x"
    youtube = "youtube"
    threads = "threads"


class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class HtmlTemplate(Base):
    """운영자가 AI로 만들어 등록한 단일 .html 파일."""

    __tablename__ = "html_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("operators.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    forms: Mapped[list["Form"]] = relationship(back_populates="template")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("operators.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    forms: Mapped[list["Form"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")


class Form(Base):
    """캠페인 + HTML 템플릿 조합으로 만든 커스텀 신청 폼. slug 로 공개된다."""

    __tablename__ = "forms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    template_id: Mapped[int] = mapped_column(ForeignKey("html_templates.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, default=new_token)
    # 성공 시 iframe 안에 표시할 메시지. 운영자 HTML 안에서 커스텀 가능.
    success_message: Mapped[str] = mapped_column(String(500), nullable=False, default="신청이 접수되었습니다. 감사합니다!")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    campaign: Mapped[Campaign] = relationship(back_populates="forms")
    template: Mapped[HtmlTemplate] = relationship(back_populates="forms")
    links: Mapped[list["DistributionLink"]] = relationship(back_populates="form", cascade="all, delete-orphan")
    visits: Mapped[list["Visit"]] = relationship(back_populates="form", cascade="all, delete-orphan")
    leads: Mapped[list["Lead"]] = relationship(back_populates="form", cascade="all, delete-orphan")


class DistributionLink(Base):
    """폼 × 채널 당 하나의 배포 링크 (/l/{token})."""

    __tablename__ = "distribution_links"
    __table_args__ = (UniqueConstraint("form_id", "channel", name="uq_link_form_channel"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    form_id: Mapped[int] = mapped_column(ForeignKey("forms.id"), nullable=False)
    channel: Mapped[Channel] = mapped_column(Enum(Channel, name="channel"), nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, default=new_token)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    form: Mapped[Form] = relationship(back_populates="links")


class Visit(Base):
    """공개 폼 페이지 로드 1회 = 방문 1건. visitor_id 는 쿠키 기반 고유 식별자."""

    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    form_id: Mapped[int] = mapped_column(ForeignKey("forms.id"), nullable=False, index=True)
    link_id: Mapped[int | None] = mapped_column(ForeignKey("distribution_links.id"))
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="direct", index=True)
    visitor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_agent: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    form: Mapped[Form] = relationship(back_populates="visits")


class Lead(Base):
    """신청 데이터 = CRM 명단."""

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    form_id: Mapped[int] = mapped_column(ForeignKey("forms.id"), nullable=False, index=True)
    link_id: Mapped[int | None] = mapped_column(ForeignKey("distribution_links.id"))
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="direct", index=True)
    visitor_id: Mapped[str | None] = mapped_column(String(64), index=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    form: Mapped[Form] = relationship(back_populates="leads")
