"""Writing profiles: how each salesperson writes proposals and replies.

Revision ID: 0053
Revises: 0052
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0053"
down_revision: str | None = "0052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "writing_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("samples", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text()),
        sa.Column("profile", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(10), nullable=False, server_default="draft"),
        sa.Column("built_by", sa.String(10)),
        sa.Column("built_at", sa.DateTime(timezone=True)),
        sa.Column("learned", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("edits", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("writing_profiles")
