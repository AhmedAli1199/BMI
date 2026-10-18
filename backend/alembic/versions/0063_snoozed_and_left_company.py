"""Review cards can be "snoozed", and contacts can be marked as having left their company.

- review_queue.status gains "snoozed": "Remind me on…" / "Not yet - next week" style buttons close a card for now
  without approving or refusing anything, so they no longer count as rejected in the automation stats.
- contacts.has_left: set when someone is confirmed as having left (a departure card's successor is confirmed, or
  "Mark as departed" on the contact). Searchable, exportable and editable in bulk like the other yes/no fields.

Revision ID: 0063
Revises: 0062
Create Date: 2026-10-18
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0063"
down_revision: str | None = "0062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_review_queue_status", "review_queue", type_="check")
    op.create_check_constraint("ck_review_queue_status", "review_queue", "status IN ('pending', 'approved', 'rejected', 'snoozed')")
    op.add_column("contacts", sa.Column("has_left", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("contacts", "has_left")
    op.execute("UPDATE review_queue SET status = 'rejected' WHERE status = 'snoozed'")
    op.drop_constraint("ck_review_queue_status", "review_queue", type_="check")
    op.create_check_constraint("ck_review_queue_status", "review_queue", "status IN ('pending', 'approved', 'rejected')")
