"""Bulk updates and contact imports (Act! feedback B3 / B4). See app/models/contact_tools.py.

Revision ID: 0034
Revises: 0033
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels = None
depends_on = None

U = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)
J = postgresql.JSONB()


def upgrade() -> None:
    op.create_table(
        "bulk_edits",
        sa.Column("id", U, primary_key=True),
        sa.Column("user_id", U, sa.ForeignKey("users.id", ondelete="SET NULL"), index=True),
        sa.Column("field_key", sa.String(100), nullable=False),
        sa.Column("field_label", sa.String(200), nullable=False),
        sa.Column("op", sa.String(12), nullable=False),
        sa.Column("new_value", sa.Text),
        sa.Column("find_text", sa.Text),
        sa.Column("scope_label", sa.String(300)),
        sa.Column("total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("changed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("before", J, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(10), nullable=False, server_default="applied"),
        sa.Column("created_at", TS, server_default=sa.func.now(), index=True),
        sa.Column("undone_at", TS),
    )
    op.create_table(
        "contact_imports",
        sa.Column("id", U, primary_key=True),
        sa.Column("created_by_user_id", U, sa.ForeignKey("users.id", ondelete="SET NULL"), index=True),
        sa.Column("filename", sa.String(300), nullable=False),
        sa.Column("file_kind", sa.String(8), nullable=False),
        sa.Column("file_data", sa.LargeBinary),
        sa.Column("status", sa.String(12), nullable=False, server_default="mapping", index=True),
        sa.Column("sheet_name", sa.String(200)),
        sa.Column("sheets", J, nullable=False, server_default="[]"),
        sa.Column("has_header", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("header_row", sa.Integer, nullable=False, server_default="0"),
        sa.Column("headers", J, nullable=False, server_default="[]"),
        sa.Column("rows", J, nullable=False, server_default="[]"),
        sa.Column("row_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("mapping", J, nullable=False, server_default="{}"),
        sa.Column("suggestions", J, nullable=False, server_default="{}"),
        sa.Column("options", J, nullable=False, server_default="{}"),
        sa.Column("excluded", J, nullable=False, server_default="[]"),
        sa.Column("notes", J, nullable=False, server_default="[]"),
        sa.Column("result", J, nullable=False, server_default="{}"),
        sa.Column("created_contact_ids", J, nullable=False, server_default="[]"),
        sa.Column("updated_before", J, nullable=False, server_default="{}"),
        sa.Column("created_at", TS, server_default=sa.func.now(), index=True),
        sa.Column("imported_at", TS),
        sa.Column("undone_at", TS),
    )


def downgrade() -> None:
    op.drop_table("contact_imports")
    op.drop_table("bulk_edits")
