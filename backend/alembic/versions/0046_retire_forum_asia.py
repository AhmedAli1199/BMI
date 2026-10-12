"""OBH Forum Asia no longer runs (Matt, 8 Oct 2026): retire the title. Its old bookings stay; it leaves the pickers.

Revision ID: 0046
Revises: 0045
"""
from __future__ import annotations

from alembic import op

revision: str = "0046"
down_revision: str | None = "0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE sales_titles SET active = false WHERE slug = 'obh-forum-asia'")


def downgrade() -> None:
    op.execute("UPDATE sales_titles SET active = true WHERE slug = 'obh-forum-asia'")
