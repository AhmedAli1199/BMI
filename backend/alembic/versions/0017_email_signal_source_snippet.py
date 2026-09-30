"""Add email_signals.source_snippet - a bounded excerpt of the specific
message a signal was extracted from, so a reviewer can see the real
context (not just the AI's one-line summary) without the backend needing
to store or re-fetch a whole email thread. See
app/automations/email_summary.py and signal_triggers.py.

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("email_signals", sa.Column("source_snippet", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("email_signals", "source_snippet")
