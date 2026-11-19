from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin, utcnow


class AgentProfile(Base, IdMixin, TimestampMixin):
    __tablename__ = "agent_profiles"

    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), unique=True, nullable=False)
    industry: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    purpose: Mapped[str] = mapped_column(Text, default="", nullable=False)
    responsibilities: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    tools: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    permissions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    data_types: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    authorised_actions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    risk_sensitivity: Mapped[str] = mapped_column(String(16), default="moderate", nullable=False)
    capabilities: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    analysis_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))


class TestingProgramme(Base, IdMixin, TimestampMixin):
    __test__ = False
    __tablename__ = "testing_programmes"

    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True, nullable=False)
    industry: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    intensity: Mapped[str] = mapped_column(String(16), default="standard", nullable=False)
    include_generic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    generic_categories: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    selection_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    profile_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)


class AssessmentLog(Base, IdMixin):
    __tablename__ = "assessment_logs"

    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id"), index=True, nullable=False)
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[str] = mapped_column(String(16), default="info", nullable=False)
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
