"""The shared calendar.

CalendarConnection  - one person's Google or Outlook calendar (read-only grant, tokens encrypted).
CalendarMeeting     - one real meeting on the shared calendar. The same meeting in several people's
                      calendars is ONE row (matched on meeting link + start time, see calendar_sync).
CalendarAttendance  - one person's copy of a meeting: their own event id, reply and privacy flag.
ZoomConnection      - one person's connected Zoom. Zoom lets the notetaker join only on behalf of a signed-in
                      person in the call; the notetaker keeps the sign-in, we keep whose it is.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import UUIDPk


class CalendarConnection(Base, UUIDPk):
    __tablename__ = "calendar_connections"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_calendar_connection_user_provider"),)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)   # google | microsoft
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    refresh_token_enc: Mapped[str] = mapped_column(Text, nullable=False)
    access_token_enc: Mapped[str | None] = mapped_column(Text)
    access_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="connected")   # connected | error
    last_error: Mapped[str | None] = mapped_column(Text)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CalendarMeeting(Base, UUIDPk):
    __tablename__ = "calendar_meetings"

    dedupe_key: Mapped[str] = mapped_column(String(600), nullable=False, unique=True)
    title: Mapped[str | None] = mapped_column(Text)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_all_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    join_url: Mapped[str | None] = mapped_column(Text)
    platform: Mapped[str | None] = mapped_column(String(20))   # google_meet | teams | zoom | None
    organizer_email: Mapped[str | None] = mapped_column(String(255))
    organizer_name: Mapped[str | None] = mapped_column(String(255))
    attendees: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)   # [{email, name, response}]
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)   # active | cancelled
    # A person's one-off choice for this meeting: "record" or "skip" (None = follow the rules)
    record_override: Mapped[str | None] = mapped_column(String(10))
    override_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    call_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)   # the CallRecording, once the bot is booked
    last_error: Mapped[str | None] = mapped_column(Text)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CalendarAttendance(Base, UUIDPk):
    __tablename__ = "calendar_attendances"
    __table_args__ = (UniqueConstraint("connection_id", "provider_event_id", name="uq_calendar_attendance_event"),)

    meeting_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("calendar_meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("calendar_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    provider_event_id: Mapped[str] = mapped_column(String(1024), nullable=False)
    response: Mapped[str] = mapped_column(String(20), nullable=False, default="none")   # organizer | accepted | tentative | declined | none
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ZoomConnection(Base, UUIDPk):
    __tablename__ = "zoom_connections"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    zoom_user_id: Mapped[str] = mapped_column(String(100), nullable=False)   # the notetaker's name for it
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="connected")   # connected | error
    last_error: Mapped[str | None] = mapped_column(Text)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
