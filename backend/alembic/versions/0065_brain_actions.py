"""The Brain's proposed actions (Phase 4): saved when the Brain offers to do something, run only on Confirm.

Revision ID: 0065
Revises: 0061
Create Date: 2026-10-18
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0065"
down_revision: str | None = "0061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brain_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("conversation_id", UUID(as_uuid=True), sa.ForeignKey("brain_conversations.id", ondelete="CASCADE"), index=True),
        sa.Column("message_id", UUID(as_uuid=True)),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("args", JSONB, nullable=False, server_default="{}"),
        sa.Column("preview", JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(12), nullable=False, server_default="pending"),
        sa.Column("result", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("brain_actions")
