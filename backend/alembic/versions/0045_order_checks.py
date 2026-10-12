"""Accounts check on orders: who checked an order before its confirmation went out, or what needs fixing.

Revision ID: 0045
Revises: 0044
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0045"
down_revision: str | None = "0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_deals", sa.Column("checked_at", sa.DateTime(timezone=True)))
    op.add_column("sales_deals", sa.Column("checked_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")))
    op.add_column("sales_deals", sa.Column("check_note", sa.String(500)))
    # Orders made before the check existed aren't held up: they count as already checked.
    op.execute("UPDATE sales_deals SET checked_at = COALESCE(sent_at, confirmed_at, created_at, now())")


def downgrade() -> None:
    for c in ("check_note", "checked_by_user_id", "checked_at"):
        op.drop_column("sales_deals", c)
