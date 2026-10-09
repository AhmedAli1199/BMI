"""Orders: one client order with several items (BMI's "order confirmation" / "schedule of works").

An order is what the salesperson agrees with the client: who it's for, where the
confirmation and the invoice go, the client's PO number, any agency's commission,
discounts, a package price, instructions. Each item is an ordinary booking
(SalesOrder.deal_id) in its own issue, month or event, with its own date - so it
counts in that issue's figures and earns commission when it publishes or happens,
item by item (Matt, Oct 2026). The confirmation is printed from the order.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPk

DEAL_STATUSES = ("pencilled", "confirmed", "cancelled")


class SalesDeal(Base, UUIDPk, TimestampMixin):
    __tablename__ = "sales_deals"

    number: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)   # BMI's order no. (2436)
    # pencilled = held for the client, not yet confirmed (not counted in sales figures or commission)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="pencilled", index=True)
    # Which document it prints as: "confirmation" (Order confirmation, invoice to follow) or "schedule" (Schedule of works)
    document: Mapped[str] = mapped_column(String(12), nullable=False, default="confirmation")

    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), index=True)
    client_name: Mapped[str] = mapped_column(String(256), nullable=False)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"))
    contact_name: Mapped[str | None] = mapped_column(String(200))
    contact_email: Mapped[str | None] = mapped_column(String(320))
    confirmation_address: Mapped[str | None] = mapped_column(Text)
    invoice_to: Mapped[str | None] = mapped_column(Text)           # often "Accounts Payable" or the agency
    invoice_email: Mapped[str | None] = mapped_column(String(320))  # "Please email the invoice to Jonathan..."
    po_number: Mapped[str | None] = mapped_column(String(80))      # the client's order ref / PO
    agency_name: Mapped[str | None] = mapped_column(String(200))   # booked through an agency (it's invoiced, takes commission)
    agency_pct: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False, default=0)

    rep_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_reps.id"), index=True)
    # Shared orders: [{"rep_id": "...", "pct": 0.5}, ...] - every item is credited this way. Empty = all to rep_id.
    split: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    booked_on: Mapped[date] = mapped_column(Date, nullable=False)

    title_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_titles.id", ondelete="SET NULL"))
    publication_label: Mapped[str | None] = mapped_column(String(200))   # "The Business Travel Magazine plus digital activity"
    insertions_label: Mapped[str | None] = mapped_column(String(300))    # override for "Insertions booked"

    # items = each line has its own price; package = one price for everything, shared out across the items
    pricing: Mapped[str] = mapped_column(String(8), nullable=False, default="items")
    package_price_gbp: Mapped[float | None] = mapped_column(Numeric(12, 2))
    package_label: Mapped[str | None] = mapped_column(String(200))     # "Marketing package for Travel Wisconsin"
    package_split: Mapped[str] = mapped_column(String(10), nullable=False, default="rate_card")   # rate_card | even | manual
    discount_pct: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False, default=0)          # off the whole order
    # The lines as entered (what prints on the confirmation); each placement is a booking:
    # [{"key", "title_id", "rate_id", "description", "size", "qty", "unit_price", "list_price", "discount_pct",
    #   "added_value", "share_gbp", "placements": [{"order_id", "edition_id", "item_date", "copy_due", "note"}]}]
    lines: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    total_gbp: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    invoice_plan: Mapped[str] = mapped_column(String(14), nullable=False, default="on_publication")  # upfront | on_publication | custom
    special_instructions: Mapped[str | None] = mapped_column(Text)
    copy_instructions: Mapped[str | None] = mapped_column(Text)
    production_contact: Mapped[str | None] = mapped_column(String(200))
    show_artwork_specs: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text)        # internal, never printed

    proposal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("proposals.id", ondelete="SET NULL"))
    rebooked_from_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_deals.id", ondelete="SET NULL"))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_to: Mapped[str | None] = mapped_column(String(400))
    cancelled_reason: Mapped[str | None] = mapped_column(String(300))


class DealSettings(Base):
    """One row: what every confirmation carries (BMI's address, terms, artwork specs) and the next order number."""
    __tablename__ = "deal_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    next_number: Mapped[int] = mapped_column(Integer, nullable=False, default=2437)
    company_block: Mapped[str] = mapped_column(Text, nullable=False, default="")
    footer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    terms: Mapped[str] = mapped_column(Text, nullable=False, default="")
    artwork_specs: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
