"""A VAT number on each booking (FIN-008), remembered for the client's next booking.

Revision ID: 0069
Revises: 0068
Create Date: 2026-11-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0069"
down_revision: str | None = "0068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_deals", sa.Column("vat_number", sa.String(40)))


def downgrade() -> None:
    op.drop_column("sales_deals", "vat_number")
