"""Add automation_state - a small persistent key/value store for producer
jobs that need a cursor across runs (see app/models/automation_state.py).
First consumer: the bounce/OOO mailbox scan, which stores the last
receivedDateTime it already processed per mailbox so a scan every 15
minutes doesn't reread the whole inbox each time.

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "automation_state",
        sa.Column("key", sa.String(length=128), primary_key=True),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("automation_state")
