"""Reminders, notifications, connected Outlook mailboxes, mail-merge
templates / merges / recipients / attachments. See app/models/messaging.py.

Revision ID: 0026
Revises: 0025
Create Date: 2026-09-29
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels = None
depends_on = None

U = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "reminders",
        sa.Column("id", U, primary_key=True),
        sa.Column("user_id", U, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("contact_id", U, sa.ForeignKey("contacts.id", ondelete="CASCADE"), index=True),
        sa.Column("company_id", U, sa.ForeignKey("companies.id", ondelete="CASCADE"), index=True),
        sa.Column("due_at", TS, nullable=False, index=True),
        sa.Column("note", sa.Text()),
        sa.Column("email_me", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(16), nullable=False, server_default="open", index=True),
        sa.Column("notified_at", TS),
        sa.Column("completed_at", TS),
        sa.Column("created_at", TS, server_default=sa.func.now()),
    )
    op.create_table(
        "notifications",
        sa.Column("id", U, primary_key=True),
        sa.Column("user_id", U, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("body", sa.Text()),
        sa.Column("link", sa.String(500)),
        sa.Column("created_at", TS, server_default=sa.func.now(), index=True),
        sa.Column("read_at", TS),
        sa.Column("email_status", sa.String(16), index=True),
        sa.Column("email_error", sa.Text()),
    )
    op.create_table(
        "mail_accounts",
        sa.Column("id", U, primary_key=True),
        sa.Column("user_id", U, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255)),
        sa.Column("refresh_token_enc", sa.Text(), nullable=False),
        sa.Column("access_token_enc", sa.Text()),
        sa.Column("access_expires_at", TS),
        sa.Column("connected_at", TS, server_default=sa.func.now()),
        sa.Column("last_error", sa.Text()),
    )
    op.create_table(
        "mail_templates",
        sa.Column("id", U, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("subject", sa.String(500)),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("owner_user_id", U, sa.ForeignKey("users.id", ondelete="SET NULL"), index=True),
        sa.Column("shared", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", TS, server_default=sa.func.now()),
        sa.Column("updated_at", TS, server_default=sa.func.now()),
    )
    op.create_table(
        "mail_merges",
        sa.Column("id", U, primary_key=True),
        sa.Column("created_by_user_id", U, sa.ForeignKey("users.id", ondelete="SET NULL"), index=True),
        sa.Column("output", sa.String(16), nullable=False),
        sa.Column("source_label", sa.String(300)),
        sa.Column("subject", sa.String(500)),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("from_email", sa.String(255)),
        sa.Column("cc", sa.String(500)),
        sa.Column("bcc", sa.String(500)),
        sa.Column("record_history", sa.String(16), nullable=False, server_default="email_full"),
        sa.Column("history_regarding", sa.String(300)),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued", index=True),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", TS, server_default=sa.func.now(), index=True),
        sa.Column("finished_at", TS),
    )
    op.create_table(
        "mail_merge_recipients",
        sa.Column("id", U, primary_key=True),
        sa.Column("merge_id", U, sa.ForeignKey("mail_merges.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("contact_id", U, sa.ForeignKey("contacts.id", ondelete="SET NULL"), index=True),
        sa.Column("email", sa.String(320)),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued", index=True),
        sa.Column("error", sa.Text()),
        sa.Column("sent_at", TS),
    )
    op.create_table(
        "mail_attachments",
        sa.Column("id", U, primary_key=True),
        sa.Column("merge_id", U, sa.ForeignKey("mail_merges.id", ondelete="CASCADE"), index=True),
        sa.Column("uploaded_by_user_id", U, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False, server_default="application/octet-stream"),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", TS, server_default=sa.func.now()),
    )


def downgrade() -> None:
    for t in ("mail_attachments", "mail_merge_recipients", "mail_merges", "mail_templates", "mail_accounts",
              "notifications", "reminders"):
        op.drop_table(t)
