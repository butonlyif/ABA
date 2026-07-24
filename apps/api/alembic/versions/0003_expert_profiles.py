"""add expert profiles

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if "expert_profiles" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "expert_profiles",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("display_name", sa.String(80), nullable=False),
        sa.Column("title", sa.String(120), nullable=False, server_default="家庭支持专家"),
        sa.Column("specialties", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("bio", sa.Text(), nullable=False, server_default=""),
        sa.Column("credentials", sa.Text(), nullable=False, server_default=""),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("accepting_clients", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("max_clients", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("expert_profiles")
