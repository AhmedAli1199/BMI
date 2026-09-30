"""Sales orders: order_ref (ticket/order numbers that aren't BMI
invoices), status_reason (the sheet text that made a row cancelled /
contra / moved) and extra (sheet columns only some titles have - Seats,
Table no., Paid?, Travel Planner/Online split...).

Revision ID: 0025
Revises: 0024
Create Date: 2026-09-28
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_orders", sa.Column("order_ref", sa.String(60)))
    op.add_column("sales_orders", sa.Column("status_reason", sa.Text()))
    op.add_column("sales_orders", sa.Column("extra", postgresql.JSONB(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("sales_orders", "extra")
    op.drop_column("sales_orders", "status_reason")
    op.drop_column("sales_orders", "order_ref")
