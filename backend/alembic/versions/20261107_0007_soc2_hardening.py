"""SOC 2 hardening: MFA, lockout, reset tokens, invites, audit hashes, retention."""

import sqlalchemy as sa
from alembic import op

revision = "20261107_0007"
down_revision = "20261106_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("mfa_secret_ciphertext", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("mfa_recovery_hashes", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("users", sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sessions", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("organisations", sa.Column("retention_days", sa.Integer(), nullable=False, server_default="365"))
    op.add_column("organisations", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("audit_events", sa.Column("event_hash", sa.String(64), nullable=True))
    op.add_column("audit_events", sa.Column("previous_hash", sa.String(64), nullable=True))
    op.add_column("intelligence_api_keys", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("intelligence_api_keys", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("intelligence_api_keys", sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=True),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)
    op.create_table(
        "mfa_challenges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.String(256), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
    )
    op.create_index("ix_mfa_challenges_user_id", "mfa_challenges", ["user_id"])
    op.create_index("ix_mfa_challenges_token_hash", "mfa_challenges", ["token_hash"], unique=True)
    op.create_table(
        "organisation_invites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("invited_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_organisation_invites_organisation_id", "organisation_invites", ["organisation_id"])
    op.create_index("ix_organisation_invites_email", "organisation_invites", ["email"])
    op.create_index("ix_organisation_invites_token_hash", "organisation_invites", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("organisation_invites")
    op.drop_table("mfa_challenges")
    op.drop_table("password_reset_tokens")
    op.drop_column("intelligence_api_keys", "last_used_at")
    op.drop_column("intelligence_api_keys", "revoked_at")
    op.drop_column("intelligence_api_keys", "expires_at")
    op.drop_column("audit_events", "previous_hash")
    op.drop_column("audit_events", "event_hash")
    op.drop_column("organisations", "deleted_at")
    op.drop_column("organisations", "retention_days")
    op.drop_column("sessions", "last_seen_at")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_count")
    op.drop_column("users", "mfa_recovery_hashes")
    op.drop_column("users", "mfa_secret_ciphertext")
    op.drop_column("users", "mfa_enabled")
