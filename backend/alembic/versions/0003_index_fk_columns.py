"""Add indexes to foreign-key columns that were missing them.

Contact.company_id in particular was unindexed - fine for the earlier
CRUD endpoints (single-row lookups, or a subquery run only for a page
of 50 rows), but the new dashboard "biggest accounts" query sorts ALL
~14k companies by a correlated contact-count subquery, which without
this index means a full sequential scan of the ~118k-row contacts
table per company: on the order of a billion row comparisons. That's
what was timing out (502s / HeadersTimeoutError) right after login,
since the dashboard is the first page rendered post-login.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-13
"""
from __future__ import annotations

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels = None
depends_on = None

INDEXES = [
    ("ix_contacts_company_id", "contacts", "company_id"),
    ("ix_companies_parent_company_id", "companies", "parent_company_id"),
    ("ix_groups_parent_group_id", "groups", "parent_group_id"),
    ("ix_activities_contact_id", "activities", "contact_id"),
    ("ix_activities_company_id", "activities", "company_id"),
    ("ix_opportunities_contact_id", "opportunities", "contact_id"),
    ("ix_opportunities_company_id", "opportunities", "company_id"),
    ("ix_addresses_contact_id", "addresses", "contact_id"),
    ("ix_addresses_company_id", "addresses", "company_id"),
    ("ix_phones_contact_id", "phones", "contact_id"),
    ("ix_phones_company_id", "phones", "company_id"),
    ("ix_emails_contact_id", "emails", "contact_id"),
    ("ix_emails_company_id", "emails", "company_id"),
]


def upgrade() -> None:
    for name, table, column in INDEXES:
        op.create_index(name, table, [column], unique=False)


def downgrade() -> None:
    for name, table, _column in INDEXES:
        op.drop_index(name, table_name=table)
