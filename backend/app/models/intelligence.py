from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, utcnow


class AssessmentSchedule(Base, IdMixin, TimestampMixin):
    __tablename__ = "assessment_schedules"

    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), nullable=False)
    sandbox_id: Mapped[str | None] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    categories: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    interval_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    max_runs: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    runs_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)


class WebhookEndpoint(Base, IdMixin):
    __tablename__ = "webhook_endpoints"

    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    schedule_id: Mapped[str | None] = mapped_column(ForeignKey("assessment_schedules.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuditEvent(Base, IdMixin):
    __tablename__ = "audit_events"

    organisation_id: Mapped[str | None] = mapped_column(ForeignKey("organisations.id"), index=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    event_hash: Mapped[str | None] = mapped_column(String(64))
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class DataContributionConsent(Base, IdMixin):
    __tablename__ = "data_contribution_consents"

    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    permitted_categories: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    intended_use: Mapped[str] = mapped_column(Text, default="", nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IntelligenceDataset(Base, IdMixin, TimestampMixin):
    __tablename__ = "intelligence_datasets"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    classification: Mapped[str] = mapped_column(String(32), default="restricted", nullable=False)

    versions: Mapped[list["DatasetVersion"]] = relationship(back_populates="dataset")


class DatasetVersion(Base, IdMixin):
    __tablename__ = "dataset_versions"
    __table_args__ = (UniqueConstraint("dataset_id", "version_label", name="uq_dataset_version_label"),)

    dataset_id: Mapped[str] = mapped_column(ForeignKey("intelligence_datasets.id"), index=True, nullable=False)
    version_label: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    dataset: Mapped[IntelligenceDataset] = relationship(back_populates="versions")
    records: Mapped[list["IntelligenceRecord"]] = relationship(back_populates="dataset_version")


class IntelligenceRecord(Base, IdMixin):
    __tablename__ = "intelligence_records"

    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True, nullable=False)
    source_organisation_id: Mapped[str | None] = mapped_column(ForeignKey("organisations.id"), index=True)
    source_consent_id: Mapped[str | None] = mapped_column(ForeignKey("data_contribution_consents.id"))
    source_finding_id: Mapped[str | None] = mapped_column(ForeignKey("findings.id"))
    redacted_summary: Mapped[str] = mapped_column(Text, nullable=False)
    record_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(32), default="pending_review", nullable=False)
    approval_status: Mapped[str] = mapped_column(String(32), default="unapproved", nullable=False)
    processing_version: Mapped[str] = mapped_column(String(32), default="2026.11", nullable=False)
    provenance_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    dataset_version: Mapped[DatasetVersion] = relationship(back_populates="records")
