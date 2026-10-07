"""Proposals (SALES-020 builder, SALES-009 logging): a proposal a salesperson
drafts for a client in BMI's Word template - what was proposed, at what
prices, and what happened to it. Kept after it is sent so it can be found
again, logged on the client, and later reused as an example for new pitches.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPk

PROPOSAL_TEMPLATES = ("obh", "stm", "tbtm")


class Proposal(Base, UUIDPk, TimestampMixin):
    __tablename__ = "proposals"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), index=True)
    title_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_titles.id", ondelete="SET NULL"), index=True)
    # The issue / event it's for, from the editorial plan (dates and features go into the wording).
    edition_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_editions.id", ondelete="SET NULL"), index=True)
    # Which of BMI's three Word templates it is written in: obh | stm | tbtm.
    template: Mapped[str] = mapped_column(String(8), nullable=False)
    # The campaign / advertiser name that goes in the Word header ("Delta 2026/27").
    campaign_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="draft", index=True)  # draft | sent
    # [{"id", "kind": intro|history|proposal|investment|next_steps|custom, "heading", "body"}]
    sections: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # [{"id", "product", "qty", "unit_price", "source": rate_card|manual}] - prices before VAT.
    lines: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    total_gbp: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    # What was known about the client when it was drafted (bookings history, rate card year, hints).
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Plain-English things the builder couldn't fill in ("No 2026 rate card for this title").
    flags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # "ai" = the wording was written by the model (and passed the figures check); "template" = standard wording.
    drafted_by: Mapped[str] = mapped_column(String(10), nullable=False, default="template")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_via: Mapped[str | None] = mapped_column(String(16))  # downloaded | outlook | other
    logged_note_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    follow_up_reminder_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    notes: Mapped[str | None] = mapped_column(Text)
