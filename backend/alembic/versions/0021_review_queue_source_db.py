"""Add review_queue.source_db - Phase 1 of scoping automations by
database/rep (see app/models/review_queue.py's docstring on the column).
Backfills existing rows from their linked contact/company/activity where
resolvable, so historical items aren't silently unscoped.

Revision ID: 0021
Revises: 0020
Create Date: 2026-09-23
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("review_queue", sa.Column("source_db", sa.String(32), nullable=True))
    op.create_index("ix_review_queue_source_db", "review_queue", ["source_db"])

    # Backfill: resolve each existing row's source_db from whichever
    # entity it points at - contact/company directly via entity_id, or
    # (for followup_due, which points at an Activity) via that Activity's
    # own contact_id/company_id. Anything left NULL (e.g. bounce_unmatched
    # with no entity at all) stays NULL - correct, not a gap: there was
    # never a resolvable database for it.
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE review_queue rq SET source_db = c.source_db
        FROM contacts c
        WHERE rq.entity_type = 'contact' AND rq.entity_id = c.id AND rq.source_db IS NULL
    """))
    conn.execute(sa.text("""
        UPDATE review_queue rq SET source_db = co.source_db
        FROM companies co
        WHERE rq.entity_type = 'company' AND rq.entity_id = co.id AND rq.source_db IS NULL
    """))
    conn.execute(sa.text("""
        UPDATE review_queue rq SET source_db = a.source_db
        FROM activities a
        WHERE rq.entity_type = 'activity' AND rq.entity_id = a.id AND rq.source_db IS NULL
    """))


def downgrade() -> None:
    op.drop_index("ix_review_queue_source_db", table_name="review_queue")
    op.drop_column("review_queue", "source_db")
