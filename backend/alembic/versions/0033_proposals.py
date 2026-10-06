"""Proposals (SALES-020 builder / SALES-009 logging). See app/models/proposal.py.

Revision ID: 0033
Revises: 0032
Create Date: 2026-10-08
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0033"
down_revision: str | None = "0032"
branch_labels = None
depends_on = None

U = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "proposals",
        sa.Column("id", U, primary_key=True),
        sa.Column("company_id", U, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("contact_id", U, sa.ForeignKey("contacts.id", ondelete="SET NULL"), index=True),
        sa.Column("title_id", U, sa.ForeignKey("sales_titles.id", ondelete="SET NULL"), index=True),
        sa.Column("template", sa.String(8), nullable=False),
        sa.Column("campaign_name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="draft", index=True),
        sa.Column("sections", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("lines", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("total_gbp", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("context", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("flags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("drafted_by", sa.String(10), nullable=False, server_default="template"),
        sa.Column("created_by_user_id", U, sa.ForeignKey("users.id", ondelete="SET NULL"), index=True),
        sa.Column("sent_at", TS),
        sa.Column("sent_via", sa.String(16)),
        sa.Column("logged_note_id", U),
        sa.Column("follow_up_reminder_id", U),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", TS, server_default=sa.func.now()),
        sa.Column("updated_at", TS, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("proposals")
