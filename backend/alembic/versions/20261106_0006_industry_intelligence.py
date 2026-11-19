"""Industry Intelligence Engine: agent profiles, testing programmes, execution logs, scenario definitions."""

import sqlalchemy as sa
from alembic import op

revision = "20261106_0006"
down_revision = "20261105_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("industry", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("responsibilities", sa.JSON(), nullable=False),
        sa.Column("tools", sa.JSON(), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("data_types", sa.JSON(), nullable=False),
        sa.Column("authorised_actions", sa.JSON(), nullable=False),
        sa.Column("risk_sensitivity", sa.String(16), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("analysis_json", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_by_user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_profiles_organisation_id", "agent_profiles", ["organisation_id"])
    op.create_index("ix_agent_profiles_agent_id", "agent_profiles", ["agent_id"], unique=True)
    op.create_table(
        "testing_programmes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("industry", sa.String(64), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("intensity", sa.String(16), nullable=False),
        sa.Column("include_generic", sa.Boolean(), nullable=False),
        sa.Column("generic_categories", sa.JSON(), nullable=False),
        sa.Column("selection_json", sa.JSON(), nullable=False),
        sa.Column("profile_snapshot", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_testing_programmes_organisation_id", "testing_programmes", ["organisation_id"])
    op.create_index("ix_testing_programmes_agent_id", "testing_programmes", ["agent_id"])
    op.create_table(
        "assessment_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("assessment_id", sa.String(36), sa.ForeignKey("assessments.id"), nullable=False),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("event", sa.String(64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("data_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assessment_logs_assessment_id", "assessment_logs", ["assessment_id"])
    op.create_index("ix_assessment_logs_organisation_id", "assessment_logs", ["organisation_id"])
    with op.batch_alter_table("assessments") as batch:
        batch.add_column(sa.Column("engine", sa.String(32), nullable=False, server_default="catalogue"))
        batch.add_column(sa.Column("programme_id", sa.String(36), nullable=True))
        batch.create_foreign_key("fk_assessments_programme_id", "testing_programmes", ["programme_id"], ["id"])
        batch.create_index("ix_assessments_programme_id", ["programme_id"])
    with op.batch_alter_table("test_cases") as batch:
        batch.add_column(sa.Column("kind", sa.String(16), nullable=False, server_default="case"))
        batch.add_column(sa.Column("definition_json", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("content_hash", sa.String(64), nullable=True))
    with op.batch_alter_table("sandbox_versions") as batch:
        batch.add_column(sa.Column("fingerprint", sa.String(64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("sandbox_versions") as batch:
        batch.drop_column("fingerprint")
    with op.batch_alter_table("test_cases") as batch:
        batch.drop_column("content_hash")
        batch.drop_column("definition_json")
        batch.drop_column("kind")
    with op.batch_alter_table("assessments") as batch:
        batch.drop_index("ix_assessments_programme_id")
        batch.drop_constraint("fk_assessments_programme_id", type_="foreignkey")
        batch.drop_column("programme_id")
        batch.drop_column("engine")
    op.drop_index("ix_assessment_logs_organisation_id", table_name="assessment_logs")
    op.drop_index("ix_assessment_logs_assessment_id", table_name="assessment_logs")
    op.drop_table("assessment_logs")
    op.drop_index("ix_testing_programmes_agent_id", table_name="testing_programmes")
    op.drop_index("ix_testing_programmes_organisation_id", table_name="testing_programmes")
    op.drop_table("testing_programmes")
    op.drop_index("ix_agent_profiles_agent_id", table_name="agent_profiles")
    op.drop_index("ix_agent_profiles_organisation_id", table_name="agent_profiles")
    op.drop_table("agent_profiles")
