"""Store generated PDF reports."""

import sqlalchemy as sa
from alembic import op

revision = "20261104_0004"
down_revision = "20261103_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("reports") as batch:
        batch.add_column(sa.Column("document", sa.LargeBinary(), nullable=True))
        batch.add_column(sa.Column("byte_size", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("reports") as batch:
        batch.drop_column("byte_size")
        batch.drop_column("document")
