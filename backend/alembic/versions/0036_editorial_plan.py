"""Editorial plan: issue deadlines and key dates on editions, planned features,
and per-brand deadline rules / regular sections. See app/models/sales.py.

Revision ID: 0036
Revises: 0035
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0036"
down_revision: str | None = "0035"
branch_labels = None
depends_on = None

U = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)
J = postgresql.JSONB()


def upgrade() -> None:
    for name in ("editorial_deadline", "ad_deadline", "copy_deadline"):
        op.add_column("sales_editions", sa.Column(name, sa.Date))
    op.add_column("sales_editions", sa.Column("milestones", J, nullable=False, server_default="[]"))
    op.add_column("sales_editions", sa.Column("theme", sa.String(300)))
    op.add_column("sales_editions", sa.Column("distribution", sa.String(300)))
    op.add_column("sales_editions", sa.Column("format", sa.String(16)))
    op.add_column("sales_editions", sa.Column("plan_needs_check", sa.Boolean, nullable=False, server_default=sa.false()))
    op.add_column("sales_editions", sa.Column("date_set_in_plan", sa.Boolean, nullable=False, server_default=sa.false()))
    op.create_table(
        "edition_features",
        sa.Column("id", U, primary_key=True),
        sa.Column("edition_id", U, sa.ForeignKey("sales_editions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("status", sa.String(12), nullable=False, server_default="planned"),
        sa.Column("sponsorable", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "editorial_settings",
        sa.Column("brand", sa.String(10), primary_key=True),
        sa.Column("deadline_rules", J, nullable=False, server_default="[]"),
        sa.Column("regular_sections", J, nullable=False, server_default="[]"),
        sa.Column("about", sa.Text),
        sa.Column("updated_at", TS, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("editorial_settings")
    op.drop_table("edition_features")
    for c in ("date_set_in_plan", "plan_needs_check", "format", "distribution", "theme", "milestones", "copy_deadline", "ad_deadline", "editorial_deadline"):
        op.drop_column("sales_editions", c)
