"""Widen every source_db column from varchar(20) to varchar(64).

Found by testing the new "add a database" feature end-to-end: creating a
contact under a freshly-added publication with a longer slug (e.g.
"airline-retail-weekly", 21 chars) hit StringDataRightTruncation because
ProvenanceMixin's source_db column was sized for the three original short
Act! slugs (onboard/prospects/sellingtravel), not an arbitrary new one.
64 matches PUBLICATION_SLUG_PATTERN's max length (see app/api/schemas.py).

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels = None
depends_on = None

TABLES = [
    "activities",
    "addresses",
    "companies",
    "contacts",
    "emails",
    "groups",
    "history_entries",
    "notes",
    "opportunities",
    "phones",
]


def upgrade() -> None:
    for table in TABLES:
        op.alter_column(table, "source_db", type_=sa.String(length=64), existing_nullable=False)


def downgrade() -> None:
    # Not reversible if any row now has a source_db longer than 20 chars -
    # intentionally left as a no-op rather than silently truncating data.
    pass
