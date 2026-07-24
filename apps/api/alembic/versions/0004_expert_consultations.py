"""add expert consultation lifecycle

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("expert_assignments")}
    if "status" not in columns:
        op.add_column("expert_assignments", sa.Column("status", sa.String(20), nullable=False, server_default="active"))
    if "ended_at" not in columns:
        op.add_column("expert_assignments", sa.Column("ended_at", sa.DateTime(timezone=True)))


def downgrade():
    op.drop_column("expert_assignments", "ended_at")
    op.drop_column("expert_assignments", "status")
