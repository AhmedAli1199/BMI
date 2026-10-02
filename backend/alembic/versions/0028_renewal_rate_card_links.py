"""Rate card and digital-edition links for renewal outreach (SALES-021).

Revision ID: 0028
Revises: 0027
Create Date: 2026-10-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels = None
depends_on = None

U = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.add_column("sales_titles", sa.Column("digital_page_url", sa.String(500)))
    op.add_column("sales_titles", sa.Column("digital_issue_url", sa.String(500)))
    op.add_column("sales_editions", sa.Column("digital_url", sa.String(500)))
    op.create_table(
        "sales_rates",
        sa.Column("id", U, primary_key=True),
        sa.Column("title_id", U, sa.ForeignKey("sales_titles.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("year", sa.Integer, nullable=False, index=True),
        sa.Column("product", sa.String(120), nullable=False),
        sa.Column("price_gbp", sa.Numeric(12, 2), nullable=False),
        sa.Column("notes", sa.String(300)),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("title_id", "year", "product", name="uq_sales_rates_title_year_product"),
    )


def downgrade() -> None:
    op.drop_table("sales_rates")
    op.drop_column("sales_editions", "digital_url")
    op.drop_column("sales_titles", "digital_issue_url")
    op.drop_column("sales_titles", "digital_page_url")
