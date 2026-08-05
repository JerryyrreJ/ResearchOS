"""add data plugin settings

Revision ID: a91f2d6c8e40
Revises: 25298139920f
Create Date: 2026-08-05 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a91f2d6c8e40"
down_revision: str | None = "25298139920f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "data_plugin_settings",
        sa.Column("plugin_id", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_by", sa.String(length=128), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("plugin_id"),
    )


def downgrade() -> None:
    op.drop_table("data_plugin_settings")
