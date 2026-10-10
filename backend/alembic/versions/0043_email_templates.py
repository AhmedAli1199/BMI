"""Email templates by brand, title and purpose; brand facts quoted in emails.

Revision ID: 0043
Revises: 0042
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0043"
down_revision: str | None = "0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mail_templates", sa.Column("brand", sa.String(10)))
    op.create_index("ix_mail_templates_brand", "mail_templates", ["brand"])
    op.add_column("mail_templates", sa.Column("title_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sales_titles.id", ondelete="SET NULL")))
    op.add_column("mail_templates", sa.Column("kind", sa.String(12), nullable=False, server_default="general"))
    op.add_column("mail_templates", sa.Column("description", sa.String(300)))
    op.add_column("mail_templates", sa.Column("source", sa.String(20)))
    op.add_column("mail_templates", sa.Column("needs_check", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("mail_templates", sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("mail_templates", sa.Column("last_used_at", sa.DateTime(timezone=True)))
    op.add_column("editorial_settings", sa.Column("facts", postgresql.JSONB(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("editorial_settings", "facts")
    for c in ("last_used_at", "use_count", "needs_check", "source", "description", "kind", "title_id"):
        op.drop_column("mail_templates", c)
    op.drop_index("ix_mail_templates_brand", "mail_templates")
    op.drop_column("mail_templates", "brand")
