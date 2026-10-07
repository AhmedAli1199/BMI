"""Rate card revamp: brands/sections, ways a price is quoted, offers & discounts,
and price history in field_changes. See app/models/sales.py (SalesRate, RateOffer).

Revision ID: 0035
Revises: 0034
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels = None
depends_on = None

U = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)
J = postgresql.JSONB()

OLD_TYPES = "('contact', 'company', 'sales_order')"
NEW_TYPES = "('contact', 'company', 'sales_order', 'sales_rate', 'rate_offer', 'sales_edition', 'edition_feature')"


def upgrade() -> None:
    op.add_column("sales_rates", sa.Column("section", sa.String(20), nullable=False, server_default="print"))
    op.add_column("sales_rates", sa.Column("price_type", sa.String(10), nullable=False, server_default="fixed"))
    op.add_column("sales_rates", sa.Column("unit", sa.String(10), nullable=False, server_default="each"))
    op.add_column("sales_rates", sa.Column("specs", sa.String(200)))
    op.add_column("sales_rates", sa.Column("aliases", J, nullable=False, server_default="[]"))
    op.add_column("sales_rates", sa.Column("valid_until", sa.Date))
    op.add_column("sales_rates", sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"))
    op.add_column("sales_rates", sa.Column("needs_check", sa.Boolean, nullable=False, server_default=sa.false()))
    op.add_column("sales_rates", sa.Column("source", sa.String(120)))
    op.add_column("sales_rates", sa.Column("archived", sa.Boolean, nullable=False, server_default=sa.false()))
    op.create_index("ix_sales_rates_archived", "sales_rates", ["archived"])
    op.alter_column("sales_rates", "price_gbp", existing_type=sa.Numeric(12, 2), nullable=True)
    op.drop_constraint("uq_sales_rates_title_year_product", "sales_rates", type_="unique")
    op.create_unique_constraint("uq_sales_rates_title_year_section_product", "sales_rates", ["title_id", "year", "section", "product"])

    op.create_table(
        "rate_offers",
        sa.Column("id", U, primary_key=True),
        sa.Column("brand", sa.String(10), nullable=False, index=True),
        sa.Column("year", sa.Integer, nullable=False, index=True),
        sa.Column("kind", sa.String(12), nullable=False, server_default="note"),
        sa.Column("label", sa.String(300), nullable=False),
        sa.Column("details", sa.Text),
        sa.Column("rules", J, nullable=False, server_default="{}"),
        sa.Column("rate_ids", J, nullable=False, server_default="[]"),
        sa.Column("section", sa.String(20)),
        sa.Column("valid_until", sa.Date),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("needs_check", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.drop_constraint("ck_field_changes_entity_type", "field_changes", type_="check")
    op.create_check_constraint("ck_field_changes_entity_type", "field_changes", f"entity_type IN {NEW_TYPES}")


def downgrade() -> None:
    op.execute("DELETE FROM field_changes WHERE entity_type NOT IN " + OLD_TYPES)
    op.drop_constraint("ck_field_changes_entity_type", "field_changes", type_="check")
    op.create_check_constraint("ck_field_changes_entity_type", "field_changes", f"entity_type IN {OLD_TYPES}")
    op.drop_table("rate_offers")
    op.drop_constraint("uq_sales_rates_title_year_section_product", "sales_rates", type_="unique")
    op.create_unique_constraint("uq_sales_rates_title_year_product", "sales_rates", ["title_id", "year", "product"])
    op.execute("DELETE FROM sales_rates WHERE price_gbp IS NULL")
    op.alter_column("sales_rates", "price_gbp", existing_type=sa.Numeric(12, 2), nullable=False)
    op.drop_index("ix_sales_rates_archived", "sales_rates")
    for c in ("archived", "source", "needs_check", "sort_order", "valid_until", "aliases", "specs", "unit", "price_type", "section"):
        op.drop_column("sales_rates", c)
