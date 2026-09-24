"""Add field_changes - per-user audit trail for direct Contact/Company
field edits. See app/models/field_change.py for the full design note.

Revision ID: 0022
Revises: 0021
Create Date: 2026-09-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "field_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(20), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field", sa.String(64), nullable=False),
        sa.Column("old_value", sa.Text()),
        sa.Column("new_value", sa.Text()),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("entity_type IN ('contact', 'company')", name="ck_field_changes_entity_type"),
    )
    op.create_index("ix_field_changes_entity_type", "field_changes", ["entity_type"])
    op.create_index("ix_field_changes_entity_id", "field_changes", ["entity_id"])
    op.create_index("ix_field_changes_changed_by_user_id", "field_changes", ["changed_by_user_id"])
    op.create_index("ix_field_changes_changed_at", "field_changes", ["changed_at"])
    # The common read pattern is always "every change for this one
    # record, newest first" - a composite index matching that shape
    # exactly, rather than relying on the two single-column indexes above
    # to be combined at query time.
    op.create_index(
        "ix_field_changes_entity_lookup", "field_changes", ["entity_type", "entity_id", "changed_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_field_changes_entity_lookup", table_name="field_changes")
    op.drop_index("ix_field_changes_changed_at", table_name="field_changes")
    op.drop_index("ix_field_changes_changed_by_user_id", table_name="field_changes")
    op.drop_index("ix_field_changes_entity_id", table_name="field_changes")
    op.drop_index("ix_field_changes_entity_type", table_name="field_changes")
    op.drop_table("field_changes")
