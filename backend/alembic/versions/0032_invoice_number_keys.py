"""Recompute each Xero invoice's comparison key with the new invoice-number rules
(case, dashes, spaces, leading zeros and a spelled-out "no." no longer matter) -
see app/sales/invoice_numbers.py. Bookings are linked on the next sync or matching run.

Revision ID: 0032
Revises: 0031
Create Date: 2026-10-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text(r"""
        UPDATE xero_invoices SET number_key = NULLIF(
            regexp_replace(
              regexp_replace(
                regexp_replace(upper(invoice_number), '\m(NO|NUM|NUMBER|NR)\M\.?\s*(?=[0-9])', '', 'g'),
                '[^A-Z0-9]', '', 'g'),
              '(^|[A-Z])0+([0-9])', '\1\2', 'g'), '')
        WHERE invoice_number IS NOT NULL
    """))


def downgrade() -> None:
    op.execute(sa.text(r"UPDATE xero_invoices SET number_key = NULLIF(upper(replace(invoice_number, ' ', '')), '') WHERE invoice_number IS NOT NULL"))
