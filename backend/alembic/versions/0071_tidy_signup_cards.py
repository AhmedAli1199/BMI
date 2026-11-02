"""Subscription sign-up cards already waiting get the tidy layout: the key details on the card, all their answers
behind "See all their answers" (app/automations/subscription_forms.py refresh_pending).

Revision ID: 0071
Revises: 0070
Create Date: 2026-11-02
"""
from __future__ import annotations

import logging

from alembic import op
from sqlalchemy.orm import Session

revision: str = "0071"
down_revision: str | None = "0070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    try:
        from app.automations.subscription_forms import refresh_pending
        db = Session(bind=op.get_bind())
        refresh_pending(db)
        db.flush()
    except Exception:   # only tidies how waiting cards look; never block a deploy over it
        logging.getLogger("alembic").warning("sign-up cards weren't tidied; new ones still are")


def downgrade() -> None:
    pass
