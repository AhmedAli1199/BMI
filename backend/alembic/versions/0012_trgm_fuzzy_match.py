"""Enable pg_trgm + trigram indexes on contacts.full_name and
companies.name - powers CS-004 (duplicate/moved-person detection) and the
name-matching step in the business-card and returned-copy automations
(app/automations/vision_intake.py's match_contact_by_name_company()).

The `%` similarity operator and similarity()/word_similarity() functions
this enables can use a GIN trigram index for fast "find rows similar to
this text" lookups - a plain btree index is useless for fuzzy matching
(same problem as ILIKE '%term%' search, already flagged in BACKLOG.md's
performance section).

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-18
"""
from __future__ import annotations

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE INDEX ix_contacts_full_name_trgm ON contacts USING gin (full_name gin_trgm_ops)")
    op.execute("CREATE INDEX ix_companies_name_trgm ON companies USING gin (name gin_trgm_ops)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_companies_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_contacts_full_name_trgm")
    # Deliberately not dropping the pg_trgm extension itself on downgrade -
    # another feature (search, per BACKLOG.md) may come to depend on it
    # independently, and DROP EXTENSION would cascade-fail if anything else
    # is using it by then.
