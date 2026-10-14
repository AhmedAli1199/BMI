"""Proposal examples library; proposals go out as an email or a Word document.

Revision ID: 0052
Revises: 0051
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0052"
down_revision: str | None = "0051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("proposals", sa.Column("output", sa.String(8), nullable=False, server_default="word"))
    op.add_column("proposals", sa.Column("request_item_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_table(
        "proposal_examples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("brand", sa.String(20), nullable=False, index=True),
        sa.Column("kind", sa.String(10), nullable=False, server_default="example"),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("format", sa.String(60)),
        sa.Column("sector", sa.String(40)),
        sa.Column("client", sa.String(120)),
        sa.Column("notes", sa.String(300)),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("link_ok", sa.Boolean()),
        sa.Column("checked_at", sa.DateTime(timezone=True)),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("proposal_examples")
    op.drop_column("proposals", "request_item_id")
    op.drop_column("proposals", "output")
