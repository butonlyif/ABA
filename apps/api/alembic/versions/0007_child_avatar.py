"""add child avatar fields and backfill seeds

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {col["name"] for col in sa.inspect(bind).get_columns("children")}
    if "avatar_url" not in columns:
        op.add_column("children", sa.Column("avatar_url", sa.String(255), nullable=True))
    if "avatar_seed" not in columns:
        op.add_column("children", sa.Column("avatar_seed", sa.String(80), nullable=True))

    # 老孩子回填：seed = name，url 指向通用端点（前端会先尝试拿真图，没有就走卡通）
    rows = bind.execute(sa.text("SELECT id, name FROM children WHERE avatar_seed IS NULL OR avatar_seed = ''"))
    for cid, name in rows:
        seed = (name or "星").strip()[:80]
        # 注意：url 留 NULL，前端走 ?seed=xxx 触发卡通路由
        bind.execute(
            sa.text("UPDATE children SET avatar_seed = :seed WHERE id = :id"),
            {"seed": seed, "id": cid},
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {col["name"] for col in sa.inspect(bind).get_columns("children")}
    if "avatar_seed" in columns:
        op.drop_column("children", "avatar_seed")
    if "avatar_url" in columns:
        op.drop_column("children", "avatar_url")
