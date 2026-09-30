"""Add automation_settings - per-key runtime overrides for automation
tunables (mailbox lists, lookback windows, confidence floors, enabled
flags), editable from the Automations UI without an env var edit +
redeploy. See app/models/automation_setting.py and
app/automations/runtime_settings.py.

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-21
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "automation_settings",
        sa.Column("key", sa.String(length=128), primary_key=True),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("automation_settings")
