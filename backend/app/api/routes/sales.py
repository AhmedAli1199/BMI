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
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.schemas import FieldChangeOut, UserSummary
from app.core.identity import Identity, get_identity
from app.db.session import get_db
from app.models import Company, FieldChange, SalesEdition, SalesOrder, SalesOrderCredit, SalesRep, SalesTitle, User
from app.roles import CAN_USE_AUTOMATIONS
from app.sales.matching import normalise
from app.sales.analytics import BOOKED, edition_totals, equivalent_editions, same_point_last_year
from app.sales.reference import ensure_reference_data
from app.sales.sor_import import parse_pages
from app.services.field_audit import record_field_changes

router = APIRouter(prefix="/sales", tags=["sales"])


# ---- Schemas ----------------------------------------------------------------

class TitleOut(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    product_line: str
    crm_source_db: str


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


class EditionDetail(EditionSummary):
    notes: str | None = None
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
    return TitleOut(id=t.id, slug=t.slug, name=t.name, product_line=t.product_line, crm_source_db=t.crm_source_db)


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
        ))
    return out


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

@router.get("/orders", response_model=OrdersPage)
def list_orders(
    year: int | None = None,
    title_id: uuid.UUID | None = None,
    rep_id: uuid.UUID | None = None,
    status: str | None = None,
    uninvoiced: bool = False,
    overdue: bool = False,
    mismatched: bool = False,
    part_invoiced: bool = False,
    warnings: bool = False,
    unlinked: bool = False,
    search: str | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
) -> OrdersPage:
    q = select(SalesOrder).join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
    if year:
        q = q.where(SalesEdition.year == year)
    if title_id:
        q = q.where(SalesEdition.title_id == title_id)
    if rep_id:
        q = q.where(or_(SalesOrder.rep_id == rep_id, SalesOrder.id.in_(
            select(SalesOrderCredit.order_id).where(SalesOrderCredit.rep_id == rep_id))))
    if status:
        q = q.where(SalesOrder.status == status)
    if uninvoiced or overdue:
        q = q.where(SalesOrder.status == BOOKED, SalesOrder.value_gbp > 0, SalesOrder.invoice_number.is_(None))
    if overdue:
        q = q.where(func.coalesce(SalesEdition.edition_date, func.make_date(SalesEdition.year, 1, 1)) <= date.today())
    if mismatched or part_invoiced:
        # Compared per client within an edition, not per row: one booking
        # invoiced in two lines (£1,500 on one invoice, £1,000 "wanted on
        # separate invoice") matches as a whole. Rows with an invoice
        # number but no amount entered are unknown, not a difference, and
        # under £2 is currency-conversion rounding.
        client_key = func.lower(func.trim(SalesOrder.client_name))
        g = (select(SalesOrder.edition_id.label("ed"), client_key.label("ck"))
             .where(SalesOrder.status == BOOKED)
             .group_by(SalesOrder.edition_id, client_key)
             .having(func.count(SalesOrder.invoice_value_gbp) > 0)
             .having(func.abs(func.sum(SalesOrder.value_gbp)
                              - func.sum(func.coalesce(SalesOrder.invoice_value_gbp, SalesOrder.value_gbp))
                              - func.sum(func.coalesce(SalesOrder.agency_commission_gbp, 0))) >= 2))
        reason_any = func.bool_or(func.coalesce(func.trim(SalesOrder.invoice_note), "") != "")
        g = g.having(reason_any if part_invoiced else ~reason_any).subquery()
        q = q.where(SalesOrder.status == BOOKED, SalesOrder.invoice_number.isnot(None),
                    SalesOrder.invoice_value_gbp.isnot(None),
                    select(1).where(g.c.ed == SalesOrder.edition_id, g.c.ck == client_key).exists())
    if warnings:
        q = q.where(SalesOrder.import_warning.isnot(None))
    if unlinked:
        q = q.where(SalesOrder.company_id.is_(None), SalesOrder.match_dismissed.is_(False))
    if search:
        like = f"%{search.strip()}%"
        q = q.where(or_(SalesOrder.client_name.ilike(like), SalesOrder.invoice_number.ilike(like), SalesOrder.order_ref.ilike(like)))
    sub = q.with_only_columns(SalesOrder.value_gbp).subquery()
    total, value = db.execute(select(func.count(), func.coalesce(func.sum(sub.c.value_gbp), 0)).select_from(sub)).one()
    rows = db.scalars(q.order_by(func.coalesce(SalesEdition.edition_date, func.make_date(SalesEdition.year, 1, 1)).desc(),
                                 SalesOrder.booked_on.desc().nulls_last()).limit(limit).offset(offset)).all()
    return OrdersPage(items=_orders_out(db, list(rows)), total=total, total_value_gbp=float(value))


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
    if data.get("invoice_number") and order.invoice_value_gbp is None:
        order.invoice_value_gbp = order.value_gbp
    if data.get("invoice_number") and not order.invoiced_on:
        order.invoiced_on = date.today()
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
