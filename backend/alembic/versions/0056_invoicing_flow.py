"""Invoicing flow from the 15 Oct call: when to invoice, invoice reminders, unlocking, the client's copy contact,
invoice currency, terms per publication.

Revision ID: 0056
Revises: 0055
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0056"
down_revision: str | None = "0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_deals", sa.Column("invoice_on", sa.Date()))
    op.add_column("sales_deals", sa.Column("invoice_instructions", sa.Text()))
    op.add_column("sales_deals", sa.Column("invoice_currency", sa.String(3), nullable=False, server_default="GBP"))
    op.add_column("sales_deals", sa.Column("copy_contact_name", sa.String(200)))
    op.add_column("sales_deals", sa.Column("copy_contact_email", sa.String(320)))
    op.add_column("sales_deals", sa.Column("unlocked_at", sa.DateTime(timezone=True)))
    op.add_column("sales_deals", sa.Column("unlocked_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")))
    # "Up front" was the old name for invoicing straight away; "as agreed" is now a set date or the instructions box.
    op.execute("UPDATE sales_deals SET invoice_plan = 'asap' WHERE invoice_plan IN ('upfront', 'custom')")
    op.add_column("sales_orders", sa.Column("invoice_due_on", sa.Date()))   # set by accounts ("remind me on"); wins over the booking's rule
    op.add_column("deal_settings", sa.Column("terms_by_title", postgresql.JSONB(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("deal_settings", "terms_by_title")
    op.drop_column("sales_orders", "invoice_due_on")
    for c in ("unlocked_by_user_id", "unlocked_at", "copy_contact_email", "copy_contact_name", "invoice_currency",
              "invoice_instructions", "invoice_on"):
        op.drop_column("sales_deals", c)
