"""Rate card sizes, page counts and each brand's own sections; costs on any edition
with parts, categories, budgets and the booking a cost is for.

Revision ID: 0044
Revises: 0043
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0044"
down_revision: str | None = "0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_rates", sa.Column("width", sa.Numeric(8, 2)))
    op.add_column("sales_rates", sa.Column("height", sa.Numeric(8, 2)))
    op.add_column("sales_rates", sa.Column("size_unit", sa.String(4)))
    op.add_column("sales_rates", sa.Column("bleed_mm", sa.Numeric(5, 2)))
    op.add_column("sales_rates", sa.Column("pages", sa.Numeric(6, 2)))
    op.create_table(
        "rate_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("brand", sa.String(10), nullable=False, index=True),
        sa.Column("key", sa.String(20), nullable=False),
        sa.Column("label", sa.String(80), nullable=False),
        sa.Column("hint", sa.String(300)),
        sa.Column("title_slug", sa.String(60)),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("brand", "key", name="uq_rate_sections_brand_key"),
    )
    op.add_column("sales_edition_costs", sa.Column("category", sa.String(30)))
    op.add_column("sales_edition_costs", sa.Column("budget_gbp", sa.Numeric(12, 2)))
    op.add_column("sales_edition_costs", sa.Column("order_id", postgresql.UUID(as_uuid=True),
                                                   sa.ForeignKey("sales_orders.id", ondelete="SET NULL"), index=True))


def downgrade() -> None:
    op.drop_column("sales_edition_costs", "order_id")
    op.drop_column("sales_edition_costs", "budget_gbp")
    op.drop_column("sales_edition_costs", "category")
    op.drop_table("rate_sections")
    for c in ("pages", "bleed_mm", "size_unit", "height", "width"):
        op.drop_column("sales_rates", c)
