"""Sales Order Register API - replaces the per-title SOR workbooks. See
app/models/sales.py for the data model and app/sales/analytics.py for
what "booked", "same point last year" and "equivalent edition" mean.

Access: the order book was a shared workbook every rep could open, so
every signed-in user can read editions and bookings and add/edit
bookings (every edit is audited in field_changes). Commission figures are
the exception - a sales rep only sees their own; admins and data
managers see everyone's.
"""
from __future__ import annotations

import io
import re
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas import FieldChangeOut, UserSummary
from app.core.identity import Identity, get_identity
from app.db.session import get_db
from app.models import Company, FieldChange, SalesEdition, SalesEditionCost, SalesOrder, SalesOrderCredit, SalesRate, SalesRep, SalesTitle, User, XeroInvoice
from app.roles import CAN_USE_AUTOMATIONS
from app.sales.matching import normalise
from app.sales.order_query import SORTS as ORDER_SORTS
from app.sales.order_query import XERO_STATES, OrderQuery
from app.sales.order_query import facets as order_facets
from app.sales.order_query import page as order_page
from app.sales.analytics import BOOKED, edition_pace, edition_totals, equivalent_editions, same_point_last_year
from app.sales.reference import ensure_reference_data
from app.sales.sor_import import parse_pages
from app.services.field_audit import record_field_changes
from app.sales.invoice_match import XERO_INVOICE_URL, booking_choices, invoice_choices, link_bookings, sync_link_after_edit, unlink_order
from app.services.xero import number_key

router = APIRouter(prefix="/sales", tags=["sales"])


# ---- Schemas ----------------------------------------------------------------

class TitleOut(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    product_line: str
    crm_source_db: str
    digital_page_url: str | None = None
    digital_issue_url: str | None = None


class RepOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    active: bool
    has_login: bool
    commission_rate: float


class Meta(BaseModel):
    titles: list[TitleOut]
    reps: list[RepOut]
    years: list[int]
    my_rep_id: uuid.UUID | None = None
    can_see_all_commission: bool


class Ref(BaseModel):
    id: uuid.UUID
    label: str


class CreditOut(BaseModel):
    rep_id: uuid.UUID
    code: str
    name: str
    amount_gbp: float


class XeroRef(BaseModel):
    """The matching sales invoice in Xero (read-only)."""
    state: str  # paid | part_paid | unpaid | overdue | voided
    status: str
    currency: str | None = None
    total: float | None = None
    amount_paid: float | None = None
    amount_due: float | None = None
    due_on: date | None = None
    paid_on: date | None = None
    invoice_number: str | None = None
    url: str | None = None  # opens the invoice in Xero
    # How the booking came to be linked: "typed" (someone typed the number), "auto" (matched on its own), "confirmed" (a person confirmed it)
    link: str | None = None
    # The booking's invoiced amount and date follow this invoice (False: they were recorded by a person or the sheet).
    figures_from_xero: bool = False


class OrderOut(BaseModel):
    id: uuid.UUID
    edition_id: uuid.UUID
    edition_label: str
    title_id: uuid.UUID
    client_name: str
    company: Ref | None = None
    match_dismissed: bool
    rep: RepOut | None = None
    credits: list[CreditOut]
    booked_on: date | None = None
    size: str | None = None
    pages: float | None = None
    series: str | None = None
    position: str | None = None
    rate_usd: float | None = None
    value_gbp: float
    agency_commission_gbp: float | None = None
    commission_rate: float | None = None
    invoice_number: str | None = None
    invoice_value_gbp: float | None = None
    invoiced_on: date | None = None
    invoice_note: str | None = None
    order_ref: str | None = None
    status: str
    status_reason: str | None = None
    extra: dict[str, str] = {}
    moved_to: Ref | None = None
    notes: str | None = None
    import_warning: str | None = None
    source: str | None = None
    edition_date: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    xero: XeroRef | None = None


class EditionSummary(BaseModel):
    id: uuid.UUID
    title: TitleOut
    year: int
    name: str
    label: str
    period_label: str | None = None
    edition_date: date | None = None
    kind: str
    status: str
    exchange_rate: float | None = None
    target_gbp: float | None = None
    booked_gbp: float
    orders: int
    invoiced_gbp: float
    uninvoiced: int
    paid_orders: int
    invoiced_orders: int
    pages: float
    warnings: int
    sheet_total_gbp: float | None = None
    previous: Ref | None = None
    previous_booked_gbp: float | None = None
    previous_same_point_gbp: float | None = None


class CostLineOut(BaseModel):
    id: uuid.UUID
    kind: str
    label: str
    amount_gbp: float | None = None
    amount_inc_vat_gbp: float | None = None
    section: str | None = None
    from_sheet: bool


class CostLineIn(BaseModel):
    kind: str = Field(default="cost", pattern="^(cost|income|note)$")
    label: str = Field(min_length=1, max_length=500)
    amount_gbp: float | None = None
    amount_inc_vat_gbp: float | None = None
    section: str | None = Field(default=None, max_length=300)


class EditionCosts(BaseModel):
    lines: list[CostLineOut]
    total_costs_gbp: float
    other_income_gbp: float
    # Booked value + other income - costs. None when there are no cost lines.
    profit_gbp: float | None = None


class EditionDetail(EditionSummary):
    notes: str | None = None
    costs: EditionCosts | None = None
    digital_url: str | None = None
    # Last cycle's equivalent edition - what a renewal pass renews from.
    renews_from: Ref | None = None
    source: str | None = None
    orders_list: list[OrderOut]
    by_rep: list[CreditOut]
    cancelled_or_moved: int
    next_edition: Ref | None = None
    prev_in_year: Ref | None = None
    next_in_year: Ref | None = None


class EditionCreate(BaseModel):
    title_id: uuid.UUID
    year: int = Field(ge=2000, le=2100)
    name: str = Field(min_length=1, max_length=120)
    period_label: str | None = None
    edition_date: date | None = None
    kind: str | None = None
    exchange_rate: float | None = None
    target_gbp: float | None = None
    notes: str | None = None
    # Copy last year's equivalent edition's advertisers as a renewal list
    # is a UI concern (Renewals page) - creating an edition never
    # pre-books anyone.


class EditionPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    period_label: str | None = None
    edition_date: date | None = None
    status: str | None = None
    exchange_rate: float | None = None
    target_gbp: float | None = None
    notes: str | None = None
    digital_url: str | None = Field(default=None, max_length=500)


class CreditIn(BaseModel):
    rep_id: uuid.UUID
    amount_gbp: float


class OrderCreate(BaseModel):
    edition_id: uuid.UUID
    client_name: str = Field(min_length=1, max_length=256)
    company_id: uuid.UUID | None = None
    rep_id: uuid.UUID | None = None
    booked_on: date | None = None
    size: str | None = None
    series: str | None = None
    position: str | None = None
    rate_usd: float | None = None
    value_gbp: float = 0
    agency_commission_gbp: float | None = None
    invoice_number: str | None = None
    invoice_value_gbp: float | None = None
    invoiced_on: date | None = None
    invoice_note: str | None = None
    status: str = "booked"
    notes: str | None = None
    credits: list[CreditIn] | None = None


class OrderPatch(BaseModel):
    client_name: str | None = Field(default=None, min_length=1, max_length=256)
    company_id: uuid.UUID | None = None
    clear_company: bool = False
    rep_id: uuid.UUID | None = None
    booked_on: date | None = None
    size: str | None = None
    series: str | None = None
    position: str | None = None
    rate_usd: float | None = None
    value_gbp: float | None = None
    agency_commission_gbp: float | None = None
    commission_rate: float | None = None
    invoice_number: str | None = None
    invoice_value_gbp: float | None = None
    invoiced_on: date | None = None
    invoice_note: str | None = None
    status: str | None = None
    moved_to_edition_id: uuid.UUID | None = None
    notes: str | None = None
    credits: list[CreditIn] | None = None
    clear_warning: bool = False


class OrdersPage(BaseModel):
    items: list[OrderOut]
    total: int
    total_value_gbp: float


class SeriesPoint(BaseModel):
    month: int
    this_year: float
    last_year: float


class TitleRow(BaseModel):
    title: TitleOut
    booked_gbp: float
    orders: int
    last_year_same_point_gbp: float
    last_year_total_gbp: float
    advertisers: int


class RepRow(BaseModel):
    rep: RepOut
    credit_gbp: float
    orders: int


class Overview(BaseModel):
    year: int
    as_of: date
    is_current_year: bool
    booked_gbp: float
    last_year_same_point_gbp: float
    last_year_total_gbp: float
    invoiced_gbp: float
    uninvoiced_count: int
    uninvoiced_gbp: float
    orders: int
    advertisers: int
    new_advertisers: int
    renewal_candidates: int
    monthly: list[SeriesPoint]
    by_title: list[TitleRow]
    by_rep: list[RepRow]
    upcoming: list[EditionSummary]


class PaceRow(BaseModel):
    edition: Ref
    title: TitleOut
    edition_date: date | None = None
    kind: str
    booked_gbp: float
    orders: int
    previous: Ref | None = None
    previous_point_gbp: float | None = None
    previous_point_orders: int | None = None
    previous_total_gbp: float | None = None
    gap_gbp: float | None = None
    gap_pct: float | None = None
    state: str  # behind | on_pace | ahead | not_comparable
    reason: str | None = None


class WeekPoint(BaseModel):
    week_start: date
    orders: int
    value_gbp: float
    last_year_value_gbp: float


class ActivityRow(BaseModel):
    rep: RepOut
    bookings: int
    booked_gbp: float
    followups_actioned: int | None = None  # None: this rep has no login, so no queue to action
    followups_outstanding: int | None = None


class Unattributed(BaseModel):
    orders: int
    value_gbp: float


class Dashboard(BaseModel):
    as_of: date
    threshold_pct: float
    min_prior_gbp: float
    min_prior_orders: int
    pace: list[PaceRow]
    weekly: list[WeekPoint]
    activity_days: int
    activity: list[ActivityRow]
    unattributed: Unattributed
    unattributed_year: int


class CommissionEditionRow(BaseModel):
    edition: Ref
    title: str
    edition_date: date | None = None
    credit_gbp: float
    commission_gbp: float
    orders: int


class CommissionRep(BaseModel):
    rep: RepOut
    credit_gbp: float
    commission_gbp: float
    orders: int
    editions: list[CommissionEditionRow]


class Commissions(BaseModel):
    year: int
    reps: list[CommissionRep]
    scoped_to_me: bool


class RenewalRow(BaseModel):
    client_name: str
    company: Ref | None = None
    rep: RepOut | None = None
    last_edition: Ref
    last_booked_on: date | None = None
    last_value_gbp: float
    last_year_value_gbp: float
    last_year_orders: int
    size: str | None = None


class Renewals(BaseModel):
    title: TitleOut
    year: int
    previous_advertisers: int
    rebooked: int
    retention_rate: float | None = None
    not_rebooked_value_gbp: float
    items: list[RenewalRow]


class CompanyBookings(BaseModel):
    lifetime_gbp: float
    orders: int
    first_booked: date | None = None
    last_booked: date | None = None
    titles: list[str]
    by_year: dict[int, float]
    items: list[OrderOut]


class ClientSuggestion(BaseModel):
    client_name: str
    company: Ref | None = None
    orders: int


# ---- Helpers ------------------------------------------------------------------

def _f(v) -> float | None:
    return None if v is None else float(v)


def _title_out(t: SalesTitle) -> TitleOut:
    return TitleOut(id=t.id, slug=t.slug, name=t.name, product_line=t.product_line, crm_source_db=t.crm_source_db,
                    digital_page_url=t.digital_page_url, digital_issue_url=t.digital_issue_url)


def _rep_out(r: SalesRep) -> RepOut:
    return RepOut(id=r.id, code=r.code, name=r.name, active=r.active, has_login=r.user_id is not None,
                  commission_rate=float(r.commission_rate))


def edition_label(title: SalesTitle, ed: SalesEdition) -> str:
    short = re.sub(r"\s*\(.*?\)", "", title.name) if "(" in title.name else title.name
    abbrev = re.search(r"\((\w+)\)", title.name)
    prefix = abbrev[1] if abbrev else short
    name = ed.name
    if re.fullmatch(r"\d{2,4}", name.strip()):
        return f"{prefix} {name.strip()}"
    if name.lower().startswith(prefix.lower()):
        return name
    return f"{prefix} · {name}"


def _is_staff(identity: Identity) -> bool:
    return not identity.is_known or identity.role in CAN_USE_AUTOMATIONS


def _my_rep(db: Session, identity: Identity) -> SalesRep | None:
    uid = identity.user_uuid
    return db.scalars(select(SalesRep).where(SalesRep.user_id == uid)).first() if uid else None


def _orders_out(db: Session, orders: list[SalesOrder]) -> list[OrderOut]:
    if not orders:
        return []
    ed_ids = {o.edition_id for o in orders} | {o.moved_to_edition_id for o in orders if o.moved_to_edition_id}
    eds = {e.id: e for e in db.scalars(select(SalesEdition).where(SalesEdition.id.in_(ed_ids)))}
    titles = {t.id: t for t in db.scalars(select(SalesTitle))}
    reps = {r.id: r for r in db.scalars(select(SalesRep))}
    comp_ids = {o.company_id for o in orders if o.company_id}
    comps = {c.id: c.name for c in db.execute(select(Company.id, Company.name).where(Company.id.in_(comp_ids)))} if comp_ids else {}
    credits: dict[uuid.UUID, list[SalesOrderCredit]] = defaultdict(list)
    for c in db.scalars(select(SalesOrderCredit).where(SalesOrderCredit.order_id.in_([o.id for o in orders]))):
        credits[c.order_id].append(c)
    keys = {number_key(o.invoice_number) for o in orders} - {None}
    xero: dict[str, XeroInvoice] = {}
    if keys:
        for inv in db.scalars(select(XeroInvoice).where(XeroInvoice.number_key.in_(keys))
                              .order_by(XeroInvoice.updated_at_xero.asc().nulls_first())):
            xero[inv.number_key] = inv  # latest wins
    linked_ids = {o.xero_invoice_id for o in orders if o.xero_invoice_id}
    xero_by_id = {i.id: i for i in db.scalars(select(XeroInvoice).where(XeroInvoice.id.in_(linked_ids)))} if linked_ids else {}

    out = []
    for o in orders:
        ed = eds[o.edition_id]
        title = titles[ed.title_id]
        moved = eds.get(o.moved_to_edition_id) if o.moved_to_edition_id else None
        out.append(OrderOut(
            id=o.id, edition_id=o.edition_id, edition_label=edition_label(title, ed), title_id=title.id,
            client_name=o.client_name,
            company=Ref(id=o.company_id, label=comps.get(o.company_id, "Company")) if o.company_id else None,
            match_dismissed=o.match_dismissed,
            rep=_rep_out(reps[o.rep_id]) if o.rep_id in reps else None,
            credits=[CreditOut(rep_id=c.rep_id, code=reps[c.rep_id].code, name=reps[c.rep_id].name, amount_gbp=float(c.amount_gbp))
                     for c in credits[o.id] if c.rep_id in reps],
            booked_on=o.booked_on, size=o.size, pages=_f(o.pages), series=o.series, position=o.position,
            rate_usd=_f(o.rate_usd), value_gbp=float(o.value_gbp or 0), agency_commission_gbp=_f(o.agency_commission_gbp),
            commission_rate=_f(o.commission_rate), invoice_number=o.invoice_number, invoice_value_gbp=_f(o.invoice_value_gbp),
            invoiced_on=o.invoiced_on, invoice_note=o.invoice_note, order_ref=o.order_ref, status=o.status,
            status_reason=o.status_reason, extra=o.extra or {},
            moved_to=Ref(id=moved.id, label=edition_label(titles[moved.title_id], moved)) if moved else None,
            notes=o.notes, import_warning=o.import_warning,
            source=f"{o.source_file} › {o.source_sheet}, row {o.source_row}" if o.source_file else None,
            edition_date=ed.edition_date, created_at=o.created_at, updated_at=o.updated_at,
            xero=_xero_ref(xero_by_id.get(o.xero_invoice_id) or xero.get(number_key(o.invoice_number) or ""), o.xero_link_source, o.invoice_from_xero),
        ))
    return out


def _xero_ref(inv: XeroInvoice | None, link: str | None = None, from_xero: bool = False) -> XeroRef | None:
    if not inv:
        return None
    due = float(inv.amount_due or 0)
    state = ("voided" if inv.status in ("VOIDED", "DELETED") else "paid" if due <= 0
             else "overdue" if inv.due_on and inv.due_on < date.today()
             else "part_paid" if float(inv.amount_paid or 0) > 0 else "unpaid")
    return XeroRef(state=state, status=inv.status, currency=inv.currency, total=_f(inv.total),
                   amount_paid=_f(inv.amount_paid), amount_due=_f(inv.amount_due), due_on=inv.due_on, paid_on=inv.paid_on,
                   invoice_number=inv.invoice_number, url=XERO_INVOICE_URL.format(inv.xero_id), link=link or "typed",
                   figures_from_xero=from_xero)


def _edition_summaries(db: Session, editions: list[SalesEdition], today: date) -> list[EditionSummary]:
    titles = {t.id: t for t in db.scalars(select(SalesTitle))}
    totals = edition_totals(db, [e.id for e in editions])
    prev = equivalent_editions(db, editions)
    prev_ids = list({p.id for p in prev.values()})
    prev_totals = edition_totals(db, prev_ids)
    prev_point = edition_totals(db, prev_ids, booked_before=same_point_last_year(today))
    out = []
    for e in editions:
        t = totals.get(e.id, {})
        p = prev.get(e.id)
        title = titles[e.title_id]
        out.append(EditionSummary(
            id=e.id, title=_title_out(title), year=e.year, name=e.name, label=edition_label(title, e),
            period_label=e.period_label, edition_date=e.edition_date, kind=e.kind, status=e.status,
            exchange_rate=_f(e.exchange_rate), target_gbp=_f(e.target_gbp),
            booked_gbp=t.get("booked", 0.0), orders=t.get("orders", 0), invoiced_gbp=t.get("invoiced", 0.0),
            uninvoiced=t.get("uninvoiced", 0), paid_orders=t.get("paid", 0), invoiced_orders=t.get("paid_invoiced", 0),
            pages=t.get("pages", 0.0), warnings=t.get("warnings", 0),
            sheet_total_gbp=_f(e.sheet_total_gbp),
            previous=Ref(id=p.id, label=edition_label(titles[p.title_id], p)) if p else None,
            previous_booked_gbp=prev_totals.get(p.id, {}).get("booked", 0.0) if p else None,
            previous_same_point_gbp=prev_point.get(p.id, {}).get("booked", 0.0) if p else None,
        ))
    return out


def _sync_single_credit(db: Session, order: SalesOrder, old_rep: uuid.UUID | None, old_value: float) -> None:
    """Keep the common case in step: an order whose only credit was the
    full value to its rep follows a change of rep or value. A split the
    user set by hand is left alone."""
    credits = db.scalars(select(SalesOrderCredit).where(SalesOrderCredit.order_id == order.id)).all()
    simple = not credits or (len(credits) == 1 and credits[0].rep_id == old_rep and abs(float(credits[0].amount_gbp) - old_value) < 0.01)
    if not simple:
        return
    for c in credits:
        db.delete(c)
    db.flush()
    if order.rep_id and float(order.value_gbp or 0):
        db.add(SalesOrderCredit(id=uuid.uuid4(), order_id=order.id, rep_id=order.rep_id, amount_gbp=order.value_gbp))


def _set_credits(db: Session, order: SalesOrder, credits: list[CreditIn]) -> None:
    for c in db.scalars(select(SalesOrderCredit).where(SalesOrderCredit.order_id == order.id)):
        db.delete(c)
    db.flush()
    merged: dict[uuid.UUID, float] = defaultdict(float)
    for c in credits:
        if c.amount_gbp:
            merged[c.rep_id] += c.amount_gbp
    for rep_id, amount in merged.items():
        if not db.get(SalesRep, rep_id):
            raise HTTPException(status_code=422, detail="Unknown salesperson in credits")
        db.add(SalesOrderCredit(id=uuid.uuid4(), order_id=order.id, rep_id=rep_id, amount_gbp=round(amount, 2)))


def _check_status(status: str) -> None:
    if status not in ("booked", "cancelled", "contra", "moved"):
        raise HTTPException(status_code=422, detail="Status must be booked, cancelled, contra or moved")


# ---- Meta ---------------------------------------------------------------------

@router.get("/meta", response_model=Meta)
def meta(db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> Meta:
    ensure_reference_data(db)
    db.commit()
    titles = db.scalars(select(SalesTitle).where(SalesTitle.active.is_(True)).order_by(SalesTitle.sort_order)).all()
    reps = db.scalars(select(SalesRep).order_by(SalesRep.active.desc(), SalesRep.name)).all()
    years = sorted({y for y in db.scalars(select(SalesEdition.year).distinct())} | {date.today().year}, reverse=True)
    me = _my_rep(db, identity)
    return Meta(titles=[_title_out(t) for t in titles], reps=[_rep_out(r) for r in reps], years=years,
                my_rep_id=me.id if me else None, can_see_all_commission=_is_staff(identity))


# ---- Overview -----------------------------------------------------------------

@router.get("/overview", response_model=Overview)
def overview(year: int | None = None, db: Session = Depends(get_db)) -> Overview:
    today = date.today()
    year = year or today.year
    is_current = year == today.year
    as_of = today if is_current else date(year, 12, 31)
    cutoff_prev = same_point_last_year(as_of)

    def booked_rows(y: int, before: date | None = None):
        q = (select(SalesOrder.value_gbp, SalesOrder.booked_on, SalesEdition.title_id, SalesOrder.client_name,
                    SalesOrder.invoice_number, SalesOrder.invoice_value_gbp, SalesEdition.edition_date, SalesOrder.id)
             .join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
             .where(SalesEdition.year == y, SalesOrder.status == BOOKED))
        if before:
            q = q.where(func.coalesce(SalesOrder.booked_on, date.min) <= before)
        return db.execute(q).all()

    this = booked_rows(year)
    last_point = booked_rows(year - 1, cutoff_prev)
    last_all = booked_rows(year - 1)
    ck = lambda n: normalise(n) or n.strip().lower()  # noqa: E731 - same client key as renewals
    earlier_clients = {ck(r.client_name) for r in db.execute(
        select(SalesOrder.client_name).join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
        .where(SalesEdition.year < year, SalesOrder.status == BOOKED)).all()}
    this_clients = {ck(r.client_name) for r in this}
    last_clients = {ck(r.client_name) for r in last_all if float(r.value_gbp) > 0}

    def month_of(r, y: int) -> int:
        """Booking month relative to the edition year: anything booked
        before 1 January (next year's issue sold early) is the position the
        year started from, so it lands in January; undated -> January too."""
        d = r.booked_on or r.edition_date
        if not d or d.year < y:
            return 1
        return 12 if d.year > y else d.month

    monthly = []
    for m in range(1, 13):
        monthly.append(SeriesPoint(
            month=m,
            this_year=round(sum(float(r.value_gbp) for r in this if month_of(r, year) == m
                                and (not is_current or not r.booked_on or r.booked_on <= today)), 2),
            last_year=round(sum(float(r.value_gbp) for r in last_all if month_of(r, year - 1) == m), 2),
        ))

    titles = {t.id: t for t in db.scalars(select(SalesTitle))}
    by_title_rows = []
    for tid, t in sorted(titles.items(), key=lambda kv: kv[1].sort_order):
        rows = [r for r in this if r.title_id == tid]
        lp = [r for r in last_point if r.title_id == tid]
        la = [r for r in last_all if r.title_id == tid]
        if not rows and not la:
            continue
        by_title_rows.append(TitleRow(
            title=_title_out(t), booked_gbp=round(sum(float(r.value_gbp) for r in rows), 2), orders=len(rows),
            last_year_same_point_gbp=round(sum(float(r.value_gbp) for r in lp), 2),
            last_year_total_gbp=round(sum(float(r.value_gbp) for r in la), 2),
            advertisers=len({ck(r.client_name) for r in rows}),
        ))
    by_title_rows.sort(key=lambda r: -r.booked_gbp)

    rep_rows = db.execute(
        select(SalesOrderCredit.rep_id, func.sum(SalesOrderCredit.amount_gbp), func.count(func.distinct(SalesOrderCredit.order_id)))
        .join(SalesOrder, SalesOrderCredit.order_id == SalesOrder.id)
        .join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
        .where(SalesEdition.year == year, SalesOrder.status == BOOKED)
        .group_by(SalesOrderCredit.rep_id)
    ).all()
    reps = {r.id: r for r in db.scalars(select(SalesRep))}
    by_rep = sorted([RepRow(rep=_rep_out(reps[rid]), credit_gbp=float(total), orders=n) for rid, total, n in rep_rows if rid in reps],
                    key=lambda r: -r.credit_gbp)

    upcoming_eds = db.scalars(select(SalesEdition).where(
        SalesEdition.edition_date >= today, SalesEdition.edition_date <= today + timedelta(days=75),
        SalesEdition.status == "open").order_by(SalesEdition.edition_date).limit(8)).all() if is_current else []

    uninvoiced = [r for r in this if float(r.value_gbp) > 0 and not r.invoice_number]
    return Overview(
        year=year, as_of=as_of, is_current_year=is_current,
        booked_gbp=round(sum(float(r.value_gbp) for r in this), 2),
        last_year_same_point_gbp=round(sum(float(r.value_gbp) for r in last_point), 2),
        last_year_total_gbp=round(sum(float(r.value_gbp) for r in last_all), 2),
        invoiced_gbp=round(sum(float(r.invoice_value_gbp or 0) for r in this), 2),
        uninvoiced_count=len(uninvoiced), uninvoiced_gbp=round(sum(float(r.value_gbp) for r in uninvoiced), 2),
        orders=len(this), advertisers=len(this_clients), new_advertisers=len(this_clients - earlier_clients),
        renewal_candidates=len(last_clients - this_clients),
        monthly=monthly, by_title=by_title_rows, by_rep=by_rep,
        upcoming=_edition_summaries(db, list(upcoming_eds), today),
    )


# ---- Dashboard (SALES-026) ---------------------------------------------------------

DASHBOARD_WEEKS = 12
ACTIVITY_DAYS = 30


@router.get("/dashboard", response_model=Dashboard)
def dashboard(db: Session = Depends(get_db)) -> Dashboard:
    """The management view: how each selling edition is tracking against its
    equivalent last cycle, weekly booking flow, what each person has
    actually done recently, and anything the register can't attribute.
    Every figure is a deterministic sum over the order register (plus the
    review-queue counts for follow-ups); nothing here uses a model.
    Activity is presented alphabetically, not ranked - it is a picture of
    what is happening, not a league table."""
    from app.automations import runtime_settings
    from app.automations.metrics import get_rep_metrics

    today = date.today()
    threshold = runtime_settings.get_float(db, "sales_pace_threshold_pct")
    min_gbp = runtime_settings.get_float(db, "sales_pace_min_prior_gbp")
    min_orders = runtime_settings.get_int(db, "sales_pace_min_prior_orders")
    titles = {t.id: t for t in db.scalars(select(SalesTitle))}
    pace = [
        PaceRow(
            edition=Ref(id=r["edition"].id, label=edition_label(titles[r["edition"].title_id], r["edition"])),
            title=_title_out(titles[r["edition"].title_id]), edition_date=r["edition"].edition_date, kind=r["edition"].kind,
            booked_gbp=r["booked"], orders=r["orders"],
            previous=Ref(id=r["prev"].id, label=edition_label(titles[r["prev"].title_id], r["prev"])) if r["prev"] else None,
            previous_point_gbp=r["prev_point_gbp"], previous_point_orders=r["prev_point_orders"],
            previous_total_gbp=r["prev_total_gbp"], gap_gbp=r["gap_gbp"], gap_pct=r["gap_pct"],
            state=r["state"], reason=r["reason"],
        )
        for r in edition_pace(db, today, threshold=threshold, min_prior_gbp=min_gbp, min_prior_orders=min_orders)
    ]

    # Weekly booking flow, Monday-start, this year's last 12 weeks against
    # the same 12 weeks 364 days earlier (so weekdays line up).
    this_monday = today - timedelta(days=today.weekday())
    first_week = this_monday - timedelta(weeks=DASHBOARD_WEEKS - 1)
    weeks = [first_week + timedelta(weeks=i) for i in range(DASHBOARD_WEEKS)]

    def weekly_rows(start: date, end: date):
        return db.execute(
            select(SalesOrder.booked_on, SalesOrder.value_gbp).where(
                SalesOrder.status == BOOKED, SalesOrder.booked_on >= start, SalesOrder.booked_on < end)).all()

    span_end = this_monday + timedelta(weeks=1)
    now_rows = weekly_rows(first_week, span_end)
    ly_rows = weekly_rows(first_week - timedelta(days=364), span_end - timedelta(days=364))
    weekly = []
    for w in weeks:
        mine = [float(v) for d, v in now_rows if w <= d < w + timedelta(weeks=1)]
        ly_start = w - timedelta(days=364)
        last = [float(v) for d, v in ly_rows if ly_start <= d < ly_start + timedelta(weeks=1)]
        weekly.append(WeekPoint(week_start=w, orders=len(mine), value_gbp=round(sum(mine), 2), last_year_value_gbp=round(sum(last), 2)))

    # Per-person recent activity: bookings credited + follow-up queue items
    # actioned, for everyone with either. Alphabetical on purpose.
    since = today - timedelta(days=ACTIVITY_DAYS)
    credit_rows = db.execute(
        select(SalesOrderCredit.rep_id, func.count(func.distinct(SalesOrderCredit.order_id)), func.coalesce(func.sum(SalesOrderCredit.amount_gbp), 0))
        .join(SalesOrder, SalesOrderCredit.order_id == SalesOrder.id)
        .where(SalesOrder.status == BOOKED, SalesOrder.booked_on >= since).group_by(SalesOrderCredit.rep_id)).all()
    credit_by_rep = {rid: (n, float(v)) for rid, n, v in credit_rows}
    queue_by_user = {r["owner_user_id"]: r for r in get_rep_metrics(db, days=ACTIVITY_DAYS)["reps"] if r["owner_user_id"]}
    activity = []
    for rep in db.scalars(select(SalesRep).order_by(SalesRep.name)):
        n, v = credit_by_rep.get(rep.id, (0, 0.0))
        q = queue_by_user.get(str(rep.user_id)) if rep.user_id else None
        if not rep.active and n == 0:
            continue
        activity.append(ActivityRow(
            rep=_rep_out(rep), bookings=n, booked_gbp=round(v, 2),
            followups_actioned=q["actioned_total"] if q else (0 if rep.user_id else None),
            followups_outstanding=q["outstanding_now"] if q else (0 if rep.user_id else None)))

    # Booked orders this year with no credit to anyone: shown, never dropped.
    credited = select(SalesOrderCredit.order_id)
    un = db.execute(
        select(func.count(), func.coalesce(func.sum(SalesOrder.value_gbp), 0))
        .join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
        .where(SalesEdition.year == today.year, SalesOrder.status == BOOKED, SalesOrder.value_gbp > 0,
               SalesOrder.id.notin_(credited))).one()
    return Dashboard(
        as_of=today, threshold_pct=threshold, min_prior_gbp=min_gbp, min_prior_orders=min_orders,
        pace=pace, weekly=weekly, activity_days=ACTIVITY_DAYS, activity=activity,
        unattributed=Unattributed(orders=un[0], value_gbp=round(float(un[1]), 2)), unattributed_year=today.year,
    )


# ---- Editions -----------------------------------------------------------------

@router.get("/editions", response_model=list[EditionSummary])
def list_editions(
    year: int | None = None,
    title_id: uuid.UUID | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
) -> list[EditionSummary]:
    q = select(SalesEdition)
    if year:
        q = q.where(SalesEdition.year == year)
    if title_id:
        q = q.where(SalesEdition.title_id == title_id)
    if status:
        q = q.where(SalesEdition.status == status)
    eds = db.scalars(q.order_by(SalesEdition.edition_date.asc().nulls_last(), SalesEdition.name)).all()
    return _edition_summaries(db, list(eds), date.today())


def _get_edition(db: Session, edition_id: uuid.UUID) -> SalesEdition:
    ed = db.get(SalesEdition, edition_id)
    if not ed:
        raise HTTPException(status_code=404, detail="Edition not found")
    return ed


@router.get("/editions/{edition_id}", response_model=EditionDetail)
def get_edition(edition_id: uuid.UUID, db: Session = Depends(get_db)) -> EditionDetail:
    ed = _get_edition(db, edition_id)
    summary = _edition_summaries(db, [ed], date.today())[0]
    orders = db.scalars(select(SalesOrder).where(SalesOrder.edition_id == ed.id)
                        .order_by(SalesOrder.booked_on.asc().nulls_last(), SalesOrder.source_row.asc().nulls_last(), SalesOrder.created_at)).all()
    orders_out = _orders_out(db, list(orders))
    by_rep: dict[uuid.UUID, CreditOut] = {}
    for o in orders_out:
        if o.status != BOOKED:
            continue
        for c in o.credits:
            cur = by_rep.get(c.rep_id)
            by_rep[c.rep_id] = CreditOut(rep_id=c.rep_id, code=c.code, name=c.name,
                                         amount_gbp=round((cur.amount_gbp if cur else 0) + c.amount_gbp, 2))
    title = db.get(SalesTitle, ed.title_id)
    siblings = db.scalars(select(SalesEdition).where(SalesEdition.title_id == ed.title_id, SalesEdition.year == ed.year)).all()
    ordered = sorted(siblings, key=lambda e: (e.edition_date or date(e.year, 12, 31), e.name))
    idx = next(i for i, e in enumerate(ordered) if e.id == ed.id)
    ref = lambda e: Ref(id=e.id, label=edition_label(title, e)) if e else None  # noqa: E731
    next_year = db.scalars(select(SalesEdition).where(SalesEdition.title_id == ed.title_id, SalesEdition.year == ed.year + 1)).all()
    nxt = next((e for e in next_year if equivalent_editions(db, [e]).get(e.id) and equivalent_editions(db, [e])[e.id].id == ed.id), None)
    return EditionDetail(
        **summary.model_dump(),
        notes=ed.notes, source=f"{ed.source_file} › {ed.source_sheet}" if ed.source_file else None,
        digital_url=ed.digital_url, renews_from=ref(equivalent_editions(db, [ed]).get(ed.id)),
        costs=_edition_costs(db, ed, summary.booked_gbp),
        orders_list=orders_out, by_rep=sorted(by_rep.values(), key=lambda c: -c.amount_gbp),
        cancelled_or_moved=sum(1 for o in orders_out if o.status in ("cancelled", "moved")),
        next_edition=ref(nxt),
        prev_in_year=ref(ordered[idx - 1]) if idx > 0 else None,
        next_in_year=ref(ordered[idx + 1]) if idx + 1 < len(ordered) else None,
    )


@router.post("/editions", response_model=EditionSummary, status_code=201)
def create_edition(payload: EditionCreate, db: Session = Depends(get_db)) -> EditionSummary:
    title = db.get(SalesTitle, payload.title_id)
    if not title:
        raise HTTPException(status_code=422, detail="Unknown title")
    name = payload.name.strip()
    if db.scalars(select(SalesEdition).where(SalesEdition.title_id == title.id, SalesEdition.year == payload.year,
                                             func.lower(SalesEdition.name) == name.lower())).first():
        raise HTTPException(status_code=409, detail=f"{title.name} already has an edition called “{name}” in {payload.year}.")
    kind = payload.kind or {"events": "event", "awards": "awards", "digital": "month"}.get(title.product_line, "issue")
    if kind not in ("issue", "month", "event", "awards", "guide"):
        raise HTTPException(status_code=422, detail="Unknown edition kind")
    ed = SalesEdition(id=uuid.uuid4(), title_id=title.id, year=payload.year, name=name, period_label=payload.period_label,
                      edition_date=payload.edition_date, kind=kind, status="open", exchange_rate=payload.exchange_rate,
                      target_gbp=payload.target_gbp, notes=payload.notes)
    db.add(ed)
    db.commit()
    return _edition_summaries(db, [ed], date.today())[0]


@router.patch("/editions/{edition_id}", response_model=EditionSummary)
def update_edition(edition_id: uuid.UUID, payload: EditionPatch, db: Session = Depends(get_db)) -> EditionSummary:
    ed = _get_edition(db, edition_id)
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in ("open", "closed"):
        raise HTTPException(status_code=422, detail="Status must be open or closed")
    for k, v in data.items():
        setattr(ed, k, v.strip() if isinstance(v, str) else v)
    db.commit()
    return _edition_summaries(db, [ed], date.today())[0]


def _edition_costs(db: Session, ed: SalesEdition, booked: float) -> EditionCosts:
    rows = db.scalars(select(SalesEditionCost).where(SalesEditionCost.edition_id == ed.id)
                      .order_by(SalesEditionCost.sort_order, SalesEditionCost.created_at)).all()
    costs = round(sum(float(r.amount_gbp or 0) for r in rows if r.kind == "cost"), 2)
    income = round(sum(float(r.amount_gbp or 0) for r in rows if r.kind == "income"), 2)
    has_costs = any(r.kind == "cost" for r in rows)
    return EditionCosts(
        lines=[CostLineOut(id=r.id, kind=r.kind, label=r.label, section=r.section, from_sheet=r.source_row is not None,
                           amount_gbp=float(r.amount_gbp) if r.amount_gbp is not None else None,
                           amount_inc_vat_gbp=float(r.amount_inc_vat_gbp) if r.amount_inc_vat_gbp is not None else None)
               for r in rows],
        total_costs_gbp=costs, other_income_gbp=income,
        # A sponsorship "income" line restates the bookings on TBTM sheets, so
        # profit is bookings - costs; other income is shown, not added.
        profit_gbp=round(booked - costs, 2) if has_costs else None,
    )


def _costs_editable(db: Session, ed: SalesEdition, identity: Identity) -> None:
    """Signed-off costs are locked (they've been paid on); a change to final costs takes them back to draft."""
    from app.api.routes.commission import can_edit_costs

    can_edit_costs(db, ed, identity)
    ed.costs_final_at = ed.costs_final_by_user_id = None


@router.get("/editions/{edition_id}/costs", response_model=EditionCosts)
def get_costs(edition_id: uuid.UUID, db: Session = Depends(get_db)) -> EditionCosts:
    ed = _get_edition(db, edition_id)
    return _edition_costs(db, ed, _edition_summaries(db, [ed], date.today())[0].booked_gbp)


@router.post("/editions/{edition_id}/costs", response_model=EditionCosts, status_code=201)
def add_cost(edition_id: uuid.UUID, payload: CostLineIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> EditionCosts:
    ed = _get_edition(db, edition_id)
    _costs_editable(db, ed, identity)
    last = db.scalar(select(func.max(SalesEditionCost.sort_order)).where(SalesEditionCost.edition_id == ed.id)) or 0
    db.add(SalesEditionCost(id=uuid.uuid4(), edition_id=ed.id, sort_order=last + 1,
                            **{**payload.model_dump(), "label": payload.label.strip()}))
    db.commit()
    return get_costs(edition_id, db)


@router.put("/editions/{edition_id}/costs/{cost_id}", response_model=EditionCosts)
def update_cost(edition_id: uuid.UUID, cost_id: uuid.UUID, payload: CostLineIn, db: Session = Depends(get_db),
                identity: Identity = Depends(get_identity)) -> EditionCosts:
    line = db.get(SalesEditionCost, cost_id)
    if not line or line.edition_id != edition_id:
        raise HTTPException(status_code=404, detail="Cost line not found")
    _costs_editable(db, _get_edition(db, edition_id), identity)
    for k, v in payload.model_dump().items():
        setattr(line, k, v.strip() if isinstance(v, str) else v)
    db.commit()
    return get_costs(edition_id, db)


@router.delete("/editions/{edition_id}/costs/{cost_id}", response_model=EditionCosts)
def delete_cost(edition_id: uuid.UUID, cost_id: uuid.UUID, db: Session = Depends(get_db),
                identity: Identity = Depends(get_identity)) -> EditionCosts:
    line = db.get(SalesEditionCost, cost_id)
    if line and line.edition_id == edition_id:
        _costs_editable(db, _get_edition(db, edition_id), identity)
        db.delete(line)
        db.commit()
    return get_costs(edition_id, db)


@router.post("/editions/{edition_id}/renewal-pass")
def renewal_pass(edition_id: uuid.UUID, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    """Draft renewal emails now for everyone who advertised in this
    edition's equivalent last cycle and hasn't rebooked (SALES-021's
    "open a renewal pass"). Safe to run more than once."""
    from app.automations.sales_orders import start_renewal_pass

    if not _is_staff(identity):
        raise HTTPException(status_code=403, detail="Only admins and data managers can start a renewal pass.")
    try:
        result = start_renewal_pass(db, _get_edition(db, edition_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return result


# ---- Rate card & online links (SALES-021) -------------------------------------

class RateIn(BaseModel):
    title_id: uuid.UUID
    year: int = Field(ge=2000, le=2100)
    product: str = Field(min_length=1, max_length=120)
    price_gbp: float = Field(ge=0)
    notes: str | None = Field(default=None, max_length=300)


class RateOut(BaseModel):
    id: uuid.UUID
    title_id: uuid.UUID
    year: int
    product: str
    price_gbp: float | None
    notes: str | None = None
    section: str = "print"
    price_type: str = "fixed"
    unit: str = "each"
    specs: str | None = None


class TitleLinks(BaseModel):
    digital_page_url: str | None = Field(default=None, max_length=500)
    digital_issue_url: str | None = Field(default=None, max_length=500)


def _rate_out(r: SalesRate) -> RateOut:
    return RateOut(id=r.id, title_id=r.title_id, year=r.year, product=r.product, price_gbp=float(r.price_gbp) if r.price_gbp is not None else None,
                   notes=r.notes, section=r.section, price_type=r.price_type, unit=r.unit, specs=r.specs)


@router.get("/rates", response_model=list[RateOut])
def list_rates(year: int | None = None, title_id: uuid.UUID | None = None, db: Session = Depends(get_db)) -> list[RateOut]:
    q = select(SalesRate).where(SalesRate.archived.is_(False))
    if year:
        q = q.where(SalesRate.year == year)
    if title_id:
        q = q.where(SalesRate.title_id == title_id)
    return [_rate_out(r) for r in db.scalars(q.order_by(SalesRate.year.desc(), SalesRate.price_gbp.desc().nullslast()))]


def _staff_only(identity: Identity) -> None:
    if not _is_staff(identity):
        raise HTTPException(status_code=403, detail="Only admins and data managers can change the rate card.")


@router.post("/rates", response_model=RateOut, status_code=201)
def create_rate(payload: RateIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> RateOut:
    _staff_only(identity)
    if not db.get(SalesTitle, payload.title_id):
        raise HTTPException(status_code=422, detail="Unknown title")
    product = payload.product.strip()
    if db.scalars(select(SalesRate).where(SalesRate.title_id == payload.title_id, SalesRate.year == payload.year, SalesRate.section == "print",
                                          func.lower(SalesRate.product) == product.lower())).first():
        raise HTTPException(status_code=409, detail=f"“{product}” already has a {payload.year} price for this title - edit it instead.")
    r = SalesRate(id=uuid.uuid4(), **{**payload.model_dump(), "product": product})
    db.add(r)
    db.commit()
    return _rate_out(r)


@router.put("/rates/{rate_id}", response_model=RateOut)
def update_rate(rate_id: uuid.UUID, payload: RateIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> RateOut:
    _staff_only(identity)
    r = db.get(SalesRate, rate_id)
    if not r:
        raise HTTPException(status_code=404, detail="Rate not found")
    for k, v in payload.model_dump().items():
        setattr(r, k, v.strip() if isinstance(v, str) else v)
    db.commit()
    return _rate_out(r)


@router.delete("/rates/{rate_id}", status_code=204, response_model=None)
def delete_rate(rate_id: uuid.UUID, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> None:
    _staff_only(identity)
    r = db.get(SalesRate, rate_id)
    if r:
        db.delete(r)
        db.commit()


@router.put("/titles/{title_id}/links", response_model=TitleOut)
def update_title_links(title_id: uuid.UUID, payload: TitleLinks, db: Session = Depends(get_db),
                       identity: Identity = Depends(get_identity)) -> TitleOut:
    """Where a title's digital edition lives - see SalesTitle.digital_page_url. Staff, or the brand's own publishers."""
    from app.sales.brands import brand_for_title_slug, can_edit_brand
    t = db.get(SalesTitle, title_id)
    if not t:
        raise HTTPException(status_code=404, detail="Title not found")
    brand = brand_for_title_slug(t.slug)
    if not (_is_staff(identity) or (brand and can_edit_brand(db, identity, brand))):
        raise HTTPException(status_code=403, detail="Only admins, data managers and this brand's publishers can change its links.")
    t.digital_page_url = (payload.digital_page_url or "").strip() or None
    t.digital_issue_url = (payload.digital_issue_url or "").strip() or None
    db.commit()
    return _title_out(t)


@router.get("/editions/{edition_id}/export")
def export_edition(edition_id: uuid.UUID, db: Session = Depends(get_db)) -> StreamingResponse:
    """The edition as an .xlsx in the SOR sheet's own layout, so finance
    can keep working from a familiar sheet during the switch-over."""
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill

    detail = get_edition(edition_id, db)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = detail.name[:31]
    bold = Font(bold=True)
    ws.append(["PUBLICATION", detail.title.name])
    ws.append(["MONTH", detail.period_label or (detail.edition_date.strftime("%d %B %Y") if detail.edition_date else ""),
               "", "Exchange rate", detail.exchange_rate or ""])
    ws.append([])
    ws.append(["Cumulative value of publication", detail.booked_gbp, "", "Total invoiced", detail.invoiced_gbp,
               "", "Total difference", round(detail.booked_gbp - detail.invoiced_gbp, 2)])
    ws.append(["Number pages booked", detail.pages])
    ws.append([])
    rep_codes = [c.code for c in detail.by_rep]
    header = ["Date", "Client", "Size", "Series", "Position", "Salesper.", "Rate US$", "£", "Invoice number",
              "Invoice value", "Invoice difference", "Reason for difference", "Status", "Notes", *rep_codes]
    ws.append(header)
    for cell in ws[ws.max_row]:
        cell.font = bold
        cell.fill = PatternFill("solid", fgColor="DDE4F0")
    for o in detail.orders_list:
        credit = {c.code: c.amount_gbp for c in o.credits}
        diff = round(o.value_gbp - (o.invoice_value_gbp or 0), 2) if o.invoice_number else None
        ws.append([
            o.booked_on.strftime("%d.%m.%y") if o.booked_on else "", o.client_name, o.size or "", o.series or "",
            o.position or "", "/".join(c.code for c in o.credits) or (o.rep.code if o.rep else ""),
            o.rate_usd, o.value_gbp, o.invoice_number or "", o.invoice_value_gbp, diff, o.invoice_note or "",
            {"booked": "", "cancelled": "CANX", "contra": "Contra", "moved": "Moved"}[o.status],
            o.notes or "", *[credit.get(code, 0) for code in rep_codes],
        ])
    ws.append([])
    rates = {r.code: float(r.commission_rate) for r in db.scalars(select(SalesRep))}
    ws.append(["Commission payable", *[""] * 13, *[round(c.amount_gbp * rates.get(c.code, 0.02), 2) for c in detail.by_rep]])
    for col, width in zip("ABCDEFGHIJKLMN", (10, 34, 14, 9, 14, 10, 10, 11, 14, 12, 12, 30, 9, 30)):
        ws.column_dimensions[col].width = width
    for row in ws.iter_rows(min_row=8):
        for cell in row:
            cell.alignment = Alignment(vertical="top")
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    fname = re.sub(r"[^A-Za-z0-9 _.-]", "", f"{detail.label} {detail.year}").strip() or "edition"
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}.xlsx"'},
    )


# ---- Orders -------------------------------------------------------------------

def order_query(
    year: list[int] = Query(default=[]),
    title_id: list[uuid.UUID] = Query(default=[]),
    product_line: list[str] = Query(default=[]),
    rep_id: list[uuid.UUID] = Query(default=[]),
    status: list[str] = Query(default=[]),
    edition_id: uuid.UUID | None = None,
    company_id: uuid.UUID | None = None,
    invoiced: bool | None = None,
    linked: bool | None = None,
    has_warning: bool | None = None,
    value_min: float | None = None,
    value_max: float | None = None,
    booked_from: date | None = None,
    booked_to: date | None = None,
    edition_from: date | None = None,
    edition_to: date | None = None,
    uninvoiced: bool = False,
    overdue: bool = False,
    mismatched: bool = False,
    part_invoiced: bool = False,
    warnings: bool = False,
    unlinked: bool = False,
    xero: list[str] = Query(default=[]),
    search: str | None = None,
    sort: str = "edition",
    desc: bool = True,
) -> OrderQuery:
    """Every bookings filter, as query parameters - shared by the list, its
    facet counts and its export. Multi-value filters repeat the parameter
    (?status=booked&status=moved)."""
    return OrderQuery(
        edition_id=edition_id, company_id=company_id, years=year, title_ids=title_id, product_lines=product_line,
        rep_ids=rep_id, statuses=status, invoiced=invoiced, linked=linked,
        has_warning=True if warnings else has_warning, value_min=value_min, value_max=value_max,
        booked_from=booked_from, booked_to=booked_to, edition_from=edition_from, edition_to=edition_to,
        uninvoiced=uninvoiced, overdue=overdue, mismatched=mismatched, part_invoiced=part_invoiced, unlinked=unlinked,
        xero=[x for x in xero if x in XERO_STATES], search=search, sort=sort if sort in ORDER_SORTS else "edition", desc=desc,
    )


@router.get("/orders", response_model=OrdersPage)
def list_orders(
    q: OrderQuery = Depends(order_query),
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
) -> OrdersPage:
    rows, total, value = order_page(db, q, limit, offset)
    return OrdersPage(items=_orders_out(db, rows), total=total, total_value_gbp=value)


@router.get("/orders/facets")
def orders_facets(q: OrderQuery = Depends(order_query), db: Session = Depends(get_db)) -> dict[str, dict[str, int]]:
    """How many bookings each filter option would give, under the other
    active filters - the counts shown beside every option in the sidebar."""
    return order_facets(db, q)


@router.get("/orders/export")
def export_orders(q: OrderQuery = Depends(order_query), db: Session = Depends(get_db)) -> StreamingResponse:
    """Exactly the filtered, sorted list on screen as .xlsx (up to 20,000 rows)."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill

    rows, _, _ = order_page(db, q, 20000, 0)
    items = _orders_out(db, rows)
    title_names = {t.id: t.name for t in db.scalars(select(SalesTitle))}
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Bookings"
    ws.append(["Client", "CRM company", "Title", "Edition", "Edition date", "Booked", "Size", "Series", "Position",
               "Salesperson(s)", "Value £", "Agency commission £", "Invoice number", "Invoice value £",
               "Reason for difference", "Status", "Status note", "Order ref", "Notes", "Needs a check"])
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="DDE4F0")
    for o in items:
        ws.append([
            o.client_name, o.company.label if o.company else None, title_names.get(o.title_id), o.edition_label,
            o.edition_date, o.booked_on, o.size, o.series, o.position,
            " / ".join(c.code for c in o.credits) or (o.rep.code if o.rep else None), o.value_gbp,
            o.agency_commission_gbp, o.invoice_number, o.invoice_value_gbp, o.invoice_note, o.status,
            o.status_reason, o.order_ref, o.notes, o.import_warning,
        ])
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for col, width in zip("ABCDEFGHIJKLMNOPQRST", (30, 28, 22, 26, 12, 12, 16, 10, 10, 14, 12, 12, 14, 12, 30, 11, 24, 12, 30, 40)):
        ws.column_dimensions[col].width = width
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    stamp = date.today().isoformat()
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f'attachment; filename="BMI bookings {stamp}.xlsx"'})


def _get_order(db: Session, order_id: uuid.UUID) -> SalesOrder:
    o = db.get(SalesOrder, order_id)
    if not o:
        raise HTTPException(status_code=404, detail="Booking not found")
    return o


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: uuid.UUID, db: Session = Depends(get_db)) -> OrderOut:
    return _orders_out(db, [_get_order(db, order_id)])[0]


@router.post("/orders", response_model=OrderOut, status_code=201)
def create_order(payload: OrderCreate, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> OrderOut:
    ed = _get_edition(db, payload.edition_id)
    _check_status(payload.status)
    if payload.rep_id and not db.get(SalesRep, payload.rep_id):
        raise HTTPException(status_code=422, detail="Unknown salesperson")
    if payload.company_id and not db.get(Company, payload.company_id):
        raise HTTPException(status_code=422, detail="Unknown company")
    title = db.get(SalesTitle, ed.title_id)
    data = payload.model_dump(exclude={"credits"})
    order = SalesOrder(id=uuid.uuid4(), **{k: (v.strip() if isinstance(v, str) else v) for k, v in data.items()},
                       pages=parse_pages(payload.size, title.product_line), created_by_user_id=identity.user_uuid)
    if order.invoice_number and order.invoice_value_gbp is None:
        order.invoice_value_gbp = order.value_gbp
    if order.invoice_number and not order.invoiced_on:
        order.invoiced_on = date.today()
    db.add(order)
    db.flush()
    if payload.credits:
        _set_credits(db, order, payload.credits)
    elif order.rep_id and order.value_gbp:
        db.add(SalesOrderCredit(id=uuid.uuid4(), order_id=order.id, rep_id=order.rep_id, amount_gbp=order.value_gbp))
    db.commit()
    return _orders_out(db, [order])[0]


_AUDITED = ("client_name", "company_id", "rep_id", "booked_on", "size", "series", "position", "rate_usd", "value_gbp",
            "agency_commission_gbp", "commission_rate", "invoice_number", "invoice_value_gbp", "invoiced_on",
            "invoice_note", "status", "moved_to_edition_id", "notes")


@router.patch("/orders/{order_id}", response_model=OrderOut)
def update_order(order_id: uuid.UUID, payload: OrderPatch, db: Session = Depends(get_db),
                 identity: Identity = Depends(get_identity)) -> OrderOut:
    order = _get_order(db, order_id)
    data = payload.model_dump(exclude_unset=True, exclude={"credits", "clear_company", "clear_warning"})
    if payload.clear_company:
        data["company_id"] = None
    if "status" in data:
        _check_status(data["status"])
    if data.get("rep_id") and not db.get(SalesRep, data["rep_id"]):
        raise HTTPException(status_code=422, detail="Unknown salesperson")
    if data.get("company_id") and not db.get(Company, data["company_id"]):
        raise HTTPException(status_code=422, detail="Unknown company")
    if data.get("moved_to_edition_id") and not db.get(SalesEdition, data["moved_to_edition_id"]):
        raise HTTPException(status_code=422, detail="Unknown edition")

    before = {k: getattr(order, k) for k in _AUDITED}
    old_rep, old_value = order.rep_id, float(order.value_gbp or 0)
    for k, v in data.items():
        setattr(order, k, v.strip() or None if isinstance(v, str) and k != "client_name" else v)
    if "company_id" in data and data["company_id"]:
        order.match_dismissed = False
    # The invoiced amount comes from Xero only when nobody recorded one; a typed amount is kept.
    take_from_xero = "invoice_number" in data and (order.invoice_value_gbp is None or order.invoice_from_xero) \
        and not ("invoice_value_gbp" in data and data["invoice_value_gbp"] is not None and data["invoice_value_gbp"] != before["invoice_value_gbp"])
    if data.get("invoice_number") and order.invoice_value_gbp is None:
        order.invoice_value_gbp = order.value_gbp
    if data.get("invoice_number") and not order.invoiced_on:
        order.invoiced_on = date.today()
    if "invoice_number" in data:
        sync_link_after_edit(db, order, take_figures=take_from_xero)  # keep the real Xero link in step with what was typed
    elif "invoice_value_gbp" in data or "invoiced_on" in data:
        order.invoice_from_xero = False  # a person changed the figures - they're theirs now
    if "size" in data:
        title = db.get(SalesTitle, db.get(SalesEdition, order.edition_id).title_id)
        order.pages = parse_pages(order.size, title.product_line)
    if payload.clear_warning:
        order.import_warning = None
    after = {k: getattr(order, k) for k in _AUDITED}
    record_field_changes(db, entity_type="sales_order", entity_id=order.id, before=before,
                         updates={k: after[k] for k in _AUDITED if k in data}, changed_by_user_id=identity.user_uuid)
    if payload.credits is not None:
        _set_credits(db, order, payload.credits)
    elif order.rep_id != old_rep or float(order.value_gbp or 0) != old_value:
        _sync_single_credit(db, order, old_rep, old_value)
    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    return _orders_out(db, [order])[0]


@router.delete("/orders/{order_id}", status_code=204, response_model=None)
def delete_order(order_id: uuid.UUID, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> None:
    """Hard delete, for an order entered by mistake - staff only. A real
    cancellation should use status "cancelled" instead, which keeps it on
    the record (the SOR's own "CANX" convention)."""
    if not _is_staff(identity):
        raise HTTPException(status_code=403, detail="Only administrators and data managers can delete a booking - mark it cancelled instead.")
    order = _get_order(db, order_id)
    db.delete(order)
    db.commit()


@router.post("/orders/{order_id}/xero-unlink", response_model=OrderOut)
def unlink_xero(order_id: uuid.UUID, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> OrderOut:
    """Undo an invoice link the matcher made (automatic or confirmed): clears
    the invoice number, value and date it filled in. The invoice won't be
    offered for this booking again."""
    order = _get_order(db, order_id)
    try:
        unlink_order(db, order, identity.user_uuid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return _orders_out(db, [order])[0]


class XeroChoice(BaseModel):
    id: uuid.UUID
    number: str | None = None
    contact: str | None = None
    reference: str | None = None
    lines: str | None = None
    issued_on: date | None = None
    currency: str
    net: float
    state: str
    url: str
    fit: list[str] = []


@router.get("/orders/{order_id}/xero-choices", response_model=list[XeroChoice])
def xero_choices(order_id: uuid.UUID, q: str = "", db: Session = Depends(get_db)) -> list[XeroChoice]:
    """Invoices in Xero this booking could be linked to (ones no booking has yet), most likely first."""
    order = _get_order(db, order_id)
    return [XeroChoice(id=f["id"], number=f["number"], contact=f["contact"], reference=f["reference"], lines=f["lines"],
                       issued_on=f["issued_on"], currency=f["currency"], net=f["net"], state=f["state"], url=f["url"], fit=f["fit"])
            for f in invoice_choices(db, order, q)]


class XeroLinkIn(BaseModel):
    invoice_id: uuid.UUID


def _invoice_or_error(db: Session, invoice_id: uuid.UUID) -> XeroInvoice:
    inv = db.get(XeroInvoice, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="That invoice isn't in the copy of Xero yet - try again after the next sync.")
    if inv.status in ("VOIDED", "DELETED"):
        raise HTTPException(status_code=409, detail="That invoice has been voided or deleted in Xero.")
    return inv


@router.post("/orders/{order_id}/xero-link", response_model=OrderOut)
def link_xero(order_id: uuid.UUID, payload: XeroLinkIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> OrderOut:
    """Links a booking to an invoice someone picked from Xero: the number, invoiced amount and date come from Xero."""
    order = _get_order(db, order_id)
    inv = _invoice_or_error(db, payload.invoice_id)
    if order.xero_invoice_id == inv.id:
        return _orders_out(db, [order])[0]
    link_bookings(db, inv, [order], "confirmed", identity.user_uuid)
    db.commit()
    return _orders_out(db, [order])[0]


class BookingChoice(BaseModel):
    key: str
    suggested: bool
    bookings: list[dict]
    total_gbp: float
    reasons: list[str]


@router.get("/xero/invoices/{invoice_id}/choices", response_model=list[BookingChoice])
def xero_invoice_choices(invoice_id: uuid.UUID, q: str = "", db: Session = Depends(get_db)) -> list[BookingChoice]:
    """Bookings this invoice could be for: the matcher's suggestions, then any waiting booking matching `q`."""
    inv = _invoice_or_error(db, invoice_id)
    return [BookingChoice(**c) for c in booking_choices(db, inv, q)]


class InvoiceLinkIn(BaseModel):
    order_ids: list[uuid.UUID] = Field(min_length=1, max_length=10)


@router.post("/xero/invoices/{invoice_id}/link", response_model=list[OrderOut])
def link_invoice_to_bookings(invoice_id: uuid.UUID, payload: InvoiceLinkIn, db: Session = Depends(get_db),
                             identity: Identity = Depends(get_identity)) -> list[OrderOut]:
    """Links an invoice from the "In Xero, not in the register" list to the booking(s) it was raised for."""
    inv = _invoice_or_error(db, invoice_id)
    orders = [_get_order(db, oid) for oid in payload.order_ids]
    for o in orders:
        if o.xero_invoice_id and o.xero_invoice_id != inv.id:
            raise HTTPException(status_code=409, detail=f"“{o.client_name}” is already linked to invoice {o.invoice_number}.")
    link_bookings(db, inv, orders, "confirmed", identity.user_uuid)
    db.commit()
    return _orders_out(db, orders)


class UnmatchedInvoice(BaseModel):
    id: uuid.UUID
    number: str | None = None
    contact: str | None = None
    reference: str | None = None
    lines: str | None = None
    issued_on: date | None = None
    currency: str
    net: float
    total: float
    state: str
    url: str


class UnmatchedInvoices(BaseModel):
    as_of: datetime | None = None
    items: list[UnmatchedInvoice]


@router.get("/xero/unmatched", response_model=UnmatchedInvoices)
def unmatched_xero_invoices(db: Session = Depends(get_db)) -> UnmatchedInvoices:
    """Invoices in Xero that no booking in the register fits - billed but
    missing from the register, or with amounts that don't line up. As of the
    last matching run."""
    from app.automations.xero_matching import unmatched_invoice_ids

    ids, at = unmatched_invoice_ids(db)
    claimed = select(SalesOrder.xero_invoice_id).where(SalesOrder.xero_invoice_id.isnot(None))
    rows = db.scalars(select(XeroInvoice).where(XeroInvoice.id.in_(ids), XeroInvoice.id.notin_(claimed))
                      .order_by(XeroInvoice.issued_on.desc().nulls_last())).all() if ids else []
    from app.sales.invoice_match import invoice_facts

    items = []
    for inv in rows:
        f = invoice_facts(inv)
        items.append(UnmatchedInvoice(id=inv.id, number=inv.invoice_number, contact=inv.contact_name, reference=inv.reference,
                                      lines=inv.line_text, issued_on=inv.issued_on, currency=f["currency"], net=f["net"],
                                      total=f["total"], state=f["state"], url=f["url"]))
    return UnmatchedInvoices(as_of=datetime.fromisoformat(at) if at else None, items=items)


@router.get("/orders/{order_id}/changes", response_model=list[FieldChangeOut])
def order_changes(order_id: uuid.UUID, db: Session = Depends(get_db)) -> list[FieldChangeOut]:
    rows = db.scalars(select(FieldChange).where(FieldChange.entity_type == "sales_order", FieldChange.entity_id == order_id)
                      .order_by(FieldChange.changed_at.desc()).limit(200)).all()
    user_ids = {r.changed_by_user_id for r in rows if r.changed_by_user_id}
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_(user_ids)))} if user_ids else {}
    return [FieldChangeOut(id=r.id, field=r.field, old_value=r.old_value, new_value=r.new_value, changed_at=r.changed_at,
                           changed_by=UserSummary.model_validate(users[r.changed_by_user_id]) if r.changed_by_user_id in users else None)
            for r in rows]


@router.get("/clients", response_model=list[ClientSuggestion])
def client_suggestions(search: str = Query(min_length=1), db: Session = Depends(get_db)) -> list[ClientSuggestion]:
    """Client names already used in the register, for the booking form's
    autocomplete - keeps "Air Canada" from becoming "Air Canada Ltd" and
    "AirCanada" across three reps."""
    rows = db.execute(
        select(SalesOrder.client_name, SalesOrder.company_id, func.count())
        .where(SalesOrder.client_name.ilike(f"%{search.strip()}%"))
        .group_by(SalesOrder.client_name, SalesOrder.company_id).order_by(func.count().desc()).limit(8)
    ).all()
    comp_ids = {r[1] for r in rows if r[1]}
    comps = {c.id: c.name for c in db.execute(select(Company.id, Company.name).where(Company.id.in_(comp_ids)))} if comp_ids else {}
    return [ClientSuggestion(client_name=n, company=Ref(id=c, label=comps.get(c, "")) if c else None, orders=k) for n, c, k in rows]


@router.get("/companies/{company_id}/orders", response_model=CompanyBookings)
def company_orders(company_id: uuid.UUID, db: Session = Depends(get_db)) -> CompanyBookings:
    orders = db.scalars(select(SalesOrder).join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
                        .where(SalesOrder.company_id == company_id)
                        .order_by(SalesEdition.year.desc(), SalesOrder.booked_on.desc().nulls_last())).all()
    out = _orders_out(db, list(orders))
    booked = [o for o in out if o.status == BOOKED]
    by_year: dict[int, float] = defaultdict(float)
    eds = {e.id: e for e in db.scalars(select(SalesEdition).where(SalesEdition.id.in_({o.edition_id for o in orders})))} if orders else {}
    titles = {t.id: t.name for t in db.scalars(select(SalesTitle))}
    for o in booked:
        by_year[eds[o.edition_id].year] += o.value_gbp
    dates = [o.booked_on for o in booked if o.booked_on]
    return CompanyBookings(
        lifetime_gbp=round(sum(o.value_gbp for o in booked), 2), orders=len(booked),
        first_booked=min(dates) if dates else None, last_booked=max(dates) if dates else None,
        titles=sorted({titles[o.title_id] for o in booked}), by_year=dict(sorted(by_year.items(), reverse=True)), items=out,
    )


# ---- Commissions ----------------------------------------------------------------

@router.get("/commissions", response_model=Commissions)
def commissions(year: int | None = None, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> Commissions:
    year = year or date.today().year
    staff = _is_staff(identity)
    me = None if staff else _my_rep(db, identity)
    if not staff and not me:
        return Commissions(year=year, reps=[], scoped_to_me=True)
    q = (select(SalesOrderCredit, SalesOrder, SalesEdition)
         .join(SalesOrder, SalesOrderCredit.order_id == SalesOrder.id)
         .join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
         .where(SalesEdition.year == year, SalesOrder.status == BOOKED))
    if me:
        q = q.where(SalesOrderCredit.rep_id == me.id)
    reps = {r.id: r for r in db.scalars(select(SalesRep))}
    titles = {t.id: t for t in db.scalars(select(SalesTitle))}
    per: dict[uuid.UUID, dict] = {}
    for credit, order, ed in db.execute(q).all():
        rep = reps[credit.rep_id]
        rate = float(order.commission_rate if order.commission_rate is not None else rep.commission_rate)
        amount = float(credit.amount_gbp)
        entry = per.setdefault(rep.id, {"credit": 0.0, "commission": 0.0, "orders": set(), "eds": {}})
        entry["credit"] += amount
        entry["commission"] += amount * rate
        entry["orders"].add(order.id)
        e = entry["eds"].setdefault(ed.id, {"ed": ed, "credit": 0.0, "commission": 0.0, "orders": 0})
        e["credit"] += amount
        e["commission"] += amount * rate
        e["orders"] += 1
    out = []
    for rep_id, v in per.items():
        eds = sorted(v["eds"].values(), key=lambda x: (x["ed"].edition_date or date(year, 12, 31), x["ed"].name))
        out.append(CommissionRep(
            rep=_rep_out(reps[rep_id]), credit_gbp=round(v["credit"], 2), commission_gbp=round(v["commission"], 2),
            orders=len(v["orders"]),
            editions=[CommissionEditionRow(
                edition=Ref(id=x["ed"].id, label=edition_label(titles[x["ed"].title_id], x["ed"])),
                title=titles[x["ed"].title_id].name, edition_date=x["ed"].edition_date,
                credit_gbp=round(x["credit"], 2), commission_gbp=round(x["commission"], 2), orders=x["orders"],
            ) for x in eds],
        ))
    out.sort(key=lambda r: -r.credit_gbp)
    return Commissions(year=year, reps=out, scoped_to_me=not staff)


# ---- Renewals -------------------------------------------------------------------

def renewal_candidates(db: Session, title_id: uuid.UUID, year: int) -> tuple[list[dict], int, int]:
    """Advertisers who booked this title last year but haven't booked it
    yet this year. Returns (rows, previous_advertisers, rebooked)."""
    def orders_for(y: int):
        return db.execute(
            select(SalesOrder, SalesEdition).join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
            .where(SalesEdition.title_id == title_id, SalesEdition.year == y, SalesOrder.status == BOOKED)
        ).all()
    def key(name: str) -> str:
        return normalise(name) or name.strip().lower()

    prev = orders_for(year - 1)
    now = orders_for(year)
    # Normalised names, so "Monty's" / "Montys" and "Sky-Blue" / "SkyBlue"
    # are one advertiser, not a renewal candidate and a rebooking.
    now_keys = {key(o.client_name) for o, _ in now}
    now_companies = {o.company_id for o, _ in now if o.company_id}
    groups: dict[str, list] = defaultdict(list)
    for o, e in prev:
        groups[key(o.client_name)].append((o, e))
    rows = []
    rebooked = 0
    for k, items in groups.items():
        if k in now_keys or any(o.company_id and o.company_id in now_companies for o, _ in items):
            rebooked += 1
            continue
        total = sum(float(o.value_gbp) for o, _ in items)
        if total <= 0:
            continue  # only ever free/contra placements - nothing to renew
        last_o, last_e = max(items, key=lambda it: (it[0].booked_on or date.min, it[1].edition_date or date.min))
        rows.append({"order": last_o, "edition": last_e, "total": total, "count": len(items)})
    rows.sort(key=lambda r: -r["total"])
    return rows, len(groups), rebooked


@router.get("/renewals", response_model=Renewals)
def renewals(title_id: uuid.UUID, year: int | None = None, db: Session = Depends(get_db)) -> Renewals:
    year = year or date.today().year
    title = db.get(SalesTitle, title_id)
    if not title:
        raise HTTPException(status_code=404, detail="Title not found")
    rows, previous, rebooked = renewal_candidates(db, title_id, year)
    reps = {r.id: r for r in db.scalars(select(SalesRep))}
    comp_ids = {r["order"].company_id for r in rows if r["order"].company_id}
    comps = {c.id: c.name for c in db.execute(select(Company.id, Company.name).where(Company.id.in_(comp_ids)))} if comp_ids else {}
    return Renewals(
        title=_title_out(title), year=year, previous_advertisers=previous, rebooked=rebooked,
        retention_rate=(rebooked / previous) if previous else None,
        not_rebooked_value_gbp=round(sum(r["total"] for r in rows), 2),
        items=[RenewalRow(
            client_name=r["order"].client_name,
            company=Ref(id=r["order"].company_id, label=comps.get(r["order"].company_id, "")) if r["order"].company_id else None,
            rep=_rep_out(reps[r["order"].rep_id]) if r["order"].rep_id in reps else None,
            last_edition=Ref(id=r["edition"].id, label=edition_label(title, r["edition"])),
            last_booked_on=r["order"].booked_on, last_value_gbp=float(r["order"].value_gbp),
            last_year_value_gbp=round(r["total"], 2), last_year_orders=r["count"], size=r["order"].size,
        ) for r in rows],
    )
