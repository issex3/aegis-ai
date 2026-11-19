from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, utcnow


class Agent(Base, IdMixin, TimestampMixin):
    __tablename__ = "agents"

    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    integration_type: Mapped[str] = mapped_column(String(64), nullable=False)
    api_endpoint: Mapped[str] = mapped_column(String(2048), nullable=False)
    model_name: Mapped[str] = mapped_column(String(160), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    behaviour: Mapped[str] = mapped_column(Text, nullable=False)
    security_boundaries: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organisation: Mapped["Organisation"] = relationship(back_populates="agents")
    integration: Mapped["AgentIntegration | None"] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
        uselist=False,
    )
    credentials: Mapped[list["AgentCredential"]] = relationship(back_populates="agent")
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="agent")


class AgentIntegration(Base, IdMixin, TimestampMixin):
    __tablename__ = "agent_integrations"

    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), unique=True, nullable=False)
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(2048), nullable=False)
    model_name: Mapped[str] = mapped_column(String(160), nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    max_output_tokens: Mapped[int] = mapped_column(Integer, default=512, nullable=False)
    temperature: Mapped[float | None] = mapped_column(Float)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    agent: Mapped[Agent] = relationship(back_populates="integration")


class AgentCredential(Base, IdMixin):
    __tablename__ = "agent_credentials"

    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True, nullable=False)
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(64), default="primary", nullable=False)
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    hint: Mapped[str] = mapped_column(String(8), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(32), default="fernet", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    agent: Mapped[Agent] = relationship(back_populates="credentials")
