"""Dates before 2000 can't be right: clear them and flag the row to check (app/core/dates.py).

They came from the order register sheets - a cell formatted as a date that held a small number reads as January
1900 - and made the app reason from them ("no spend found since 1898", "invoiced 46,314 days after the booking").
A booking date or invoice date like that is cleared and the item gets a "check this row" note saying what it
said, so someone types the real one; other item dates are just cleared. A booking (several items) must keep a
date, so it takes the day it was entered. Invoice-to-booking questions still waiting that were worked out from
such a date are removed; the next scan asks them again with the date cleared.

Revision ID: 0068
Revises: 0067
Create Date: 2026-10-26
"""
from __future__ import annotations

from alembic import op

revision: str = "0068"
down_revision: str | None = "0067"
branch_labels = None
depends_on = None

EARLIEST = "2000-01-01"


def _flag(column: str, what: str) -> None:
    op.execute(f"""
        UPDATE sales_orders
           SET import_warning = concat_ws('; ', nullif(import_warning, ''),
                   'the {what} read as ' || to_char({column}, 'FMDD Mon YYYY') || ', which can''t be right - type the real date'),
               {column} = NULL
         WHERE {column} < DATE '{EARLIEST}'
    """)


def upgrade() -> None:
    _flag("booked_on", "booking date")
    _flag("invoiced_on", "invoice date")
    for column in ("item_date", "copy_due", "invoice_due_on"):
        op.execute(f"UPDATE sales_orders SET {column} = NULL WHERE {column} < DATE '{EARLIEST}'")
    op.execute(f"UPDATE sales_deals SET booked_on = created_at::date WHERE booked_on < DATE '{EARLIEST}'")
    op.execute(f"UPDATE sales_deals SET invoice_on = NULL WHERE invoice_on < DATE '{EARLIEST}'")
    op.execute("""
        DELETE FROM review_queue
         WHERE kind = 'sor_invoice_match' AND status = 'pending'
           AND payload::text ~ '"booked_on": "1[0-9]{3}-'
    """)


def downgrade() -> None:
    pass   # the cleared dates were wrong; there is nothing to put back
