"""Items still to be allocated on bookings; online booking forms; filler ads on the order register.

Revision ID: 0051
Revises: 0050
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0051"
down_revision: str | None = "0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_deals", sa.Column("unallocated_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("sales_deals", sa.Column("unallocated_gbp", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("sales_deals", sa.Column("allocate_by", sa.Date(), nullable=True))
    op.create_index("ix_sales_deals_unallocated_count", "sales_deals", ["unallocated_count"])
    op.add_column("sales_orders", sa.Column("filler", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        "booking_forms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("source", sa.String(16), nullable=False, server_default="jotform"),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("title_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sales_titles.id", ondelete="SET NULL")),
        sa.Column("edition_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sales_editions.id", ondelete="SET NULL")),
        sa.Column("rate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sales_rates.id", ondelete="SET NULL")),
        sa.Column("description", sa.String(300), nullable=False, server_default=""),
        sa.Column("unit_price", sa.Numeric(12, 2)),
        sa.Column("rep_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sales_reps.id", ondelete="SET NULL")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_received_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("booking_forms")
    op.drop_column("sales_orders", "filler")
    op.drop_index("ix_sales_deals_unallocated_count", "sales_deals")
    op.drop_column("sales_deals", "allocate_by")
    op.drop_column("sales_deals", "unallocated_gbp")
    op.drop_column("sales_deals", "unallocated_count")
