"""Link bookings to their Xero invoice (xero_invoice_id), and keep what each invoice says it is for.

Revision ID: 0031
Revises: 0030
Create Date: 2026-10-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("xero_invoices", sa.Column("line_text", sa.Text()))
    op.add_column("xero_invoices", sa.Column("currency_rate", sa.Numeric(14, 6)))
    op.add_column("sales_orders", sa.Column("xero_invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("xero_invoices.id", ondelete="SET NULL")))
    op.add_column("sales_orders", sa.Column("xero_link_source", sa.String(16)))
    op.add_column("sales_orders", sa.Column("xero_linked_at", sa.DateTime(timezone=True)))
    op.create_index("ix_sales_orders_xero_invoice_id", "sales_orders", ["xero_invoice_id"])


def downgrade() -> None:
    op.drop_index("ix_sales_orders_xero_invoice_id", table_name="sales_orders")
    op.drop_column("sales_orders", "xero_linked_at")
    op.drop_column("sales_orders", "xero_link_source")
    op.drop_column("sales_orders", "xero_invoice_id")
    op.drop_column("xero_invoices", "currency_rate")
    op.drop_column("xero_invoices", "line_text")
