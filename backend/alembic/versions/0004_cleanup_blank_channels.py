"""Delete already-migrated phone/address/email rows that carry no actual
value - just an Act! type label (e.g. "Fax", "Mobile") with nothing filled
in. Act! keeps one TBL_PHONE/TBL_ADDRESS/TBL_EMAIL row per slot whether or
not it was ever used, and the original ETL migrated all of them verbatim;
this is the one-time cleanup for data already loaded before etl.py's
_migrate_channel started skipping these at the source. See the contact/
company detail page bug report: "Fax:" / "Mobile:" rows with no value, and
several unrelated channels all bare-labeled "Business".

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-13
"""
from __future__ import annotations

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM phones WHERE number IS NULL OR btrim(number) = ''")
    op.execute("DELETE FROM emails WHERE address IS NULL OR btrim(address) = ''")
    op.execute(
        """
        DELETE FROM addresses
        WHERE COALESCE(btrim(line1), '') = ''
          AND COALESCE(btrim(line2), '') = ''
          AND COALESCE(btrim(line3), '') = ''
          AND COALESCE(btrim(city), '') = ''
          AND COALESCE(btrim(state), '') = ''
          AND COALESCE(btrim(postal_code), '') = ''
          AND COALESCE(btrim(country), '') = ''
          AND latitude IS NULL
          AND longitude IS NULL
        """
    )


def downgrade() -> None:
    # Deleted rows aren't recoverable from within Postgres - re-run the ETL
    # from the original Act! .bak backups to restore them if ever needed.
    pass
