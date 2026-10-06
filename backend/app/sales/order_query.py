"""One definition of "which bookings, in what order" for every bookings
table in the app - All bookings, the Invoicing views, an edition's own
list - plus the counts beside each filter option (facets) and the Excel
export of exactly what's on screen.

Keeping it in one place means a filter added here works everywhere at once
and the list, its totals, its facet counts and its export can never
disagree about which rows they mean.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, fields, replace
from datetime import date

from sqlalchemy import Select, and_, case, func, or_, select, union_all
from sqlalchemy.orm import Session

from app.sales.invoice_numbers import canonical_sql
from app.models import Company, SalesEdition, SalesOrder, SalesOrderCredit, SalesRep, SalesTitle, XeroInvoice
from app.sales.analytics import BOOKED

SORTS = ("edition", "booked", "client", "value", "invoice", "rep", "status", "title", "size")


@dataclass
class OrderQuery:
    # Scope
    edition_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    # Multi-value filters (empty = any)
    years: list[int] = field(default_factory=list)
    title_ids: list[uuid.UUID] = field(default_factory=list)
    product_lines: list[str] = field(default_factory=list)
    rep_ids: list[uuid.UUID] = field(default_factory=list)
    statuses: list[str] = field(default_factory=list)
    # Tri-state filters: None = any
    invoiced: bool | None = None
    linked: bool | None = None
    has_warning: bool | None = None
    # Ranges
    value_min: float | None = None
    value_max: float | None = None
    booked_from: date | None = None
    booked_to: date | None = None
    edition_from: date | None = None
    edition_to: date | None = None
    # Invoicing views (kept as named shortcuts - their rules are subtle)
    uninvoiced: bool = False
    overdue: bool = False
    mismatched: bool = False
    part_invoiced: bool = False
    unlinked: bool = False
    # Payment state in Xero: paid, part_paid, unpaid, overdue, voided, not_in_xero
    xero: list[str] = field(default_factory=list)
    search: str | None = None
    sort: str = "edition"
    desc: bool = True

    def without(self, *names: str) -> "OrderQuery":
        """A copy with some filters cleared - a facet counts its options
        under every *other* active filter, so ticking one status still
        shows how many each other status would give."""
        blank = OrderQuery()
        return replace(self, **{n: getattr(blank, n) for n in names})

    def is_filtered(self) -> bool:
        blank = OrderQuery()
        return any(getattr(self, f.name) != getattr(blank, f.name) for f in fields(self) if f.name not in ("sort", "desc"))


def _edition_date():
    return func.coalesce(SalesEdition.edition_date, func.make_date(SalesEdition.year, 1, 1))


def _difference_groups(explained: bool):
    """(edition, client) pairs whose invoices differ from their bookings -
    compared per client within an edition, not per row: one booking
    invoiced in two lines matches as a whole. Rows with an invoice number
    but no amount are unknown, not a difference, and under £2 is
    currency-conversion rounding."""
    client_key = func.lower(func.trim(SalesOrder.client_name))
    g = (select(SalesOrder.edition_id.label("ed"), client_key.label("ck"))
         .where(SalesOrder.status == BOOKED)
         .group_by(SalesOrder.edition_id, client_key)
         .having(func.count(SalesOrder.invoice_value_gbp) > 0)
         .having(func.abs(func.sum(SalesOrder.value_gbp)
                          - func.sum(func.coalesce(SalesOrder.invoice_value_gbp, SalesOrder.value_gbp))
                          - func.sum(func.coalesce(SalesOrder.agency_commission_gbp, 0))) >= 2))
    reason_any = func.bool_or(func.coalesce(func.trim(SalesOrder.invoice_note), "") != "")
    g = g.having(reason_any if explained else ~reason_any).subquery()
    return and_(SalesOrder.status == BOOKED, SalesOrder.invoice_number.isnot(None),
                SalesOrder.invoice_value_gbp.isnot(None),
                select(1).where(g.c.ed == SalesOrder.edition_id, g.c.ck == client_key).exists())


XERO_STATES = ("paid", "part_paid", "unpaid", "overdue", "voided", "not_in_xero")


def xero_state():
    """The booking's payment state in Xero, matched by invoice number
    (spaces and case ignored). NULL when the booking has no invoice."""
    key = canonical_sql(SalesOrder.invoice_number)
    state = (
        select(case(
            (XeroInvoice.status.in_(("VOIDED", "DELETED")), "voided"),
            (func.coalesce(XeroInvoice.amount_due, 0) <= 0, "paid"),
            (XeroInvoice.due_on < date.today(), "overdue"),
            (func.coalesce(XeroInvoice.amount_paid, 0) > 0, "part_paid"),
            else_="unpaid",
        ))
        .where(or_(XeroInvoice.id == SalesOrder.xero_invoice_id, XeroInvoice.number_key == key))
        .order_by((XeroInvoice.id == SalesOrder.xero_invoice_id).desc(), XeroInvoice.updated_at_xero.desc().nulls_last())
        .limit(1)
        .scalar_subquery()
    )
    return case((SalesOrder.invoice_number.is_(None), None), else_=func.coalesce(state, "not_in_xero"))


def conditions(q: OrderQuery) -> list:
    c: list = []
    if q.edition_id:
        c.append(SalesOrder.edition_id == q.edition_id)
    if q.company_id:
        c.append(SalesOrder.company_id == q.company_id)
    if q.years:
        c.append(SalesEdition.year.in_(q.years))
    if q.title_ids:
        c.append(SalesEdition.title_id.in_(q.title_ids))
    if q.product_lines:
        c.append(SalesEdition.title_id.in_(select(SalesTitle.id).where(SalesTitle.product_line.in_(q.product_lines))))
    if q.rep_ids:
        c.append(or_(SalesOrder.rep_id.in_(q.rep_ids), SalesOrder.id.in_(
            select(SalesOrderCredit.order_id).where(SalesOrderCredit.rep_id.in_(q.rep_ids)))))
    if q.statuses:
        c.append(SalesOrder.status.in_(q.statuses))
    if q.invoiced is True:
        c.append(SalesOrder.invoice_number.isnot(None))
    elif q.invoiced is False:
        c.extend([SalesOrder.invoice_number.is_(None), SalesOrder.status == BOOKED, SalesOrder.value_gbp > 0])
    if q.linked is True:
        c.append(SalesOrder.company_id.isnot(None))
    elif q.linked is False:
        c.append(SalesOrder.company_id.is_(None))
    if q.has_warning is True:
        c.append(SalesOrder.import_warning.isnot(None))
    elif q.has_warning is False:
        c.append(SalesOrder.import_warning.is_(None))
    if q.value_min is not None:
        c.append(SalesOrder.value_gbp >= q.value_min)
    if q.value_max is not None:
        c.append(SalesOrder.value_gbp <= q.value_max)
    if q.booked_from:
        c.append(SalesOrder.booked_on >= q.booked_from)
    if q.booked_to:
        c.append(SalesOrder.booked_on <= q.booked_to)
    if q.edition_from:
        c.append(_edition_date() >= q.edition_from)
    if q.edition_to:
        c.append(_edition_date() <= q.edition_to)
    if q.uninvoiced or q.overdue:
        c.extend([SalesOrder.status == BOOKED, SalesOrder.value_gbp > 0, SalesOrder.invoice_number.is_(None)])
    if q.overdue:
        c.append(_edition_date() <= date.today())
    if q.mismatched:
        c.append(_difference_groups(explained=False))
    if q.part_invoiced:
        c.append(_difference_groups(explained=True))
    if q.unlinked:
        c.extend([SalesOrder.company_id.is_(None), SalesOrder.match_dismissed.is_(False)])
    if q.xero:
        c.append(xero_state().in_(q.xero))
    if q.search and q.search.strip():
        like = f"%{q.search.strip()}%"
        c.append(or_(
            SalesOrder.client_name.ilike(like), SalesOrder.invoice_number.ilike(like), SalesOrder.order_ref.ilike(like),
            SalesOrder.size.ilike(like), SalesOrder.notes.ilike(like), SalesOrder.invoice_note.ilike(like),
            SalesEdition.name.ilike(like),
            SalesOrder.company_id.in_(select(Company.id).where(Company.name.ilike(like))),
            SalesOrder.rep_id.in_(select(SalesRep.id).where(or_(SalesRep.name.ilike(like), SalesRep.code.ilike(like)))),
        ))
    return c


def base(q: OrderQuery, *columns) -> Select:
    stmt = select(*(columns or (SalesOrder,))).select_from(SalesOrder).join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
    return stmt.where(*conditions(q))


def ordered(stmt: Select, q: OrderQuery) -> Select:
    key = {
        "booked": SalesOrder.booked_on,
        "client": func.lower(SalesOrder.client_name),
        "value": SalesOrder.value_gbp,
        "invoice": SalesOrder.invoice_number,
        "rep": select(SalesRep.code).where(SalesRep.id == SalesOrder.rep_id).scalar_subquery(),
        "status": SalesOrder.status,
        "title": select(SalesTitle.name).where(SalesTitle.id == SalesEdition.title_id).scalar_subquery(),
        "size": func.lower(SalesOrder.size),
    }.get(q.sort, _edition_date())
    first = key.desc().nulls_last() if q.desc else key.asc().nulls_last()
    # Stable tie-breaks so paging never repeats or skips a row.
    return stmt.order_by(first, _edition_date().desc(), SalesOrder.booked_on.desc().nulls_last(), SalesOrder.id)


def page(db: Session, q: OrderQuery, limit: int, offset: int) -> tuple[list[SalesOrder], int, float]:
    sub = base(q, SalesOrder.value_gbp).subquery()
    total, value = db.execute(select(func.count(), func.coalesce(func.sum(sub.c.value_gbp), 0)).select_from(sub)).one()
    rows = db.scalars(ordered(base(q), q).limit(limit).offset(offset)).all()
    return list(rows), int(total), float(value)


def facets(db: Session, q: OrderQuery) -> dict[str, dict[str, int]]:
    """{dimension: {option: count}} - each dimension counted with every
    other filter applied but its own cleared."""
    out: dict[str, dict[str, int]] = {}

    def grouped(dim: str, col, *clear: str):
        stmt = base(q.without(*clear), col, func.count(func.distinct(SalesOrder.id))).group_by(col)
        out[dim] = {str(k): n for k, n in db.execute(stmt) if k is not None}

    grouped("status", SalesOrder.status, "statuses")
    grouped("year", SalesEdition.year, "years")
    grouped("title", SalesEdition.title_id, "title_ids")
    line = select(SalesTitle.product_line).where(SalesTitle.id == SalesEdition.title_id).scalar_subquery()
    grouped("product_line", line, "product_lines")
    grouped("xero", xero_state(), "xero")

    # A booking counts for every rep it credits, not only its main rep.
    ids = base(q.without("rep_ids"), SalesOrder.id).subquery()
    pairs = union_all(
        select(SalesOrder.id.label("oid"), SalesOrder.rep_id.label("rid")).where(SalesOrder.id.in_(select(ids.c.id)), SalesOrder.rep_id.isnot(None)),
        select(SalesOrderCredit.order_id, SalesOrderCredit.rep_id).where(SalesOrderCredit.order_id.in_(select(ids.c.id))),
    ).subquery()
    out["rep"] = {str(r): n for r, n in db.execute(
        select(pairs.c.rid, func.count(func.distinct(pairs.c.oid))).group_by(pairs.c.rid))}

    # Yes/no filters: counted by applying each answer, so a count always
    # equals what ticking it would show.
    for attr in ("invoiced", "linked", "has_warning"):
        out[attr] = {}
        for answer in (True, False):
            sub = base(replace(q, **{attr: answer}), SalesOrder.id).subquery()
            out[attr][str(answer).lower()] = db.scalar(select(func.count()).select_from(sub)) or 0
    return out
