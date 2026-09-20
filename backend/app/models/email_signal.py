"""One row per (contact, conversation, signal_type) - a structured fact
extracted from real email correspondence with a contact, by
app/automations/email_summary.py. Kept as its own indexed table rather
than a JSONB blob on Contact specifically so SALES-012/013 can cheaply
query "which signals are due", across every contact, without a full scan.

A thread producing a new message doesn't create a new row - it updates
the existing one for that (contact, source_thread_id, signal_type), so a
long-running conversation about the same renewal keeps exactly one row
that gets more accurate over time, not a growing pile of near-duplicates.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Float, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import UUIDPk

EMAIL_SIGNAL_TYPES = ("budget_window", "renewal_date", "promised_callback", "personal_touchpoint")
EMAIL_SIGNAL_STATUSES = ("open", "actioned", "dismissed")


class EmailSignal(Base, UUIDPk):
    __tablename__ = "email_signals"
    __table_args__ = (
        CheckConstraint(
            "signal_type IN ('budget_window', 'renewal_date', 'promised_callback', 'personal_touchpoint')",
            name="ck_email_signals_type",
        ),
        CheckConstraint("status IN ('open', 'actioned', 'dismissed')", name="ck_email_signals_status"),
        # One live signal of a given type per thread - a thread's third
        # message about the same renewal date updates this row, it never
        # multiplies it.
        UniqueConstraint("source_thread_id", "signal_type", name="uq_email_signals_thread_type"),
    )

    contact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False, index=True)

    signal_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    # Graph identifiers - never a message body, just enough to find/update
    # the right row and to fetch the source message again if a reviewer
    # ever wants to see it.
    source_thread_id: Mapped[str] = mapped_column(String(256), nullable=False)
    source_message_id: Mapped[str] = mapped_column(String(256), nullable=False)

    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
