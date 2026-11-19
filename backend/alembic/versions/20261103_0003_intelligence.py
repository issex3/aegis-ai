"""Findings detail, baselines, schedules, and intelligence provenance."""

import sqlalchemy as sa
from alembic import op

revision = "20261103_0003"
down_revision = "20261102_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("assessments") as batch:
        batch.add_column(sa.Column("is_baseline", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("trigger_type", sa.String(32), nullable=False, server_default="manual"))
        batch.add_column(sa.Column("configuration_json", sa.JSON(), nullable=False, server_default="{}"))
        batch.add_column(sa.Column("parent_assessment_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("schedule_id", sa.String(36), nullable=True))
    with op.batch_alter_table("findings") as batch:
        batch.add_column(sa.Column("test_case_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("sandbox_version_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("stable_key", sa.String(64), nullable=True))
        batch.add_column(sa.Column("category", sa.String(64), nullable=False, server_default=""))
        batch.add_column(sa.Column("business_impact", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("reproduction_steps", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("expected_behaviour", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("actual_behaviour", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("confidence", sa.String(16), nullable=False, server_default="medium"))
        batch.add_column(sa.Column("severity_rule", sa.String(64), nullable=False, server_default=""))
    op.create_index("ix_findings_stable_key", "findings", ["stable_key"])
    op.create_table(
        "finding_status_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("finding_id", sa.String(36), sa.ForeignKey("findings.id"), nullable=False),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("from_status", sa.String(32)),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("assessment_comparisons") as batch:
        batch.add_column(sa.Column("details_json", sa.JSON(), nullable=False, server_default="{}"))
    with op.batch_alter_table("data_contribution_consents") as batch:
        batch.add_column(sa.Column("permitted_categories", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("intended_use", sa.Text(), nullable=False, server_default=""))
    with op.batch_alter_table("intelligence_records") as batch:
        batch.add_column(sa.Column("validation_status", sa.String(32), nullable=False, server_default="pending_review"))
        batch.add_column(sa.Column("approval_status", sa.String(32), nullable=False, server_default="unapproved"))
        batch.add_column(sa.Column("processing_version", sa.String(32), nullable=False, server_default="2026.11"))
        batch.add_column(sa.Column("provenance_json", sa.JSON(), nullable=False, server_default="{}"))
    op.create_table(
        "assessment_schedules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("sandbox_id", sa.String(36)),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("categories", sa.JSON(), nullable=False),
        sa.Column("interval_hours", sa.Integer(), nullable=False),
        sa.Column("max_runs", sa.Integer(), nullable=False),
        sa.Column("runs_completed", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "webhook_endpoints",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("schedule_id", sa.String(36), sa.ForeignKey("assessment_schedules.id")),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_webhook_endpoints_token_hash", "webhook_endpoints", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_webhook_endpoints_token_hash", table_name="webhook_endpoints")
    op.drop_table("webhook_endpoints")
    op.drop_table("assessment_schedules")
    op.drop_index("ix_findings_stable_key", table_name="findings")
    op.drop_table("finding_status_events")
