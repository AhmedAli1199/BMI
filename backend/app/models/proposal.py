"""Proposals (SALES-020 builder, SALES-009 logging): a proposal a salesperson
drafts for a client in BMI's Word template - what was proposed, at what
prices, and what happened to it. Kept after it is sent so it can be found
again, logged on the client, and later reused as an example for new pitches.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
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
    # What sort of proposal it is (app/proposals/pricing.py KINDS) - shapes the wording.
    kind: Mapped[str] = mapped_column(String(12), nullable=False, default="issue")
    # % off the whole proposal (each option's total), after any % off a line and rate-card offers.
    discount_pct: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False, default=0)
    # [{"id", "product", "qty", "unit_price", "source": rate_card|manual|offer, "rate_id", "title_id", "issues": [edition ids],
    #   "issue_labels", "discount_pct", "option"}] - prices before VAT (see app/proposals/pricing.py).
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
    # How it goes to the client: "word" (a Word document in the brand's template) or "email" (the proposal is the email itself).
    output: Mapped[str] = mapped_column(String(8), nullable=False, default="word", server_default="word")
    # The proposal request (Review Queue item) it was started from, if any.
    request_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class ProposalExample(Base, UUIDPk, TimestampMixin):
    """A link a salesperson can drop into a proposal: a past page that shows the kind of thing on offer
    ("Spotlight on JetBlue, page 38"), or a resource (media pack, features list, awards site). One library per
    brand, shared by everyone; tagged by format and sector so the right ones can be suggested."""
    __tablename__ = "proposal_examples"

    brand: Mapped[str] = mapped_column(String(20), nullable=False, index=True)        # brands.py key: tbtm | obh | stm
    kind: Mapped[str] = mapped_column(String(10), nullable=False, default="example")  # example | resource
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    format: Mapped[str | None] = mapped_column(String(60))      # "Spotlight on", "Q&A", "Double page sponsored"...
    sector: Mapped[str | None] = mapped_column(String(40))      # airline | hotel | tech | tmc | tourism | rail | travel_services | other
    client: Mapped[str | None] = mapped_column(String(120))     # whose page it was
    notes: Mapped[str | None] = mapped_column(String(300))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    link_ok: Mapped[bool | None] = mapped_column(Boolean)       # None = not checked yet
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class WritingProfile(Base, UUIDPk, TimestampMixin):
    """How one salesperson writes proposals and replies ("Teach the Brain how you write"): built by the AI from their
    past proposals and a note in their own words, then corrected by them. Used to draft their enquiry replies and new
    proposals; what they keep changing in drafts is learned and shown back to them (app/proposals/style.py)."""
    __tablename__ = "writing_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    # [{"id", "name", "source": upload|paste|sent, "text", "added_at"}] - the past proposals it learns from
    samples: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    notes: Mapped[str | None] = mapped_column(Text)          # "I never put prices in the first email..."
    profile: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="draft")   # draft | ready
    built_by: Mapped[str | None] = mapped_column(String(10))   # ai | standard
    built_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # What the Brain noticed from their edits: [{"key", "text", "at", "active"}]
    learned: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # The last few drafts compared with what was actually sent: [{"at", "kind", "situation", "removed", "sign_off"}]
    edits: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
