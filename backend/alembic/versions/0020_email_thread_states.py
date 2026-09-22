"""Add email_thread_states - SALES-010's thread-quiescence tracker (last
message time, running thread_summary/is_meaningful, close state) so the
scan can detect a thread going idle and write one real closing Note per
exchange, without re-reading the whole thread. See
app/models/email_thread_state.py and app/automations/email_summary.py.

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_thread_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_thread_id", sa.String(256), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id"), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("thread_summary", sa.Text(), nullable=True),
        sa.Column("is_meaningful", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_note_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notes.id"), nullable=True),
        sa.Column("reopen_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source_thread_id", name="uq_email_thread_states_thread"),
    )
    op.create_index("ix_email_thread_states_contact_id", "email_thread_states", ["contact_id"])
    op.create_index("ix_email_thread_states_last_message_at", "email_thread_states", ["last_message_at"])


def downgrade() -> None:
    op.drop_index("ix_email_thread_states_last_message_at", table_name="email_thread_states")
    op.drop_index("ix_email_thread_states_contact_id", table_name="email_thread_states")
    op.drop_table("email_thread_states")
