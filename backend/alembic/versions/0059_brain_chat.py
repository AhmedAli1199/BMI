"""The AI Hub chat: conversations, messages (with their trace) and screenshots sent with questions.

Revision ID: 0059
Revises: 0058
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0059"
down_revision: str | None = "0058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brain_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(200), nullable=False, server_default="New chat"),
        sa.Column("started_on", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "brain_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brain_conversations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("role", sa.String(12), nullable=False),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("model_text", sa.Text()),
        sa.Column("context", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("trace", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("rating", sa.SmallInteger()),
        sa.Column("rating_note", sa.Text()),
        sa.Column("feedback_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
    )
    op.create_table(
        "brain_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brain_messages.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("mime", sa.String(40), nullable=False, server_default="image/png"),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("label", sa.String(200)),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
    )


def downgrade() -> None:
    op.drop_table("brain_images")
    op.drop_table("brain_messages")
    op.drop_table("brain_conversations")
