"""Shared calendar: connected Google/Outlook calendars, the merged meetings, each person's copy.

Revision ID: 0049
Revises: 0048
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0049"
down_revision: str | None = "0048"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "calendar_connections",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("refresh_token_enc", sa.Text(), nullable=False),
        sa.Column("access_token_enc", sa.Text()),
        sa.Column("access_expires_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False, server_default="connected"),
        sa.Column("last_error", sa.Text()),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("connected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "provider", name="uq_calendar_connection_user_provider"),
    )
    op.create_table(
        "calendar_meetings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("dedupe_key", sa.String(600), nullable=False, unique=True),
        sa.Column("title", sa.Text()),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_all_day", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("join_url", sa.Text()),
        sa.Column("platform", sa.String(20)),
        sa.Column("organizer_email", sa.String(255)),
        sa.Column("organizer_name", sa.String(255)),
        sa.Column("attendees", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active", index=True),
        sa.Column("record_override", sa.String(10)),
        sa.Column("override_by_user_id", UUID),
        sa.Column("contact_id", UUID),
        sa.Column("company_id", UUID),
        sa.Column("call_id", UUID, index=True),
        sa.Column("last_error", sa.Text()),
        sa.Column("notified_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "calendar_attendances",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("meeting_id", UUID, sa.ForeignKey("calendar_meetings.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("connection_id", UUID, sa.ForeignKey("calendar_connections.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", UUID, nullable=False, index=True),
        sa.Column("provider_event_id", sa.String(1024), nullable=False),
        sa.Column("response", sa.String(20), nullable=False, server_default="none"),
        sa.Column("is_private", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("connection_id", "provider_event_id", name="uq_calendar_attendance_event"),
    )
    op.add_column("call_recordings", sa.Column("calendar_meeting_id", UUID))
    op.create_index("ix_call_recordings_calendar_meeting_id", "call_recordings", ["calendar_meeting_id"])


def downgrade() -> None:
    op.drop_index("ix_call_recordings_calendar_meeting_id", "call_recordings")
    op.drop_column("call_recordings", "calendar_meeting_id")
    op.drop_table("calendar_attendances")
    op.drop_table("calendar_meetings")
    op.drop_table("calendar_connections")
