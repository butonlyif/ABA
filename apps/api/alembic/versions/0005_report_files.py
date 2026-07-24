"""add report file key

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("reports")}
    if "file_key" not in columns:
        op.add_column("reports", sa.Column("file_key", sa.String(length=500), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("reports")}
    if "file_key" in columns:
        op.drop_column("reports", "file_key")
