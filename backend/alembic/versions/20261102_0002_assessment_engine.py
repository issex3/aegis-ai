"""Assessment engine fields for integrations, cases, and results."""

import sqlalchemy as sa
from alembic import op

revision = "20261102_0002"
down_revision = "20261101_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("agent_integrations") as batch:
        batch.add_column(sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="30"))
        batch.add_column(sa.Column("max_output_tokens", sa.Integer(), nullable=False, server_default="512"))
        batch.add_column(sa.Column("temperature", sa.Float(), nullable=True))
        batch.add_column(sa.Column("config_json", sa.JSON(), nullable=False, server_default="{}"))
    with op.batch_alter_table("test_cases") as batch:
        batch.add_column(sa.Column("category", sa.String(64), nullable=False, server_default="general"))
        batch.add_column(sa.Column("attack_scenario", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("test_input", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("expected_behaviour", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("evaluation_criteria", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("evidence_requirements", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("remediation_guidance", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("version", sa.String(16), nullable=False, server_default="1"))
        batch.add_column(sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("requires_tools", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("assessments") as batch:
        batch.add_column(sa.Column("selected_categories", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("simulated_role", sa.String(64), nullable=True))
        batch.add_column(sa.Column("authorised_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("authorisation_note", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("error_summary", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("assessment_results") as batch:
        batch.add_column(sa.Column("duration_ms", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("test_case_version", sa.String(16), nullable=True))
        batch.add_column(sa.Column("sandbox_version_id", sa.String(36), nullable=True))
        batch.create_foreign_key(
            "fk_assessment_results_sandbox_version",
            "sandbox_versions",
            ["sandbox_version_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("assessment_results") as batch:
        batch.drop_constraint("fk_assessment_results_sandbox_version", type_="foreignkey")
        batch.drop_column("sandbox_version_id")
        batch.drop_column("test_case_version")
        batch.drop_column("duration_ms")
    with op.batch_alter_table("assessments") as batch:
        for name in (
            "is_simulated",
            "error_summary",
            "cancel_requested",
            "authorisation_note",
            "authorised_at",
            "simulated_role",
            "selected_categories",
        ):
            batch.drop_column(name)
    with op.batch_alter_table("test_cases") as batch:
        for name in (
            "requires_tools",
            "tags",
            "version",
            "remediation_guidance",
            "evidence_requirements",
            "evaluation_criteria",
            "expected_behaviour",
            "test_input",
            "attack_scenario",
            "category",
        ):
            batch.drop_column(name)
    with op.batch_alter_table("agent_integrations") as batch:
        for name in ("config_json", "temperature", "max_output_tokens", "timeout_seconds"):
            batch.drop_column(name)
