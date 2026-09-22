"""SALES-010's own thread-quiescence tracker - one row per email thread
app/automations/email_summary.py has ever seen, updated on every scan
that finds a new message on it. Separate from EmailSignal (which only
exists for the four *triggerable* fact types SALES-012/013 need): this
table exists purely so the scan can tell "this thread has gone quiet"
without re-reading the whole thread, and to hold the running
thread_summary/is_meaningful verdict the per-message extraction call
already produces for free, so closing a thread costs no extra LLM call.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import UUIDPk


class EmailThreadState(Base, UUIDPk):
    __tablename__ = "email_thread_states"
    __table_args__ = (
        UniqueConstraint("source_thread_id", name="uq_email_thread_states_thread"),
    )

    source_thread_id: Mapped[str] = mapped_column(String(256), nullable=False)
    contact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False, index=True)

    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # The latest "where this conversation stands" verdict from the
    # per-message extraction call (_SIGNAL_EXTRACTION_PROMPT's
    # thread_summary/is_meaningful) - kept current on every new message so
    # closing the thread just reads this, no separate summarising call.
    thread_summary: Mapped[str | None] = mapped_column(Text)
    is_meaningful: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Set once the idle-close sweep actually writes (or decides not to
    # write) a Note for this thread. NULL means "still open, not yet
    # swept" or "reopened since the last close" - either way, still a
    # candidate for the next sweep. closed_note_id is only set when a Note
    # was actually written (is_meaningful was true); a non-meaningful
    # thread still gets closed_at set (so it stops being re-checked every
    # run) but no Note and no closed_note_id.
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_note_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("notes.id"))
    # How many times this thread has been closed and then reopened with a
    # new message - drives "continued conversation" wording on the next
    # closing Note rather than reading like the first exchange all over
    # again.
    reopen_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
