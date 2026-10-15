"""Hand-offs to editorial and production: the routing table and what was sent for each booking line.

Revision ID: 0058
Revises: 0057
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0058"
down_revision: str | None = "0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("deal_settings", sa.Column("handoff_routes", postgresql.JSONB(), nullable=False, server_default="{}"))
    op.add_column("sales_deals", sa.Column("handoff_log", postgresql.JSONB(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("sales_deals", "handoff_log")
    op.drop_column("deal_settings", "handoff_routes")
