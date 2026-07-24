"""add production operations records

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "system_events" not in tables:
        op.create_table(
            "system_events",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("level", sa.String(20), nullable=False),
            sa.Column("category", sa.String(50), nullable=False),
            sa.Column("message", sa.String(255), nullable=False),
            sa.Column("details", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_system_events_level", "system_events", ["level"])
        op.create_index("ix_system_events_category", "system_events", ["category"])
        op.create_index("ix_system_events_created_at", "system_events", ["created_at"])
    if "ai_usage" not in tables:
        op.create_table(
            "ai_usage",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("product", sa.String(20), nullable=False),
            sa.Column("provider", sa.String(40), nullable=False),
            sa.Column("model", sa.String(80), nullable=False),
            sa.Column("success", sa.Boolean(), nullable=False),
            sa.Column("fallback", sa.Boolean(), nullable=False),
            sa.Column("prompt_tokens", sa.Integer(), nullable=False),
            sa.Column("completion_tokens", sa.Integer(), nullable=False),
            sa.Column("latency_ms", sa.Integer(), nullable=False),
            sa.Column("error_type", sa.String(100)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_ai_usage_user_id", "ai_usage", ["user_id"])
        op.create_index("ix_ai_usage_product", "ai_usage", ["product"])
        op.create_index("ix_ai_usage_created_at", "ai_usage", ["created_at"])


def downgrade() -> None:
    op.drop_table("ai_usage")
    op.drop_table("system_events")
