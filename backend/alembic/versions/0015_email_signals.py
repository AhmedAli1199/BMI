"""Add email_signals - structured facts extracted from real email
correspondence (budget windows, renewal dates, promised call-backs,
personal touchpoints) by app/automations/email_summary.py. Feeds
SALES-012 (Budget-Window & Renewal Triggers) and SALES-005 (Personal
Touchpoint Reminders) once those are rebuilt to read from it instead of
bare Activity rows.

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-21
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id"), nullable=False),
        sa.Column("signal_type", sa.String(length=32), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_thread_id", sa.String(length=256), nullable=False),
        sa.Column("source_message_id", sa.String(length=256), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "signal_type IN ('budget_window', 'renewal_date', 'promised_callback', 'personal_touchpoint')",
            name="ck_email_signals_type",
        ),
        sa.CheckConstraint("status IN ('open', 'actioned', 'dismissed')", name="ck_email_signals_status"),
        sa.UniqueConstraint("source_thread_id", "signal_type", name="uq_email_signals_thread_type"),
    )
    op.create_index("ix_email_signals_contact_id", "email_signals", ["contact_id"])
    op.create_index("ix_email_signals_signal_type", "email_signals", ["signal_type"])
    op.create_index("ix_email_signals_due_date", "email_signals", ["due_date"])
    op.create_index("ix_email_signals_status", "email_signals", ["status"])


def downgrade() -> None:
    op.drop_table("email_signals")
