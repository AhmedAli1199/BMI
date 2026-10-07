"""Proposals remember which issue they are for (from the editorial plan).

Revision ID: 0037
Revises: 0036
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0037"
down_revision: str | None = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("proposals", sa.Column("edition_id", postgresql.UUID(as_uuid=True),
                                         sa.ForeignKey("sales_editions.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_proposals_edition_id", "proposals", ["edition_id"])


def downgrade() -> None:
    op.drop_index("ix_proposals_edition_id", table_name="proposals")
    op.drop_column("proposals", "edition_id")
