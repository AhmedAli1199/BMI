"""Sales Order Register: sales_titles, sales_editions, sales_reps,
sales_orders, sales_order_credits - see app/models/sales.py. Also widens field_changes'
entity_type check so order edits get the same per-user audit trail.

Revision ID: 0024
Revises: 0023
Create Date: 2026-09-27
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "sales_titles",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("product_line", sa.String(20), nullable=False, server_default="print"),
        sa.Column("crm_source_db", sa.String(64), nullable=False, server_default="sellingtravel"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "sales_editions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("title_id", UUID, sa.ForeignKey("sales_titles.id"), nullable=False, index=True),
        sa.Column("year", sa.Integer(), nullable=False, index=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("period_label", sa.String(200)),
        sa.Column("edition_date", sa.Date(), index=True),
        sa.Column("kind", sa.String(20), nullable=False, server_default="issue"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("exchange_rate", sa.Numeric(8, 4)),
        sa.Column("target_gbp", sa.Numeric(12, 2)),
        sa.Column("notes", sa.Text()),
        sa.Column("source_file", sa.String(200)),
        sa.Column("source_sheet", sa.String(120)),
        sa.Column("sheet_total_gbp", sa.Numeric(12, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("title_id", "year", "name", name="uq_sales_editions_title_year_name"),
        sa.CheckConstraint("kind IN ('issue', 'month', 'event', 'awards', 'guide')", name="ck_sales_editions_kind"),
        sa.CheckConstraint("status IN ('open', 'closed')", name="ck_sales_editions_status"),
    )
    op.create_table(
        "sales_reps",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("code", sa.String(16), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), index=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("commission_rate", sa.Numeric(5, 4), nullable=False, server_default="0.02"),
    )
    op.create_table(
        "sales_orders",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("edition_id", UUID, sa.ForeignKey("sales_editions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("client_name", sa.String(256), nullable=False, index=True),
        sa.Column("company_id", UUID, sa.ForeignKey("companies.id", ondelete="SET NULL"), index=True),
        sa.Column("match_dismissed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rep_id", UUID, sa.ForeignKey("sales_reps.id"), index=True),
        sa.Column("booked_on", sa.Date(), index=True),
        sa.Column("size", sa.String(120)),
        sa.Column("pages", sa.Numeric(6, 3)),
        sa.Column("series", sa.String(60)),
        sa.Column("position", sa.String(60)),
        sa.Column("rate_usd", sa.Numeric(12, 2)),
        sa.Column("value_gbp", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("agency_commission_gbp", sa.Numeric(12, 2)),
        sa.Column("commission_rate", sa.Numeric(5, 4)),
        sa.Column("invoice_number", sa.String(60), index=True),
        sa.Column("invoice_value_gbp", sa.Numeric(12, 2)),
        sa.Column("invoiced_on", sa.Date()),
        sa.Column("invoice_note", sa.Text()),
        sa.Column("status", sa.String(20), nullable=False, server_default="booked", index=True),
        sa.Column("moved_to_edition_id", UUID, sa.ForeignKey("sales_editions.id", ondelete="SET NULL")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by_user_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("source_file", sa.String(200)),
        sa.Column("source_sheet", sa.String(120)),
        sa.Column("source_row", sa.Integer()),
        sa.Column("import_warning", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('booked', 'cancelled', 'contra', 'moved')", name="ck_sales_orders_status"),
    )
    op.create_table(
        "sales_order_credits",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("order_id", UUID, sa.ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("rep_id", UUID, sa.ForeignKey("sales_reps.id"), nullable=False, index=True),
        sa.Column("amount_gbp", sa.Numeric(12, 2), nullable=False),
        sa.UniqueConstraint("order_id", "rep_id", name="uq_sales_order_credits_order_rep"),
    )
    op.drop_constraint("ck_field_changes_entity_type", "field_changes", type_="check")
    op.create_check_constraint(
        "ck_field_changes_entity_type", "field_changes", "entity_type IN ('contact', 'company', 'sales_order')"
    )


def downgrade() -> None:
    op.execute("DELETE FROM field_changes WHERE entity_type = 'sales_order'")
    op.drop_constraint("ck_field_changes_entity_type", "field_changes", type_="check")
    op.create_check_constraint("ck_field_changes_entity_type", "field_changes", "entity_type IN ('contact', 'company')")
    op.drop_table("sales_order_credits")
    op.drop_table("sales_orders")
    op.drop_table("sales_reps")
    op.drop_table("sales_editions")
    op.drop_table("sales_titles")
