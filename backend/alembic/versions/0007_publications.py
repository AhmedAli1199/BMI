"""publications table - the "add a new database" feature.

A row here does NOT create a new Postgres database - `slug` is exactly
what's stored in every other table's source_db column (see
app/models/publication.py's docstring). Seeds the three titles that were
previously hardcoded in the frontend (publication-switcher.tsx,
publication-quick-filter.tsx, the dashboard's magazine tiles), preserving
their existing color/icon so nothing visually changes for them.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-14
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import column, table

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels = None
depends_on = None

publications_table = table(
    "publications",
    column("id", postgresql.UUID(as_uuid=True)),
    column("slug", sa.String),
    column("name", sa.String),
    column("description", sa.String),
    column("color", sa.String),
    column("icon", sa.String),
)


def upgrade() -> None:
    op.create_table(
        "publications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column("color", sa.String(length=32), nullable=False, server_default="slate"),
        sa.Column("icon", sa.String(length=32), nullable=False, server_default="newspaper"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_publications_slug", "publications", ["slug"])

    op.bulk_insert(
        publications_table,
        [
            {
                "id": uuid.uuid4(),
                "slug": "onboard",
                "name": "Onboard Hospitality",
                "description": "Inflight catering, retail & passenger experience",
                "color": "blue",
                "icon": "plane",
            },
            {
                "id": uuid.uuid4(),
                "slug": "sellingtravel",
                "name": "Selling Travel",
                "description": "UK travel trade, agents & destination guides",
                "color": "emerald",
                "icon": "compass",
            },
            {
                "id": uuid.uuid4(),
                "slug": "prospects",
                "name": "Prospects Database",
                "description": "Unclaimed prospects & automated lead discovery",
                "color": "amber",
                "icon": "sparkles",
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_publications_slug", table_name="publications")
    op.drop_table("publications")
