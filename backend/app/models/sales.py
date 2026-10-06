"""The Sales Order Register (SOR) - BMI's order book, moved out of the
per-title Excel workbooks it lived in (one workbook per title per year,
one sheet per issue/month/event, one row per booking).

Four tables, mirroring the spreadsheet's own shape so nothing a sheet
could say is lost:

- SalesTitle: a product line that gets its own workbook - "OBH",
  "Selling Travel Online", "STM Connect Events". Not the same thing as
  Publication (a CRM *database*): several titles share one database,
  which `crm_source_db` records so client matching knows where to look.
- SalesEdition: one sheet - an issue ("OBH 105"), a month of web sales
  ("Jan 2026"), or an event ("Feb Asia"). Carries the sheet's exchange
  rate and, for imported sheets, the sheet's own "Cumulative value"
  figure so the import can be checked against it.
- SalesRep: the initials used in the "Salesper." column, linked to a CRM
  login where one exists (former reps keep a row with no login).
- SalesOrder: one booking row.

Every edit to an order goes through FieldChange (entity_type
"sales_order"), which is what ends the "someone overwrote the sheet"
problem the backlog describes.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPk

EDITION_KINDS = ("issue", "month", "event", "awards", "guide")
ORDER_STATUSES = ("booked", "cancelled", "contra", "moved")


class SalesTitle(Base, UUIDPk):
    __tablename__ = "sales_titles"

    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # "print" | "digital" | "events" | "awards" - drives the icon/grouping
    # in the UI and which default edition kind a new sheet gets.
    product_line: Mapped[str] = mapped_column(String(20), nullable=False, default="print")
    crm_source_db: Mapped[str] = mapped_column(String(64), nullable=False, default="sellingtravel")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Where last year's ad can be seen online (SALES-021 renewal emails link
    # to it). Templates with {edition}, {year} and {page} placeholders, e.g.
    # "https://example.com/obh/{edition}/page/{page}". The page link is used
    # when the booking's page number is known, else the issue link.
    digital_page_url: Mapped[str | None] = mapped_column(String(500))
    digital_issue_url: Mapped[str | None] = mapped_column(String(500))


class SalesRate(Base, UUIDPk, TimestampMixin):
    """The rate card - this year's price for a product in a title (a full
    page in OBH, a banner on STO). Renewal emails quote it; nothing is
    ever priced from a guess."""
    __tablename__ = "sales_rates"
    __table_args__ = (UniqueConstraint("title_id", "year", "product", name="uq_sales_rates_title_year_product"),)

    title_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_titles.id", ondelete="CASCADE"), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # As the sheets write it ("FP", "1/2", "DPS", "Banner") - matched to a
    # booking's size, so it should use the same shorthand.
    product: Mapped[str] = mapped_column(String(120), nullable=False)
    price_gbp: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(300))


class SalesEdition(Base, UUIDPk, TimestampMixin):
    __tablename__ = "sales_editions"
    __table_args__ = (
        UniqueConstraint("title_id", "year", "name", name="uq_sales_editions_title_year_name"),
        CheckConstraint("kind IN ('issue', 'month', 'event', 'awards', 'guide')", name="ck_sales_editions_kind"),
        CheckConstraint("status IN ('open', 'closed')", name="ck_sales_editions_status"),
    )

    title_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_titles.id"), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # The sheet's own MONTH cell, verbatim ("March/April/May WTCE Preview",
    # "19th/20th Jan") - often more informative than the sheet name.
    period_label: Mapped[str | None] = mapped_column(String(200))
    # Best-known date the issue publishes / the event runs / the month
    # starts. Drives "upcoming", renewal timing and invoice chasing.
    edition_date: Mapped[date | None] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="issue")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    exchange_rate: Mapped[float | None] = mapped_column(Numeric(8, 4))
    # For the booking-value target shown as a progress bar - optional.
    target_gbp: Mapped[float | None] = mapped_column(Numeric(12, 2))
    # This edition's own online link (SALES-021) - overrides the title's
    # issue-link template when the address doesn't follow a pattern.
    digital_url: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)

    # Import provenance + the sheet's own totals, kept for the
    # "imported total vs. sheet total" check. Null for editions created
    # in the app.
    source_file: Mapped[str | None] = mapped_column(String(200))
    source_sheet: Mapped[str | None] = mapped_column(String(120))
    sheet_total_gbp: Mapped[float | None] = mapped_column(Numeric(12, 2))


class SalesRep(Base, UUIDPk):
    __tablename__ = "sales_reps"

    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Every "Commission payable" figure in the 2026 SOR is 2% of the rep's
    # booked total - see docs/bmi-open-questions.md for the open question
    # on the two 5% exceptions. Per-order override lives on SalesOrder.
    commission_rate: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.02)


class SalesOrder(Base, UUIDPk, TimestampMixin):
    __tablename__ = "sales_orders"
    __table_args__ = (
        CheckConstraint("status IN ('booked', 'cancelled', 'contra', 'moved')", name="ck_sales_orders_status"),
    )

    edition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_editions.id", ondelete="CASCADE"), nullable=False, index=True)
    # The client exactly as the sheet/rep wrote it - always kept, even
    # once linked to a CRM company, since the two can legitimately differ
    # ("Brunswick - Delice de France" books for a company named Brunswick).
    client_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), index=True)
    # True once someone confirmed "this client isn't in the CRM" - stops
    # the matcher re-suggesting it forever.
    match_dismissed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rep_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_reps.id"), index=True)

    booked_on: Mapped[date | None] = mapped_column(Date, index=True)
    size: Mapped[str | None] = mapped_column(String(120))
    # Page-equivalents for print ("FP" = 1, "DPS" = 2, "0.5"), parsed from
    # size where possible - what the sheet's "Number pages booked" sums.
    pages: Mapped[float | None] = mapped_column(Numeric(6, 3))
    series: Mapped[str | None] = mapped_column(String(60))
    position: Mapped[str | None] = mapped_column(String(60))

    rate_usd: Mapped[float | None] = mapped_column(Numeric(12, 2))
    value_gbp: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    agency_commission_gbp: Mapped[float | None] = mapped_column(Numeric(12, 2))
    commission_rate: Mapped[float | None] = mapped_column(Numeric(5, 4))

    invoice_number: Mapped[str | None] = mapped_column(String(60), index=True)
    invoice_value_gbp: Mapped[float | None] = mapped_column(Numeric(12, 2))
    invoiced_on: Mapped[date | None] = mapped_column(Date)
    # The sheet's "Reason for difference" column - often not about a
    # difference at all ("raise on 23rd", "need po"), so shown as a note.
    # The Xero invoice this booking belongs to - a real link, not just a matching number.
    # xero_link_source: "typed" (someone typed a number that matches Xero), "auto" (matched
    # automatically, no one asked), "confirmed" (a person confirmed a suggestion).
    xero_invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("xero_invoices.id", ondelete="SET NULL"), index=True)
    xero_link_source: Mapped[str | None] = mapped_column(String(16))
    xero_linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invoice_note: Mapped[str | None] = mapped_column(Text)
    # A ticket/order number from the sheet's invoice column that isn't a
    # BMI invoice (People Awards seats carry an 8-digit online order ref
    # and a £0 value) - kept, but never treated as "invoiced".
    order_ref: Mapped[str | None] = mapped_column(String(60))

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="booked", index=True)
    moved_to_edition_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_editions.id", ondelete="SET NULL"))
    notes: Mapped[str | None] = mapped_column(Text)
    # The sheet text that made the importer mark this row cancelled /
    # contra / moved ("Judge ticket cancelled 4/9") - shown next to the
    # status so nobody has to open the spreadsheet to see why.
    status_reason: Mapped[str | None] = mapped_column(Text)
    # Sheet columns only some titles have, by their sheet header:
    # {"Seats": "9", "Table no.": "no. 5", "Paid?": "paid by cc"}.
    extra: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    source_file: Mapped[str | None] = mapped_column(String(200))
    source_sheet: Mapped[str | None] = mapped_column(String(120))
    source_row: Mapped[int | None] = mapped_column(Integer)
    # Anything the importer couldn't parse cleanly (a date written as
    # "19th/20th Jan", a value typed as "40, 0000") - shown as a warning
    # badge so a person can fix it, instead of the importer guessing.
    import_warning: Mapped[str | None] = mapped_column(Text)



class SalesOrderCredit(Base, UUIDPk):
    """Who gets credit (and so commission) for an order, and how much.
    Almost every booking has exactly one credit for its full value; a
    shared booking ("SP/ST" - e.g. BA/Hungary 2025, credited £3,000 each
    in the sheet's commission columns) has one per rep."""
    __tablename__ = "sales_order_credits"
    __table_args__ = (UniqueConstraint("order_id", "rep_id", name="uq_sales_order_credits_order_rep"),)

    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    rep_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_reps.id"), nullable=False, index=True)
    amount_gbp: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)


class SalesEditionCost(Base, UUIDPk, TimestampMixin):
    """A line of an event's costs/P&L, kept next to its bookings so revenue
    and direct costs are seen together - what the events sheets track under
    the booking list (venue hire, food, AV, photographer, travel, BMI
    overheads...). Also any free-text line from that area of the sheet
    (venue contracted on..., deposit paid...) as a "note" line.

    kind: "cost" (counts towards total costs), "income" (extra income not
    in the bookings, e.g. a sponsorship line), "summary" (the sheet's own
    totals/profit lines, kept for reference but never added up - we
    calculate those) or "note" (text only)."""
    __tablename__ = "sales_edition_costs"

    edition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_editions.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="cost")
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    amount_gbp: Mapped[float | None] = mapped_column(Numeric(12, 2))
    # The VAT-inclusive figure when the sheet gives both ("1,913.76 plus vat 2,257.45").
    amount_inc_vat_gbp: Mapped[float | None] = mapped_column(Numeric(12, 2))
    # Sub-heading the line sits under (an event day/venue: "Edinburgh 27th January").
    section: Mapped[str | None] = mapped_column(String(300))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_row: Mapped[int | None] = mapped_column(Integer)  # null = added in the app
