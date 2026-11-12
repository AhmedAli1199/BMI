"""The booking form's Publication drop-down in BMI's words (Craig, 12 Nov): booking_products, each filed under an
existing sales title. Also the OBH Client Solus Email price (£2,990) Craig sent, for each year OBH has prices.

Revision ID: 0076
Revises: 0075
Create Date: 2026-11-12
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0076"
down_revision: str | None = "0075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "booking_products",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("group_label", sa.String(120), nullable=False, server_default=""),
        sa.Column("title_id", UUID(as_uuid=True), sa.ForeignKey("sales_titles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rate_sections", JSONB, nullable=False, server_default="[]"),
        sa.Column("rate_words", JSONB, nullable=False, server_default="[]"),
        sa.Column("rate_exclude", JSONB, nullable=False, server_default="[]"),
        sa.Column("booked_by", sa.String(10), nullable=False, server_default="issue"),
        sa.Column("edition_words", JSONB, nullable=False, server_default="[]"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="100"),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    from sqlalchemy.orm import Session

    from app.sales.booking_products import seed
    db = Session(bind=op.get_bind())
    seed(db)
    db.flush()
    conn = op.get_bind()
    web = conn.execute(sa.text("SELECT id FROM sales_titles WHERE slug = 'obh-web'")).scalar()
    if web:
        years = [y for (y,) in conn.execute(sa.text("SELECT DISTINCT year FROM sales_rates WHERE title_id = :t"), {"t": web})]
        for y in years:
            conn.execute(sa.text("""
                INSERT INTO sales_rates (id, title_id, year, section, product, price_type, price_gbp, unit, aliases, notes,
                                         sort_order, needs_check, source, archived, created_at, updated_at)
                SELECT :id, :t, :y, 'newsletter', 'Client solus email', 'fixed', 2990, 'each', '["Solus email"]'::jsonb,
                       'From Craig McQuinn, 12 Nov 2026', 900, true, 'Craig McQuinn, 12 Nov 2026', false, now(), now()
                WHERE NOT EXISTS (SELECT 1 FROM sales_rates WHERE title_id = :t AND year = :y AND section = 'newsletter'
                                  AND lower(product) IN ('client solus email', 'solus email', 'dedicated email'))
            """), {"id": uuid.uuid4(), "t": web, "y": y})


def downgrade() -> None:
    op.drop_table("booking_products")
