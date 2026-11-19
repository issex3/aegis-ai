from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Table, Text, Column, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, utcnow


test_case_industries = Table(
    "test_case_industries",
    Base.metadata,
    Column("test_case_id", String(36), ForeignKey("test_cases.id"), primary_key=True),
    Column("industry_id", String(36), ForeignKey("industries.id"), primary_key=True),
)


class AssessmentSuite(Base, IdMixin, TimestampMixin):
    __tablename__ = "assessment_suites"

    organisation_id: Mapped[str | None] = mapped_column(ForeignKey("organisations.id"), index=True)
    industry_id: Mapped[str | None] = mapped_column(ForeignKey("industries.id"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    test_cases: Mapped[list["TestCase"]] = relationship(back_populates="suite")


class TestCase(Base, IdMixin, TimestampMixin):
    __test__ = False
    __tablename__ = "test_cases"

    organisation_id: Mapped[str | None] = mapped_column(ForeignKey("organisations.id"), index=True)
    suite_id: Mapped[str | None] = mapped_column(ForeignKey("assessment_suites.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    objective: Mapped[str] = mapped_column(Text, default="", nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)
    procedure: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_platform: Mapped[bool] = mapped_column(default=False, nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="general", nullable=False)
    attack_scenario: Mapped[str] = mapped_column(Text, default="", nullable=False)
    test_input: Mapped[str] = mapped_column(Text, default="", nullable=False)
    expected_behaviour: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evaluation_criteria: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_requirements: Mapped[str] = mapped_column(Text, default="", nullable=False)
    remediation_guidance: Mapped[str] = mapped_column(Text, default="", nullable=False)
    version: Mapped[str] = mapped_column(String(16), default="1", nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    requires_tools: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), default="case", server_default="case", nullable=False)
    definition_json: Mapped[dict | None] = mapped_column(JSON)
    content_hash: Mapped[str | None] = mapped_column(String(64))

    suite: Mapped[AssessmentSuite | None] = relationship(back_populates="test_cases")
    industries: Mapped[list["Industry"]] = relationship(secondary=test_case_industries)


class Assessment(Base, IdMixin, TimestampMixin):
    __tablename__ = "assessments"

    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True, nullable=False)
    suite_id: Mapped[str | None] = mapped_column(ForeignKey("assessment_suites.id"))
    sandbox_version_id: Mapped[str | None] = mapped_column(ForeignKey("sandbox_versions.id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    selected_categories: Mapped[list | None] = mapped_column(JSON)
    simulated_role: Mapped[str | None] = mapped_column(String(64))
    authorised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    authorisation_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    configuration_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    parent_assessment_id: Mapped[str | None] = mapped_column(ForeignKey("assessments.id"))
    schedule_id: Mapped[str | None] = mapped_column(String(36))
    engine: Mapped[str] = mapped_column(String(32), default="catalogue", server_default="catalogue", nullable=False)
    programme_id: Mapped[str | None] = mapped_column(ForeignKey("testing_programmes.id"), index=True)

    agent: Mapped["Agent"] = relationship(back_populates="assessments")
    results: Mapped[list["AssessmentResult"]] = relationship(back_populates="assessment")
    findings: Mapped[list["Finding"]] = relationship(back_populates="assessment")


class AssessmentResult(Base, IdMixin):
    __tablename__ = "assessment_results"

    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id"), index=True, nullable=False)
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    test_case_id: Mapped[str | None] = mapped_column(ForeignKey("test_cases.id"))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    test_case_version: Mapped[str | None] = mapped_column(String(16))
    sandbox_version_id: Mapped[str | None] = mapped_column(ForeignKey("sandbox_versions.id"))

    assessment: Mapped[Assessment] = relationship(back_populates="results")


class Finding(Base, IdMixin, TimestampMixin):
    __tablename__ = "findings"

    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id"), index=True, nullable=False)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True, nullable=False)
    result_id: Mapped[str | None] = mapped_column(ForeignKey("assessment_results.id"))
    test_case_id: Mapped[str | None] = mapped_column(ForeignKey("test_cases.id"))
    sandbox_version_id: Mapped[str | None] = mapped_column(String(36))
    stable_key: Mapped[str | None] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    business_impact: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reproduction_steps: Mapped[str] = mapped_column(Text, default="", nullable=False)
    expected_behaviour: Mapped[str] = mapped_column(Text, default="", nullable=False)
    actual_behaviour: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    severity_rule: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)

    assessment: Mapped[Assessment] = relationship(back_populates="findings")
    evidence_items: Mapped[list["FindingEvidence"]] = relationship(back_populates="finding")
    remediations: Mapped[list["Remediation"]] = relationship(back_populates="finding")


class FindingEvidence(Base, IdMixin):
    __tablename__ = "finding_evidence"

    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), index=True, nullable=False)
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    finding: Mapped[Finding] = relationship(back_populates="evidence_items")


class FindingStatusEvent(Base, IdMixin):
    __tablename__ = "finding_status_events"

    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), index=True, nullable=False)
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Remediation(Base, IdMixin, TimestampMixin):
    __tablename__ = "remediations"

    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), index=True, nullable=False)
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    guidance: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="proposed", nullable=False)

    finding: Mapped[Finding] = relationship(back_populates="remediations")


class AssessmentComparison(Base, IdMixin):
    __tablename__ = "assessment_comparisons"
    __table_args__ = (
        UniqueConstraint("baseline_assessment_id", "compared_assessment_id", name="uq_assessment_comparison_pair"),
    )

    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    baseline_assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id"), nullable=False)
    compared_assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id"), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Report(Base, IdMixin, TimestampMixin):
    __tablename__ = "reports"

    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True, nullable=False)
    assessment_id: Mapped[str | None] = mapped_column(ForeignKey("assessments.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    document: Mapped[bytes | None] = mapped_column(LargeBinary)
    byte_size: Mapped[int | None] = mapped_column(Integer)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
