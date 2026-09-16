"""Give History and Activity real write paths: created_by_user_id + is_private
on all three interaction tables (notes already had is_private), plus a
simple recurrence field on activities.

Until now, activities (2,131 real migrated rows - Act!'s calendar/task
data) had zero API exposure, and history had none either - the "Quick
Touchpoint" buttons on a contact just wrote a Note. This migration adds
what's needed to let the CRM create real History and Activity rows going
forward, attributed to whichever of our own users logged them (nullable,
since migrated rows have no such user).

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-17
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "activities",
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column("activities", sa.Column("is_private", sa.Boolean(), nullable=False, server_default=sa.false()))
    # Simple enum, not a full RRULE - "never" covers every migrated row.
    op.add_column(
        "activities", sa.Column("recurrence", sa.String(length=20), nullable=False, server_default="never")
    )

    op.add_column(
        "history_entries",
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column("history_entries", sa.Column("is_private", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.add_column(
        "notes",
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )

    op.create_index("ix_activities_created_by_user_id", "activities", ["created_by_user_id"])
    op.create_index("ix_history_entries_created_by_user_id", "history_entries", ["created_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_history_entries_created_by_user_id", table_name="history_entries")
    op.drop_index("ix_activities_created_by_user_id", table_name="activities")

    op.drop_column("notes", "created_by_user_id")

    op.drop_column("history_entries", "is_private")
    op.drop_column("history_entries", "created_by_user_id")

    op.drop_column("activities", "recurrence")
    op.drop_column("activities", "is_private")
    op.drop_column("activities", "created_by_user_id")
