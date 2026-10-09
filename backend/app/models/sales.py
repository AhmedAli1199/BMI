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

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPk

EDITION_KINDS = ("issue", "month", "event", "awards", "guide")
ORDER_STATUSES = ("booked", "cancelled", "contra", "moved", "pencilled")


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
    """The rate card - one product's price for a year (a full page in OBH, a
    website banner per month, an award entry). Proposals and renewal emails
    quote it; nothing is ever priced from a guess.

    The rate card screen groups these by brand and section (app/sales/brands.py);
    title_id is the sales title the product is booked under, so a booking's
    size can find its price."""
    __tablename__ = "sales_rates"
    __table_args__ = (UniqueConstraint("title_id", "year", "section", "product", name="uq_sales_rates_title_year_section_product"),)

    title_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_titles.id", ondelete="CASCADE"), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # Section of the brand's rate card: print | sponsored | website | newsletter | events | awards | listings | other
    section: Mapped[str] = mapped_column(String(20), nullable=False, default="print")
    # What people call it ("Full page", "Newsletter banner (Position A)").
    product: Mapped[str] = mapped_column(String(120), nullable=False)
    # fixed = the price; from = a starting price; poa = price on request (price_gbp empty)
    price_type: Mapped[str] = mapped_column(String(10), nullable=False, default="fixed")
    price_gbp: Mapped[float | None] = mapped_column(Numeric(12, 2))
    # What the price is for: each (advert/item) | month | week | year | event | entry
    unit: Mapped[str] = mapped_column(String(10), nullable=False, default="each")
    specs: Mapped[str | None] = mapped_column(String(200))  # "728px x 90px", "4 pages"
    # Shorthand the order register uses for the same thing ("FP", "1/2", "DPS") - how a booking finds its price.
    aliases: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    notes: Mapped[str | None] = mapped_column(String(300))
    valid_until: Mapped[date | None] = mapped_column(Date)  # early-bird prices etc.
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Loaded from a media pack (or copied to a new year) and not yet looked at by a person.
    needs_check: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str | None] = mapped_column(String(120))
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)


class RateOffer(Base, UUIDPk, TimestampMixin):
    """A deal on a brand's rate card for a year, in plain words: "Book 2 adverts,
    save 10%", "Early bird until 1 February", "Four dinners at £3,250 each".
    `rules` makes it usable by the proposal builder:
      volume:     {"tiers": [{"qty": 2, "discount_pct": 10}, ...]}
      series:     {"tiers": [{"qty": 2, "unit_price": 3750}, ...]}
      early_bird: {} (valid_until says when it ends)
      note:       {} (just information)"""
    __tablename__ = "rate_offers"

    brand: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(12), nullable=False, default="note")
    label: Mapped[str] = mapped_column(String(300), nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
    rules: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Which rate-card products it applies to (ids); empty = the whole section / brand as described.
    rate_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    section: Mapped[str | None] = mapped_column(String(20))
    valid_until: Mapped[date | None] = mapped_column(Date)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    needs_check: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


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
    # ---- Editorial plan (app/api/routes/editorial.py) ----
    # The issue's deadlines. edition_date stays the publication / event date.
    editorial_deadline: Mapped[date | None] = mapped_column(Date)
    ad_deadline: Mapped[date | None] = mapped_column(Date)  # booking deadline for adverts
    copy_deadline: Mapped[date | None] = mapped_column(Date)  # artwork / copy deadline
    # Any other key dates, in the brand's own words: [{"label": "Entries close", "date": "2026-12-01"}]
    milestones: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    theme: Mapped[str | None] = mapped_column(String(300))  # headline theme of the issue
    distribution: Mapped[str | None] = mapped_column(String(300))  # shows / events it's handed out at
    format: Mapped[str | None] = mapped_column(String(16))  # print_digital | print | digital | event | awards
    # Some dates were worked out (e.g. from "25th of the month before") or estimated - a person should confirm them.
    plan_needs_check: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # The publication date was set in the editorial plan - a re-import of the order register keeps it.
    date_set_in_plan: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Commission: a guide/supplement that is a new contract-publishing job (earns its seller the new-guide bonus).
    new_contract_guide: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    new_contract_rep_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_reps.id", ondelete="SET NULL"))
    # Event costs: marked final by whoever enters them, then signed off by a manager before profit share is paid.
    costs_final_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    costs_final_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    costs_signed_off_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    costs_signed_off_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    source_file: Mapped[str | None] = mapped_column(String(200))
    source_sheet: Mapped[str | None] = mapped_column(String(120))
    sheet_total_gbp: Mapped[float | None] = mapped_column(Numeric(12, 2))


class EditionFeature(Base, UUIDPk, TimestampMixin):
    """One planned feature in an issue ("Seafood", "Top business travel trends for 2027")."""
    __tablename__ = "edition_features"

    edition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_editions.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="planned")  # planned | confirmed | dropped
    sponsorable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # open to sponsorship / sponsored content
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class EditorialSetting(Base):
    """Per brand: how deadlines are usually worked out, and the regular sections every issue has."""
    __tablename__ = "editorial_settings"

    brand: Mapped[str] = mapped_column(String(10), primary_key=True)
    # [{"key": "editorial"|"advertising"|"copy"|<custom>, "label": "...", "kind": "days_before"|"day_prev_month", "value": 25}]
    deadline_rules: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # [{"name": "Take Five", "description": "Experts share five insights on a topic"}]
    regular_sections: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    about: Mapped[str | None] = mapped_column(Text)  # one paragraph on the brand's publishing schedule
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


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
        CheckConstraint("status IN ('booked', 'cancelled', 'contra', 'moved', 'pencilled')", name="ck_sales_orders_status"),
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
    # True when the invoiced amount and date were filled in from the linked Xero invoice (and so follow it);
    # False when they were recorded by a person or the order register, which are never overwritten.
    invoice_from_xero: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Commission: a manager's decision on whether this booking is new business (None = worked out from history).
    new_business_override: Mapped[bool | None] = mapped_column(Boolean)
    new_business_reason: Mapped[str | None] = mapped_column(String(300))
    new_business_set_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    new_business_set_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # ---- An item of a multi-item order (app/models/deal.py) ----
    deal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sales_deals.id", ondelete="SET NULL"), index=True)
    deal_line: Mapped[str | None] = mapped_column(String(40))          # which line of the order it belongs to
    description: Mapped[str | None] = mapped_column(String(300))       # "Solus html email", "Sponsored feature"
    quantity: Mapped[int | None] = mapped_column(Integer)
    unit_price_gbp: Mapped[float | None] = mapped_column(Numeric(12, 2))
    list_price_gbp: Mapped[float | None] = mapped_column(Numeric(12, 2))   # the rate card price ("usual rate £3,750")
    added_value: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # given free with the order
    item_date: Mapped[date | None] = mapped_column(Date, index=True)   # when this item runs, if not the issue's date (an email on 13 May)
    copy_due: Mapped[date | None] = mapped_column(Date)                # copy / artwork deadline for this item



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
