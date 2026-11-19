from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, utcnow


class Industry(Base, IdMixin):
    __tablename__ = "industries"

    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    sandboxes: Mapped[list["Sandbox"]] = relationship(back_populates="industry")


class Sandbox(Base, IdMixin, TimestampMixin):
    __tablename__ = "sandboxes"

    organisation_id: Mapped[str | None] = mapped_column(ForeignKey("organisations.id"), index=True)
    industry_id: Mapped[str] = mapped_column(ForeignKey("industries.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    current_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("sandbox_versions.id", use_alter=True, name="fk_sandbox_current_version"),
    )
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))

    industry: Mapped[Industry] = relationship(back_populates="sandboxes")
    versions: Mapped[list["SandboxVersion"]] = relationship(
        back_populates="sandbox",
        foreign_keys="SandboxVersion.sandbox_id",
    )


class SandboxVersion(Base, IdMixin):
    __tablename__ = "sandbox_versions"
    __table_args__ = (UniqueConstraint("sandbox_id", "version_number", name="uq_sandbox_version_number"),)

    sandbox_id: Mapped[str] = mapped_column(ForeignKey("sandboxes.id"), index=True, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    changelog: Mapped[str] = mapped_column(Text, default="", nullable=False)
    fingerprint: Mapped[str | None] = mapped_column(String(64))
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    sandbox: Mapped[Sandbox] = relationship(
        back_populates="versions",
        foreign_keys=[sandbox_id],
    )
    datasets: Mapped[list["SandboxDataset"]] = relationship(back_populates="version")
    tools: Mapped[list["SandboxTool"]] = relationship(back_populates="version")
    workflows: Mapped[list["SandboxWorkflow"]] = relationship(back_populates="version")


class SandboxDataset(Base, IdMixin):
    __tablename__ = "sandbox_datasets"

    sandbox_version_id: Mapped[str] = mapped_column(ForeignKey("sandbox_versions.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    schema_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    storage_ref: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    version: Mapped[SandboxVersion] = relationship(back_populates="datasets")


class SandboxTool(Base, IdMixin):
    __tablename__ = "sandbox_tools"

    sandbox_version_id: Mapped[str] = mapped_column(ForeignKey("sandbox_versions.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    specification_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    version: Mapped[SandboxVersion] = relationship(back_populates="tools")


class SandboxWorkflow(Base, IdMixin):
    __tablename__ = "sandbox_workflows"

    sandbox_version_id: Mapped[str] = mapped_column(ForeignKey("sandbox_versions.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    definition_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    version: Mapped[SandboxVersion] = relationship(back_populates="workflows")
