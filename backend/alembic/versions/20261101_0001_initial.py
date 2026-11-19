"""Initial Aegis schema and industry catalogue."""

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "20261101_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_platform_operator", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "organisations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_organisations_slug", "organisations", ["slug"], unique=True)

    op.create_table(
        "organisation_memberships",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organisation_id", "user_id", name="uq_membership_org_user"),
    )
    op.create_index("ix_organisation_memberships_organisation_id", "organisation_memberships", ["organisation_id"])
    op.create_index("ix_organisation_memberships_user_id", "organisation_memberships", ["user_id"])

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id")),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.String(256)),
        sa.Column("ip_address", sa.String(64)),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_organisation_id", "sessions", ["organisation_id"])
    op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"], unique=True)

    op.create_table(
        "industries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_industries_slug", "industries", ["slug"], unique=True)

    op.create_table(
        "agents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("integration_type", sa.String(64), nullable=False),
        sa.Column("api_endpoint", sa.String(2048), nullable=False),
        sa.Column("model_name", sa.String(160), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("behaviour", sa.Text(), nullable=False),
        sa.Column("security_boundaries", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agents_organisation_id", "agents", ["organisation_id"])

    op.create_table(
        "agent_integrations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("endpoint", sa.String(2048), nullable=False),
        sa.Column("model_name", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_integrations_agent_id", "agent_integrations", ["agent_id"], unique=True)
    op.create_index("ix_agent_integrations_organisation_id", "agent_integrations", ["organisation_id"])

    op.create_table(
        "agent_credentials",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column("hint", sa.String(8), nullable=False),
        sa.Column("algorithm", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_agent_credentials_agent_id", "agent_credentials", ["agent_id"])
    op.create_index("ix_agent_credentials_organisation_id", "agent_credentials", ["organisation_id"])

    op.create_table(
        "sandboxes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id")),
        sa.Column("industry_id", sa.String(36), sa.ForeignKey("industries.id"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sandboxes_organisation_id", "sandboxes", ["organisation_id"])
    op.create_index("ix_sandboxes_industry_id", "sandboxes", ["industry_id"])

    op.create_table(
        "sandbox_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sandbox_id", sa.String(36), sa.ForeignKey("sandboxes.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("changelog", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("sandbox_id", "version_number", name="uq_sandbox_version_number"),
    )
    op.create_index("ix_sandbox_versions_sandbox_id", "sandbox_versions", ["sandbox_id"])

    with op.batch_alter_table("sandboxes") as batch:
        batch.add_column(sa.Column("current_version_id", sa.String(36), nullable=True))
        batch.create_foreign_key("fk_sandbox_current_version", "sandbox_versions", ["current_version_id"], ["id"])

    op.create_table(
        "sandbox_datasets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sandbox_version_id", sa.String(36), sa.ForeignKey("sandbox_versions.id"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("schema_json", sa.JSON(), nullable=False),
        sa.Column("storage_ref", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sandbox_datasets_sandbox_version_id", "sandbox_datasets", ["sandbox_version_id"])

    op.create_table(
        "sandbox_tools",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sandbox_version_id", sa.String(36), sa.ForeignKey("sandbox_versions.id"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("specification_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sandbox_tools_sandbox_version_id", "sandbox_tools", ["sandbox_version_id"])

    op.create_table(
        "sandbox_workflows",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sandbox_version_id", sa.String(36), sa.ForeignKey("sandbox_versions.id"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("definition_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sandbox_workflows_sandbox_version_id", "sandbox_workflows", ["sandbox_version_id"])

    op.create_table(
        "assessment_suites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id")),
        sa.Column("industry_id", sa.String(36), sa.ForeignKey("industries.id")),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assessment_suites_organisation_id", "assessment_suites", ["organisation_id"])
    op.create_index("ix_assessment_suites_industry_id", "assessment_suites", ["industry_id"])

    op.create_table(
        "test_cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id")),
        sa.Column("suite_id", sa.String(36), sa.ForeignKey("assessment_suites.id")),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("procedure", sa.Text(), nullable=False),
        sa.Column("is_platform", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_test_cases_code", "test_cases", ["code"], unique=True)
    op.create_index("ix_test_cases_organisation_id", "test_cases", ["organisation_id"])
    op.create_index("ix_test_cases_suite_id", "test_cases", ["suite_id"])

    op.create_table(
        "test_case_industries",
        sa.Column("test_case_id", sa.String(36), sa.ForeignKey("test_cases.id"), primary_key=True),
        sa.Column("industry_id", sa.String(36), sa.ForeignKey("industries.id"), primary_key=True),
    )

    op.create_table(
        "assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("suite_id", sa.String(36), sa.ForeignKey("assessment_suites.id")),
        sa.Column("sandbox_version_id", sa.String(36), sa.ForeignKey("sandbox_versions.id")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assessments_organisation_id", "assessments", ["organisation_id"])
    op.create_index("ix_assessments_agent_id", "assessments", ["agent_id"])

    op.create_table(
        "assessment_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("assessment_id", sa.String(36), sa.ForeignKey("assessments.id"), nullable=False),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("test_case_id", sa.String(36), sa.ForeignKey("test_cases.id")),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assessment_results_assessment_id", "assessment_results", ["assessment_id"])
    op.create_index("ix_assessment_results_organisation_id", "assessment_results", ["organisation_id"])

    op.create_table(
        "findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("assessment_id", sa.String(36), sa.ForeignKey("assessments.id"), nullable=False),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("result_id", sa.String(36), sa.ForeignKey("assessment_results.id")),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_findings_organisation_id", "findings", ["organisation_id"])
    op.create_index("ix_findings_assessment_id", "findings", ["assessment_id"])
    op.create_index("ix_findings_agent_id", "findings", ["agent_id"])

    op.create_table(
        "finding_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("finding_id", sa.String(36), sa.ForeignKey("findings.id"), nullable=False),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("evidence_type", sa.String(64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_finding_evidence_finding_id", "finding_evidence", ["finding_id"])
    op.create_index("ix_finding_evidence_organisation_id", "finding_evidence", ["organisation_id"])

    op.create_table(
        "remediations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("finding_id", sa.String(36), sa.ForeignKey("findings.id"), nullable=False),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("guidance", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_remediations_finding_id", "remediations", ["finding_id"])
    op.create_index("ix_remediations_organisation_id", "remediations", ["organisation_id"])

    op.create_table(
        "assessment_comparisons",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("baseline_assessment_id", sa.String(36), sa.ForeignKey("assessments.id"), nullable=False),
        sa.Column("compared_assessment_id", sa.String(36), sa.ForeignKey("assessments.id"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("baseline_assessment_id", "compared_assessment_id", name="uq_assessment_comparison_pair"),
    )
    op.create_index("ix_assessment_comparisons_organisation_id", "assessment_comparisons", ["organisation_id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("assessment_id", sa.String(36), sa.ForeignKey("assessments.id")),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reports_organisation_id", "reports", ["organisation_id"])
    op.create_index("ix_reports_assessment_id", "reports", ["assessment_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id")),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(36)),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_organisation_id", "audit_events", ["organisation_id"])
    op.create_index("ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"])

    op.create_table(
        "data_contribution_consents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("policy_version", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(64), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_data_contribution_consents_organisation_id", "data_contribution_consents", ["organisation_id"])

    op.create_table(
        "intelligence_datasets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("classification", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "dataset_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dataset_id", sa.String(36), sa.ForeignKey("intelligence_datasets.id"), nullable=False),
        sa.Column("version_label", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dataset_id", "version_label", name="uq_dataset_version_label"),
    )
    op.create_index("ix_dataset_versions_dataset_id", "dataset_versions", ["dataset_id"])

    op.create_table(
        "intelligence_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dataset_version_id", sa.String(36), sa.ForeignKey("dataset_versions.id"), nullable=False),
        sa.Column("source_organisation_id", sa.String(36), sa.ForeignKey("organisations.id")),
        sa.Column("source_consent_id", sa.String(36), sa.ForeignKey("data_contribution_consents.id")),
        sa.Column("source_finding_id", sa.String(36), sa.ForeignKey("findings.id")),
        sa.Column("redacted_summary", sa.Text(), nullable=False),
        sa.Column("record_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_intelligence_records_dataset_version_id", "intelligence_records", ["dataset_version_id"])
    op.create_index("ix_intelligence_records_source_organisation_id", "intelligence_records", ["source_organisation_id"])

    now = datetime.now(timezone.utc)
    industries = sa.table(
        "industries",
        sa.column("id", sa.String),
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("created_at", sa.DateTime),
    )
    op.bulk_insert(
        industries,
        [
            {
                "id": "0b6d1a0e-5a1c-4b7e-9c1a-111111111111",
                "slug": "financial-services",
                "name": "Financial services",
                "description": "Retail banking, payments, lending, and insurance workflows where agents may see account data or initiate transactions.",
                "created_at": now,
            },
            {
                "id": "0b6d1a0e-5a1c-4b7e-9c1a-222222222222",
                "slug": "healthcare",
                "name": "Healthcare",
                "description": "Clinical and administrative agents that may encounter patient information, care instructions, or scheduling systems.",
                "created_at": now,
            },
            {
                "id": "0b6d1a0e-5a1c-4b7e-9c1a-333333333333",
                "slug": "legal",
                "name": "Legal",
                "description": "Matter-management and research agents that handle privileged material and external communications.",
                "created_at": now,
            },
            {
                "id": "0b6d1a0e-5a1c-4b7e-9c1a-444444444444",
                "slug": "customer-operations",
                "name": "Customer operations",
                "description": "Support and success agents with access to tickets, customer records, and refund or account tools.",
                "created_at": now,
            },
            {
                "id": "0b6d1a0e-5a1c-4b7e-9c1a-555555555555",
                "slug": "software-engineering",
                "name": "Software engineering",
                "description": "Coding and operations agents that can read repositories, propose changes, or call internal tools.",
                "created_at": now,
            },
            {
                "id": "0b6d1a0e-5a1c-4b7e-9c1a-666666666666",
                "slug": "public-sector",
                "name": "Public sector",
                "description": "Service-delivery agents operating under statutory duties and strict data-handling obligations.",
                "created_at": now,
            },
        ],
    )


def downgrade() -> None:
    for table in (
        "intelligence_records",
        "dataset_versions",
        "intelligence_datasets",
        "data_contribution_consents",
        "audit_events",
        "reports",
        "assessment_comparisons",
        "remediations",
        "finding_evidence",
        "findings",
        "assessment_results",
        "assessments",
        "test_case_industries",
        "test_cases",
        "assessment_suites",
        "sandbox_workflows",
        "sandbox_tools",
        "sandbox_datasets",
        "sandbox_versions",
        "sandboxes",
        "agent_credentials",
        "agent_integrations",
        "agents",
        "industries",
        "sessions",
        "organisation_memberships",
        "organisations",
        "users",
    ):
        op.drop_table(table)
