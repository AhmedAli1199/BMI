"""Accounts permission on users; production/accounts copies on confirmations.

Revision ID: 0050
Revises: 0049
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0050"
down_revision: str | None = "0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("can_approve_bookings", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("deal_settings", sa.Column("production_emails", sa.Text(), nullable=False, server_default=""))
    op.add_column("deal_settings", sa.Column("accounts_emails", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("deal_settings", "accounts_emails")
    op.drop_column("deal_settings", "production_emails")
    op.drop_column("users", "can_approve_bookings")
