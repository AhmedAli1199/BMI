"""Full "nothing missed" gap-fill pass over Act!'s schema, covering every
table/column with real business data connected to contacts/companies/
groups/activities/opportunities that the original migration skipped.

The original ETL only ever queried a narrow slice of Act!'s schema; a few
of its own comments even claimed data didn't exist ("no reliable
Activity->Contact link table") when it actually does, just in tables that
were never queried. This migration adds what's needed to hold it; the
actual backfill is a re-run of migration/etl.py against the .bak (see
migration/README.md). Covers:

- Activity <-> contact/company/group associations + invitees (from
  TBL_CONTACT_ACTIVITY, TBL_COMPANY_ACTIVITY, TBL_GROUP_ACTIVITY,
  TBL_ACCESSOR_ACTIVITY) - fixes activities always landing with
  contact_id/company_id = NULL.
- Attachments (file metadata, not the files themselves - TBL_ATTACHMENT).
- Activity.duration_minutes + organized_by_name (Act!'s DURATION column,
  and a denormalized organizer name via TBL_ACCESSOR - not a `users` FK,
  see activity.py's docstring on why).
- Notes/History entity_type widened to include 'group'/'opportunity'
  (TBL_GROUP_NOTE, TBL_GROUP_HISTORY, TBL_OPPORTUNITY_HISTORY were
  entirely dropped by the "if not entity_id: continue" guard).
- Company.ticker_symbol/sic_code - selected by the ETL from day one but
  never actually written to the row dict (bug fix, not new scope).
- Contact: company_name_freetext, last_results, is_email_opted_out,
  has_bounced, engagement_score - the AEM/bounce fields are directly
  relevant to the CS-001 bounce-handling automation, which currently has
  no historical signal to start from.
- Phone.extension (Act!'s SUFFIX).
- Opportunity.custom_fields (USER1-8 - discover_custom_columns() was only
  ever called for contact/company/group, never opportunity).
- contact_company_links (TBL_COMPANY_CONTACT) - a contact can belong to
  several companies in Act!; Contact.company_id only ever holds one.

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-17
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- Activities: duration + organizer, plus real association data ----
    op.add_column("activities", sa.Column("duration_minutes", sa.Integer(), nullable=True))
    op.add_column("activities", sa.Column("organized_by_name", sa.String(length=256), nullable=True))
    op.add_column("activities", sa.Column("priority", sa.String(length=32), nullable=False, server_default="normal"))

    op.create_table(
        "activity_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("activities.id"), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id"), nullable=False),
        sa.Column("is_invited", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("activity_id", "contact_id", name="uq_activity_contacts"),
    )
    op.create_index("ix_activity_contacts_activity_id", "activity_contacts", ["activity_id"])
    op.create_index("ix_activity_contacts_contact_id", "activity_contacts", ["contact_id"])

    op.create_table(
        "activity_companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("activities.id"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.UniqueConstraint("activity_id", "company_id", name="uq_activity_companies"),
    )
    op.create_index("ix_activity_companies_activity_id", "activity_companies", ["activity_id"])
    op.create_index("ix_activity_companies_company_id", "activity_companies", ["company_id"])

    op.create_table(
        "activity_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("activities.id"), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.UniqueConstraint("activity_id", "group_id", name="uq_activity_groups"),
    )
    op.create_index("ix_activity_groups_activity_id", "activity_groups", ["activity_id"])
    op.create_index("ix_activity_groups_group_id", "activity_groups", ["group_id"])

    op.create_table(
        "activity_invitees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("activities.id"), nullable=False),
        sa.Column("accessor_name", sa.String(length=256), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.UniqueConstraint("activity_id", "accessor_name", name="uq_activity_invitees"),
    )
    op.create_index("ix_activity_invitees_activity_id", "activity_invitees", ["activity_id"])
    op.create_index("ix_activity_invitees_user_id", "activity_invitees", ["user_id"])

    op.create_table(
        "attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_db", sa.String(length=64), nullable=False),
        sa.Column("source_act_id", sa.String(length=64), nullable=False),
        sa.Column("note_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notes.id"), nullable=True),
        sa.Column("history_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("history_entries.id"), nullable=True),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("activities.id"), nullable=True),
        sa.Column("file_name", sa.String(length=512), nullable=True),
        sa.Column("display_name", sa.String(length=512), nullable=True),
        sa.UniqueConstraint("source_db", "source_act_id", name="uq_attachments_source"),
    )
    op.create_index("ix_attachments_source_db", "attachments", ["source_db"])
    op.create_index("ix_attachments_note_id", "attachments", ["note_id"])
    op.create_index("ix_attachments_history_id", "attachments", ["history_id"])
    op.create_index("ix_attachments_activity_id", "attachments", ["activity_id"])

    # ---- Notes/History: widen entity_type to cover group + opportunity ----
    op.drop_constraint("ck_notes_entity_type", "notes", type_="check")
    op.create_check_constraint(
        "ck_notes_entity_type", "notes", "entity_type IN ('contact', 'company', 'group', 'opportunity')"
    )
    op.drop_constraint("ck_history_entity_type", "history_entries", type_="check")
    op.create_check_constraint(
        "ck_history_entity_type",
        "history_entries",
        "entity_type IN ('contact', 'company', 'group', 'opportunity')",
    )

    # ---- Company: ticker/SIC were selected by the ETL but never written ----
    op.add_column("companies", sa.Column("ticker_symbol", sa.String(length=32), nullable=True))
    op.add_column("companies", sa.Column("sic_code", sa.String(length=32), nullable=True))

    # ---- Contact: free-text company, last results, AEM/bounce, engagement ----
    op.add_column("contacts", sa.Column("last_email_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("contacts", sa.Column("company_name_freetext", sa.String(length=256), nullable=True))
    op.add_column("contacts", sa.Column("last_results", sa.String(length=256), nullable=True))
    op.add_column(
        "contacts", sa.Column("is_email_opted_out", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column("contacts", sa.Column("has_bounced", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("contacts", sa.Column("engagement_score", sa.Integer(), nullable=True))

    # ---- Phone: extension (Act!'s SUFFIX) ----
    op.add_column("phones", sa.Column("extension", sa.String(length=32), nullable=True))

    # ---- Opportunity: USER1-8 custom fields, never discovered before ----
    op.add_column(
        "opportunities", sa.Column("custom_fields", postgresql.JSONB(), nullable=False, server_default="{}")
    )

    # ---- Contact <-> Company secondary links (TBL_COMPANY_CONTACT) ----
    op.create_table(
        "contact_company_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("row_source", sa.String(length=1), nullable=True),
        sa.UniqueConstraint("contact_id", "company_id", name="uq_contact_company_links"),
    )
    op.create_index("ix_contact_company_links_contact_id", "contact_company_links", ["contact_id"])
    op.create_index("ix_contact_company_links_company_id", "contact_company_links", ["company_id"])


def downgrade() -> None:
    op.drop_table("contact_company_links")
    op.drop_column("opportunities", "custom_fields")
    op.drop_column("phones", "extension")
    op.drop_column("contacts", "engagement_score")
    op.drop_column("contacts", "has_bounced")
    op.drop_column("contacts", "is_email_opted_out")
    op.drop_column("contacts", "last_results")
    op.drop_column("contacts", "company_name_freetext")
    op.drop_column("contacts", "last_email_date")
    op.drop_column("companies", "sic_code")
    op.drop_column("companies", "ticker_symbol")

    op.drop_constraint("ck_history_entity_type", "history_entries", type_="check")
    op.create_check_constraint(
        "ck_history_entity_type", "history_entries", "entity_type IN ('contact', 'company')"
    )
    op.drop_constraint("ck_notes_entity_type", "notes", type_="check")
    op.create_check_constraint("ck_notes_entity_type", "notes", "entity_type IN ('contact', 'company')")

    op.drop_table("attachments")
    op.drop_table("activity_invitees")
    op.drop_table("activity_groups")
    op.drop_table("activity_companies")
    op.drop_table("activity_contacts")
    op.drop_column("activities", "priority")
    op.drop_column("activities", "organized_by_name")
    op.drop_column("activities", "duration_minutes")
