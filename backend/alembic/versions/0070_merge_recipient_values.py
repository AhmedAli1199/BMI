"""Each mail merge recipient's own merge fields that aren't on their record (SALES-003: their advert's page).

Revision ID: 0070
Revises: 0069
Create Date: 2026-11-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0070"
down_revision: str | None = "0069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mail_merge_recipients", sa.Column("values", postgresql.JSONB(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("mail_merge_recipients", "values")
