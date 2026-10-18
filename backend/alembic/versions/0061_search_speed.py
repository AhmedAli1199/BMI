"""Faster contact search and lists at production size (~118k contacts).

The quick search box (app/services/contact_lookup.py `_quick_match`) looks for each word in names, job, company,
email, phone, address and the Act! custom fields. These trigram indexes let each of those lookups use an index
instead of reading every row; the expressions must stay exactly as written in contact_lookup.py (SEARCH_* constants).
Also: the contacts list's default order (last name, first name) and the calendar list's order (start date).

Revision ID: 0061
Revises: 0060
Create Date: 2026-10-18
"""
from __future__ import annotations

from alembic import op

revision: str = "0061"
down_revision: str | None = "0060"
branch_labels = None
depends_on = None

CONTACT_TEXT = ("(coalesce(full_name, '') || ' ' || coalesce(first_name, '') || ' ' || coalesce(last_name, '') || ' ' || "
                "coalesce(job_title, '') || ' ' || coalesce(company_name_freetext, '') || ' ' || coalesce(department, '') || ' ' || "
                "coalesce(category, '') || ' ' || coalesce(referred_by, ''))")
ADDRESS_TEXT = ("(coalesce(line1, '') || ' ' || coalesce(line2, '') || ' ' || coalesce(line3, '') || ' ' || coalesce(city, '') || ' ' || "
                "coalesce(state, '') || ' ' || coalesce(postal_code, '') || ' ' || coalesce(country, ''))")

INDEXES = {
    "ix_contacts_search_text_trgm": f"contacts USING gin ({CONTACT_TEXT} gin_trgm_ops)",
    "ix_contacts_custom_fields_trgm": "contacts USING gin ((custom_fields::text) gin_trgm_ops)",
    "ix_emails_address_trgm": "emails USING gin (address gin_trgm_ops)",
    "ix_phones_number_trgm": "phones USING gin (number gin_trgm_ops)",
    "ix_phones_digits_trgm": "phones USING gin ((regexp_replace(number, '\\D', '', 'g')) gin_trgm_ops)",
    "ix_addresses_search_text_trgm": f"addresses USING gin ({ADDRESS_TEXT} gin_trgm_ops)",
    "ix_contacts_db_name": "contacts (source_db, last_name, first_name)",
    "ix_contacts_name": "contacts (last_name, first_name)",
    "ix_companies_db_name": "companies (source_db, name)",
    "ix_activities_start_at": "activities (start_at)",
}


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for name, spec in INDEXES.items():
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {spec}")


def downgrade() -> None:
    for name in INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {name}")
