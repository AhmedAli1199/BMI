"""Draft invoices in Xero: the Xero contact chosen for a booking (remembered on the company), and the Xero codes
each publication's invoice lines use.

Revision ID: 0057
Revises: 0056
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0057"
down_revision: str | None = "0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for t in ("sales_deals", "companies"):
        op.add_column(t, sa.Column("xero_contact_id", sa.String(64)))
        op.add_column(t, sa.Column("xero_contact_name", sa.String(255)))
    op.add_column("deal_settings", sa.Column("xero_codes", postgresql.JSONB(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("deal_settings", "xero_codes")
    for t in ("sales_deals", "companies"):
        op.drop_column(t, "xero_contact_name")
        op.drop_column(t, "xero_contact_id")
