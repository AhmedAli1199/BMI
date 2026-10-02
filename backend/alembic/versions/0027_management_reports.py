"""Weekly management summaries and behind-last-cycle alerts (SALES-028).
See app/models/management.py.

Revision ID: 0027
Revises: 0026
Create Date: 2026-09-30
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels = None
depends_on = None

U = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "management_alerts",
        sa.Column("id", U, primary_key=True),
        sa.Column("subject_type", sa.String(20), nullable=False, server_default="edition"),
        sa.Column("subject_id", U, nullable=False, index=True),
        sa.Column("subject_label", sa.String(200), nullable=False),
        sa.Column("comparison_label", sa.String(200)),
        sa.Column("prior_value", sa.Numeric(12, 2), nullable=False),
        sa.Column("current_value", sa.Numeric(12, 2), nullable=False),
        sa.Column("gap", sa.Numeric(12, 2), nullable=False),
        sa.Column("gap_pct", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("records_ref", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("fired_at", TS, nullable=False, server_default=sa.func.now(), index=True),
    )
    op.create_table(
        "weekly_summaries",
        sa.Column("id", U, primary_key=True),
        sa.Column("week_of", sa.Date(), nullable=False, unique=True),
        sa.Column("brief_markdown", sa.Text(), nullable=False),
        sa.Column("sections", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("metrics_snapshot", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("source", sa.String(16), nullable=False, server_default="template"),
        sa.Column("generated_at", TS, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("weekly_summaries")
    op.drop_table("management_alerts")
