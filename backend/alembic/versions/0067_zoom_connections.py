"""Each person's connected Zoom (the notetaker joins Zoom calls on their behalf).

Revision ID: 0067
Revises: 0066
Create Date: 2026-10-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0067"
down_revision: str | None = "0066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "zoom_connections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("zoom_user_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="connected"),
        sa.Column("last_error", sa.Text()),
        sa.Column("connected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("checked_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("zoom_connections")
