"""Proposals across several titles and issues: proposal kind and % off the whole proposal.

Revision ID: 0042
Revises: 0041
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0042"
down_revision: str | None = "0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("proposals", sa.Column("kind", sa.String(12), nullable=False, server_default="issue"))
    op.add_column("proposals", sa.Column("discount_pct", sa.Numeric(6, 4), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("proposals", "discount_pct")
    op.drop_column("proposals", "kind")
