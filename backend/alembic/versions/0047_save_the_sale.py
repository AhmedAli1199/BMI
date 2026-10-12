"""SALES-022: a client's "no" is an email signal (type "decline") with the reason.

Revision ID: 0047
Revises: 0046
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0047"
down_revision: str | None = "0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_email_signals_type", "email_signals", type_="check")
    op.create_check_constraint("ck_email_signals_type", "email_signals",
                               "signal_type IN ('budget_window', 'renewal_date', 'promised_callback', 'personal_touchpoint', 'decline')")
    op.add_column("email_signals", sa.Column("reason", sa.String(20)))


def downgrade() -> None:
    op.drop_column("email_signals", "reason")
    op.execute("DELETE FROM email_signals WHERE signal_type = 'decline'")
    op.drop_constraint("ck_email_signals_type", "email_signals", type_="check")
    op.create_check_constraint("ck_email_signals_type", "email_signals",
                               "signal_type IN ('budget_window', 'renewal_date', 'promised_callback', 'personal_touchpoint')")
