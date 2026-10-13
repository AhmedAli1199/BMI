import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import UUIDPk


class CallRecording(Base, UUIDPk):
    """A call the notetaker was sent into (the separate Notetaker service does the recording;
    this is BMI Brain's copy of the result, tied to the contact and company)."""
    __tablename__ = "call_recordings"

    notetaker_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    calendar_meeting_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)   # set when booked from the shared calendar
    meeting_url: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str | None] = mapped_column(String(20))
    title: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="scheduled", index=True)
    status_label: Mapped[str | None] = mapped_column(String(100))
    status_detail: Mapped[str | None] = mapped_column(Text)
    participants: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    notes: Mapped[dict | None] = mapped_column(JSONB)
    transcript: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    saved_to_history_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
