"""Subscriptions, durable assessment jobs, notifications, and licensed API keys."""

import sqlalchemy as sa
from alembic import op

revision = "20261105_0005"
down_revision = "20261104_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("plan_code", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("stripe_customer_id", sa.String(64)),
        sa.Column("stripe_subscription_id", sa.String(64)),
        sa.Column("current_period_end", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_subscriptions_organisation_id", "subscriptions", ["organisation_id"], unique=True)
    op.create_table(
        "assessment_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("assessment_id", sa.String(36), sa.ForeignKey("assessments.id"), nullable=False),
        sa.Column("triggered_by_user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assessment_jobs_assessment_id", "assessment_jobs", ["assessment_id"])
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "intelligence_api_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("prefix", sa.String(16), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("requests_made", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_intelligence_api_keys_token_hash", "intelligence_api_keys", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_intelligence_api_keys_token_hash", table_name="intelligence_api_keys")
    op.drop_table("intelligence_api_keys")
    op.drop_table("notifications")
    op.drop_index("ix_assessment_jobs_assessment_id", table_name="assessment_jobs")
    op.drop_table("assessment_jobs")
    op.drop_index("ix_subscriptions_organisation_id", table_name="subscriptions")
    op.drop_table("subscriptions")
