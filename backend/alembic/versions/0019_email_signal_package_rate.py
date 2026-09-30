"""Add email_signals.package_offered/rate_offered - verbatim package/rate
text captured alongside a signal, when the message actually states one.
See app/models/email_signal.py and app/automations/email_summary.py.

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("email_signals", sa.Column("package_offered", sa.String(256), nullable=True))
    op.add_column("email_signals", sa.Column("rate_offered", sa.String(256), nullable=True))


def downgrade() -> None:
    op.drop_column("email_signals", "rate_offered")
    op.drop_column("email_signals", "package_offered")
