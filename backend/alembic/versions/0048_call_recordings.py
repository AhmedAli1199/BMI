"""Calls the notetaker records, with their notes and transcript.

Revision ID: 0048
Revises: 0047
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0048"
down_revision: str | None = "0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "call_recordings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("notetaker_id", sa.String(64), unique=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True)),
        sa.Column("company_id", postgresql.UUID(as_uuid=True)),
        sa.Column("meeting_url", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(20)),
        sa.Column("title", sa.Text()),
        sa.Column("status", sa.String(30), nullable=False, server_default="scheduled"),
        sa.Column("status_label", sa.String(100)),
        sa.Column("status_detail", sa.Text()),
        sa.Column("participants", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("notes", postgresql.JSONB()),
        sa.Column("transcript", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("saved_to_history_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for col in ("notetaker_id", "user_id", "contact_id", "company_id", "status"):
        op.create_index(f"ix_call_recordings_{col}", "call_recordings", [col])


def downgrade() -> None:
    op.drop_table("call_recordings")
