"""Add owner_user_id to contacts and companies - backfilled from Act!'s
MANAGEUSERID ("Record Manager") field via migration/backfill_owner.py, run
once against the restored .bak SQL Server databases (never migrated by the
original ETL). Powers per-salesperson views (the morning follow-up queue,
SALES-013) once populated - null until that backfill script runs.

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contacts", sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_contacts_owner_user_id", "contacts", ["owner_user_id"])
    op.create_foreign_key(
        "fk_contacts_owner_user_id", "contacts", "users", ["owner_user_id"], ["id"]
    )

    op.add_column("companies", sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_companies_owner_user_id", "companies", ["owner_user_id"])
    op.create_foreign_key(
        "fk_companies_owner_user_id", "companies", "users", ["owner_user_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_companies_owner_user_id", "companies", type_="foreignkey")
    op.drop_index("ix_companies_owner_user_id", table_name="companies")
    op.drop_column("companies", "owner_user_id")

    op.drop_constraint("fk_contacts_owner_user_id", "contacts", type_="foreignkey")
    op.drop_index("ix_contacts_owner_user_id", table_name="contacts")
    op.drop_column("contacts", "owner_user_id")
