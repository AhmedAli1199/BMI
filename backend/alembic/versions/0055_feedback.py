"""Feedback from testers: reports, what they pointed at, screenshots.

Revision ID: 0055
Revises: 0054
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0055"
down_revision: str | None = "0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("number", sa.Integer(), sa.Identity(), nullable=False, unique=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), index=True),
        sa.Column("user_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("user_role", sa.String(50)),
        sa.Column("kind", sa.String(20), nullable=False, server_default="broken"),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("page_path", sa.String(500), nullable=False, server_default="/", index=True),
        sa.Column("page_title", sa.String(300)),
        sa.Column("page_url", sa.String(1000)),
        sa.Column("elements", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("context", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="new", index=True),
        sa.Column("status_note", sa.Text()),
        sa.Column("status_by", sa.String(255)),
        sa.Column("status_at", sa.DateTime(timezone=True)),
        sa.Column("me_too", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("comments", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("github_number", sa.Integer()),
        sa.Column("github_url", sa.String(500)),
        sa.Column("github_error", sa.Text()),
        sa.Column("github_synced_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "feedback_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("feedback_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("feedback.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("label", sa.String(300)),
        sa.Column("content_type", sa.String(50), nullable=False, server_default="image/png"),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("github_url", sa.String(500)),
    )


def downgrade() -> None:
    op.drop_table("feedback_images")
    op.drop_table("feedback")
