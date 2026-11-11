"""Publication short codes (OBH, TBTM...) and an end date on booked items (digital runs from one date to another).

Craig's feedback #25 and #26: issues listed as BMI names them ("OBH108"), and digital items booked with From and To
dates instead of issues. Codes start as guesses from the publication's name, changeable on the Rate card page.

Revision ID: 0074
Revises: 0073
Create Date: 2026-11-11
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0074"
down_revision: str | None = "0073"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.sales.title_codes import guess

    op.add_column("sales_titles", sa.Column("code", sa.String(24)))
    op.add_column("sales_orders", sa.Column("item_end", sa.Date()))
    conn = op.get_bind()
    for tid, slug, name in conn.execute(sa.text("SELECT id, slug, name FROM sales_titles")).all():
        conn.execute(sa.text("UPDATE sales_titles SET code = :c WHERE id = :i"), {"c": guess(slug, name)[:24], "i": tid})


def downgrade() -> None:
    op.drop_column("sales_orders", "item_end")
    op.drop_column("sales_titles", "code")
