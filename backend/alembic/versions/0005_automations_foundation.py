"""Foundation columns for the automations/review-queue system.

- contacts.is_unsubscribed: set by the bounce-handling automation on a
  confirmed hard bounce.
- review_queue.resolved_action: the precise action a human took on a
  review item (e.g. "confirm_hard_bounce"), distinct from the coarse
  pending/approved/rejected status - see app/automations/registry.py.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contacts",
        sa.Column("is_unsubscribed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_contacts_is_unsubscribed", "contacts", ["is_unsubscribed"])

    op.add_column("review_queue", sa.Column("resolved_action", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("review_queue", "resolved_action")
    op.drop_index("ix_contacts_is_unsubscribed", table_name="contacts")
    op.drop_column("contacts", "is_unsubscribed")
