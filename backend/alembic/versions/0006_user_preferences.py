"""Per-user app preferences (see app/preferences.py's registry).

users.preferences: a JSONB blob of {preference_key: option_value}. Stored
sparse - a missing key means "use the default from the registry", so
adding a brand-new preference later never requires a migration.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("preferences", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("users", "preferences")
