"""The figures the assistant can quote, each defined once, the same way the Sales Orders screens work them out
(the overview, editions and All items). The model never adds numbers up itself: it asks for a measure, a period
and a grouping, and gets back totals worked out here, with a plain definition and a link to the screen that
shows the same figure (the "semantic layer" idea in docs/ai-hub-plan.md).

Rules (matching app/api/routes/sales.py overview):
- Only items with status "booked" count; pencilled, cancelled and moved items don't.
- A year is the reporting year the edition belongs to: a calendar year goes by the edition's year, a financial
  year (BMI's starts 1 July, named by the year it starts in) by the edition's date.
- booked = value of the items (before VAT, after discounts); invoiced = the invoiced value of items with an
  invoice number; awaiting invoice = booked items with a value and no invoice number yet.
- By salesperson uses each person's share of split bookings, like the overview.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Company, SalesEdition, SalesOrder, SalesOrderCredit, SalesRep, SalesTitle
from app.sales.analytics import BOOKED, edition_date_expr, period_bounds, period_label, period_year_of

MEASURES = {
    "booked": "Booked: the value of booked items (before VAT, after discounts); pencilled, cancelled and moved items don't count.",
    "invoiced": "Invoiced: the invoiced value of booked items that have an invoice number.",
    "awaiting_invoice": "Awaiting invoice: booked items with a value and no invoice number yet.",
    "items": "Items: how many booked items (one per advert, sponsored piece or listing per edition).",
    "advertisers": "Advertisers: how many different clients have booked items.",
}
GROUPS = ("none", "title", "salesperson", "month", "client", "edition", "product_line")


class MetricError(ValueError):
    pass


def year_basis(db: Session, basis: str | None) -> tuple[bool, int]:
    from app.automations import runtime_settings
    start_month = min(12, max(1, runtime_settings.get_int(db, "sales_financial_year_start_month") or 7))
    financial = basis == "financial" if basis in ("calendar", "financial") else runtime_settings.get_bool(db, "sales_use_financial_year")
    return financial and start_month != 1, start_month


def _in_period(year: int, financial: bool, start_month: int):
    if not financial:
        return SalesEdition.year == year
    lo, hi = period_bounds(year, True, start_month)
    return edition_date_expr().between(lo, hi)


def _match_titles(db: Session, title: str | None) -> list[SalesTitle]:
    if not title:
        return []
    t = title.strip().lower()
    rows = db.scalars(select(SalesTitle)).all()
    hits = [x for x in rows if x.slug == t or x.name.lower() == t] or [x for x in rows if t in x.name.lower() or t in x.slug]
    if not hits:
        raise MetricError(f"There's no title called {title!r}. Titles: " + ", ".join(sorted(x.name for x in rows)))
    return hits


def _match_rep(db: Session, rep: str | None) -> SalesRep | None:
    if not rep:
        return None
    r = rep.strip().lower()
    rows = db.scalars(select(SalesRep)).all()
    hits = [x for x in rows if x.code.lower() == r or x.name.lower() == r] or [x for x in rows if r in x.name.lower()]
    if len(hits) != 1:
        raise MetricError(f"Which salesperson? {'Several match' if hits else 'None match'} {rep!r}: "
                          + ", ".join(f"{x.name} ({x.code})" for x in (hits or rows)))
    return hits[0]


def compute(db: Session, *, measure: str = "booked", group_by: str = "none", year: int | None = None, basis: str | None = None,
            title: str | None = None, salesperson: str | None = None, client: str | None = None, product_line: str | None = None,
            compare_last_year: bool = False, top: int = 15, today: date | None = None) -> dict:
    if measure not in MEASURES:
        raise MetricError("Measure must be one of: " + ", ".join(MEASURES))
    if group_by not in GROUPS:
        raise MetricError("Group by must be one of: " + ", ".join(GROUPS))
    today = today or date.today()
    financial, start_month = year_basis(db, basis)
    year = year or period_year_of(today, financial, start_month)
    titles = _match_titles(db, title)
    rep = _match_rep(db, salesperson)

    def run(y: int) -> tuple[float, list[tuple[str, float]]]:
        by_rep = group_by == "salesperson" or rep is not None
        if by_rep:   # each person's share of split bookings, so nothing is counted twice
            amount = (SalesOrderCredit.amount_gbp * func.coalesce(SalesOrder.invoice_value_gbp, 0) / func.nullif(SalesOrder.value_gbp, 0)
                      if measure == "invoiced" else SalesOrderCredit.amount_gbp)
        else:
            amount = SalesOrder.invoice_value_gbp if measure == "invoiced" else SalesOrder.value_gbp
        if measure == "items":
            agg = func.count(func.distinct(SalesOrder.id))
        elif measure == "advertisers":
            agg = func.count(func.distinct(func.lower(func.coalesce(Company.name, SalesOrder.client_name))))
        else:
            agg = func.coalesce(func.sum(amount), 0)
        key = {
            "none": None, "title": SalesTitle.name, "salesperson": SalesRep.name, "client": func.coalesce(Company.name, SalesOrder.client_name),
            "edition": SalesTitle.name + " · " + SalesEdition.name, "product_line": SalesTitle.product_line,
            "month": func.to_char(edition_date_expr(), "YYYY-MM"),
        }[group_by]
        stmt = (select(*( [key] if key is not None else []), agg).select_from(SalesOrder)
                .join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
                .join(SalesTitle, SalesEdition.title_id == SalesTitle.id)
                .outerjoin(Company, Company.id == SalesOrder.company_id)
                .where(SalesOrder.status == BOOKED, _in_period(y, financial, start_month)))
        if by_rep:
            stmt = stmt.join(SalesOrderCredit, SalesOrderCredit.order_id == SalesOrder.id).join(SalesRep, SalesRep.id == SalesOrderCredit.rep_id)
            if rep:
                stmt = stmt.where(SalesOrderCredit.rep_id == rep.id)
        if measure == "invoiced":
            stmt = stmt.where(SalesOrder.invoice_number.isnot(None))
        if measure == "awaiting_invoice":
            stmt = stmt.where(SalesOrder.invoice_number.is_(None), SalesOrder.value_gbp > 0)
        if titles:
            stmt = stmt.where(SalesEdition.title_id.in_([t.id for t in titles]))
        if product_line:
            stmt = stmt.where(SalesTitle.product_line == product_line)
        if client:
            like = f"%{client.strip()}%"
            stmt = stmt.where(or_(SalesOrder.client_name.ilike(like), Company.name.ilike(like)))
        if key is None:
            return float(db.scalar(stmt) or 0), []
        rows = [(str(k or "Not set"), float(v or 0)) for k, v in db.execute(stmt.group_by(key)).all()]
        rows.sort(key=(lambda r: r[0]) if group_by == "month" else (lambda r: (-r[1], r[0])))
        return round(sum(v for _, v in rows), 2), rows

    total, rows = run(year)
    money = measure not in ("items", "advertisers")
    out = {
        "measure": measure, "definition": MEASURES[measure],
        "period": period_label(year, financial, start_month) + (" (financial year)" if financial else " (calendar year)"),
        "filters": {k: v for k, v in {"title": ", ".join(t.name for t in titles) or None, "salesperson": rep.name if rep else None,
                                      "client": client, "product_line": product_line}.items() if v},
        "total": round(total, 2), "unit": "GBP" if money else "count",
        "rows": [{"name": k, "value": round(v, 2)} for k, v in rows[:top]], "more_rows": max(0, len(rows) - top),
        "where_to_see_it": "/sales" if group_by in ("none", "title", "salesperson", "month") else "/sales/bookings",
    }
    if year == period_year_of(today, financial, start_month):
        out["note"] = "This year isn't over yet: the total so far, including items booked for later in the year."
    if compare_last_year:
        last_total, last_rows = run(year - 1)
        out["last_year"] = {"period": period_label(year - 1, financial, start_month), "total": round(last_total, 2),
                            "rows": {k: round(v, 2) for k, v in last_rows[:top]}}
    return out

