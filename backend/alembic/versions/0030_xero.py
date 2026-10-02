"""Xero connection and synced sales invoices.

Revision ID: 0030
Revises: 0029
Create Date: 2026-10-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels = None
depends_on = None

U = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)
M = sa.Numeric(12, 2)


def upgrade() -> None:
    op.create_table(
        "xero_connections",
        sa.Column("id", U, primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("tenant_name", sa.String(255)),
        sa.Column("refresh_token_enc", sa.Text, nullable=False),
        sa.Column("access_token_enc", sa.Text),
        sa.Column("access_expires_at", TS),
        sa.Column("connected_by_user_id", U, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("connected_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("synced_until", TS),
        sa.Column("last_sync_at", TS),
        sa.Column("last_error", sa.Text),
    )
    op.create_table(
        "xero_invoices",
        sa.Column("id", U, primary_key=True),
        sa.Column("xero_id", sa.String(64), nullable=False, unique=True),
        sa.Column("number_key", sa.String(60), index=True),
        sa.Column("invoice_number", sa.String(60)),
        sa.Column("contact_name", sa.String(255)),
        sa.Column("reference", sa.String(255)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("currency", sa.String(3)),
        sa.Column("issued_on", sa.Date),
        sa.Column("due_on", sa.Date),
        sa.Column("paid_on", sa.Date),
        sa.Column("sub_total", M),
        sa.Column("total_tax", M),
        sa.Column("total", M),
        sa.Column("amount_paid", M),
        sa.Column("amount_due", M),
        sa.Column("amount_credited", M),
        sa.Column("updated_at_xero", TS),
        sa.Column("synced_at", TS, server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("xero_invoices")
    op.drop_table("xero_connections")
