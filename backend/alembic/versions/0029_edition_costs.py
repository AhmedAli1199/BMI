"""Event cost / P&L lines per edition.

Revision ID: 0029
Revises: 0028
Create Date: 2026-10-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels = None
depends_on = None

U = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "sales_edition_costs",
        sa.Column("id", U, primary_key=True),
        sa.Column("edition_id", U, sa.ForeignKey("sales_editions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("kind", sa.String(16), nullable=False, server_default="cost"),
        sa.Column("label", sa.String(500), nullable=False),
        sa.Column("amount_gbp", sa.Numeric(12, 2)),
        sa.Column("amount_inc_vat_gbp", sa.Numeric(12, 2)),
        sa.Column("section", sa.String(300)),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("source_row", sa.Integer),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("sales_edition_costs")
