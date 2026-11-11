"""BMI calls the Business database "TBTM" (Craig, feedback #28): rename it where the Brain shows it.

Only a publication called just "Business", or "The Business Travel Magazine"/"Business Travel...", is renamed.

Revision ID: 0075
Revises: 0074
Create Date: 2026-11-11
"""
from __future__ import annotations

from alembic import op

revision: str = "0075"
down_revision: str | None = "0074"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE publications SET name = 'TBTM'
        WHERE lower(trim(name)) IN ('business', 'business travel', 'the business travel magazine', 'business travel magazine')
    """)


def downgrade() -> None:
    pass   # the old name isn't kept; rename it back by hand if ever needed
