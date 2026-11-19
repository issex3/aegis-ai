from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin, utcnow


class Subscription(Base, IdMixin, TimestampMixin):
    __tablename__ = "subscriptions"

    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), unique=True, nullable=False)
    plan_code: Mapped[str] = mapped_column(String(32), default="starter", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="inactive", nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(64))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssessmentJob(Base, IdMixin, TimestampMixin):
    __tablename__ = "assessment_jobs"

    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id"), index=True, nullable=False)
    triggered_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AppNotification(Base, IdMixin):
    __tablename__ = "notifications"

    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class IntelligenceApiKey(Base, IdMixin):
    __tablename__ = "intelligence_api_keys"

    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requests_made: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
