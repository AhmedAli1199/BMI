"""Booking defaults: what every new booking's confirmation starts with.

Revision ID: 0054
Revises: 0053
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0054"
down_revision: str | None = "0053"
branch_labels = None
depends_on = None

COLS = ("default_production_contact", "default_copy_instructions", "default_special_instructions")


def upgrade() -> None:
    for c in COLS:
        op.add_column("deal_settings", sa.Column(c, sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    for c in COLS:
        op.drop_column("deal_settings", c)
