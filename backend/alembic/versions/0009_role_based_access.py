"""Role-based access: users.is_active + the user_access table.

users.role already existed (String, default was "rep" - now "sales", see
app/roles.py for the three real values: admin / data_manager / sales).
is_active lets an account be disabled without deleting it (keeps their
name attributable on past notes/history/review actions).

user_access is one row per {database, optional group} a user can see -
an admin needs no rows (their role alone grants everything); everyone
else's visible data is the union of their rows. See
app/models/user_access.py's docstring for the full shape.

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-16
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))

    op.create_table(
        "user_access",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_db", sa.String(length=64), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "source_db", "group_id", name="uq_user_access_scope"),
    )
    op.create_index("ix_user_access_user_id", "user_access", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_access_user_id", table_name="user_access")
    op.drop_table("user_access")
    op.drop_column("users", "is_active")
