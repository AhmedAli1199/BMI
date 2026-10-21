"""Who looks after each client, per magazine; who wrote each Act! note and history entry.

Revision ID: 0066
Revises: 0065
Create Date: 2026-10-21
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0066"
down_revision: str | None = "0065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_owners",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("area", sa.String(24), nullable=False, index=True),
        sa.Column("rep_id", UUID(as_uuid=True), sa.ForeignKey("sales_reps.id", ondelete="SET NULL"), index=True),
        sa.Column("rule", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(400), nullable=False),
        sa.Column("evidence_on", sa.Date()),
        sa.Column("regions", JSONB, nullable=False, server_default="[]"),
        sa.Column("chosen_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("chosen", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "area", name="uq_client_owners_company_area"),
    )
    op.add_column("notes", sa.Column("act_author", sa.String(120)))
    op.add_column("history_entries", sa.Column("act_author", sa.String(120)))


def downgrade() -> None:
    op.drop_column("history_entries", "act_author")
    op.drop_column("notes", "act_author")
    op.drop_table("client_owners")
