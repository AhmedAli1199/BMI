"""Cards from someone's email belong to that person: email_signals.mailbox, and an owner on waiting cards.

New signals record whose inbox they were read from, and their cards go to that person. Cards already waiting get
an owner from the contact's or company's record manager (the inbox wasn't recorded before); with none, only
administrators see them.

Revision ID: 0073
Revises: 0072
Create Date: 2026-11-10
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0073"
down_revision: str | None = "0072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("email_signals", sa.Column("mailbox", sa.String(320)))
    op.execute("""
        UPDATE review_queue rq
           SET payload = rq.payload || jsonb_build_object('owner_user_id', COALESCE(c.owner_user_id, co.owner_user_id)::text)
          FROM contacts c LEFT JOIN companies co ON co.id = c.company_id
         WHERE rq.kind IN ('signal_trigger', 'personal_touchpoint_due') AND rq.status = 'pending'
           AND rq.entity_type = 'contact' AND rq.entity_id = c.id
           AND COALESCE(rq.payload ->> 'owner_user_id', '') = ''
           AND COALESCE(c.owner_user_id, co.owner_user_id) IS NOT NULL
    """)
    op.execute("""
        UPDATE review_queue rq
           SET payload = rq.payload || jsonb_build_object('owner_user_id',
                 COALESCE(a.created_by_user_id, c.owner_user_id, co.owner_user_id)::text)
          FROM activities a LEFT JOIN contacts c ON c.id = a.contact_id LEFT JOIN companies co ON co.id = a.company_id
         WHERE rq.kind = 'followup_due' AND rq.status = 'pending' AND rq.entity_id = a.id
           AND COALESCE(rq.payload ->> 'owner_user_id', '') = ''
           AND COALESCE(a.created_by_user_id, c.owner_user_id, co.owner_user_id) IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_column("email_signals", "mailbox")
