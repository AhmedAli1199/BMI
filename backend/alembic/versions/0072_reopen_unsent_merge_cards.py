"""Cards closed just by pressing "Open as a mail merge", with no mail merge sent from them, go back to waiting.

Until now that button closed the card at once, so looking at a mail merge and not sending it lost the card. The
button now leaves the card waiting, and sending the mail merge closes it (app/api/routes/messaging.py _close_card).
A card counts as sent if its reviewer sent an email mail merge with the card's label after pressing the button.

Revision ID: 0072
Revises: 0071
Create Date: 2026-11-05
"""
from __future__ import annotations

from alembic import op

revision: str = "0072"
down_revision: str | None = "0071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE review_queue rq
           SET status = 'pending', resolved_action = NULL, reviewed_at = NULL, reviewed_by_user_id = NULL, review_note = NULL
         WHERE rq.status = 'approved' AND rq.resolved_action = 'open_merge'
           AND NOT EXISTS (SELECT 1 FROM mail_merges m
                            WHERE m.output = 'email' AND m.created_at >= rq.reviewed_at
                              AND (rq.reviewed_by_user_id IS NULL OR m.created_by_user_id = rq.reviewed_by_user_id)
                              AND m.source_label = rq.payload -> 'merge' ->> 'label')
    """)


def downgrade() -> None:
    pass
