"""When each booked item should be invoiced (15 Oct call with Matt, Clare and Samantha).

The salesperson records what was agreed with the client on the booking (`SalesDeal.invoice_plan`):
  asap            invoice as soon as allowed: now if it publishes this quarter, else the first day of the quarter
                  it publishes in (BMI invoices in the same quarter as publication, for VAT). The default.
  on_publication  the day it publishes / the event happens
  after_run       a few days after it has run (tear sheet or link sent first) - setting `invoice_after_run_days`
  on_date         a date agreed with the client (`SalesDeal.invoice_on`)
  next_quarter    the first day of the quarter after the one it publishes in
  next_year       the first day of the financial year after the one it publishes in

Accounts can set their own date on any item ("remind me on", `SalesOrder.invoice_due_on`), which wins. Everything
else follows the issue's date, so when an issue moves in the editorial plan, the reminders move with it.
Quarters follow BMI's financial year (setting `sales_financial_year_start_month`, July).
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.automations import runtime_settings

PLANS = {
    "asap": "As soon as allowed (same quarter as it runs)",
    "on_publication": "When it runs",
    "after_run": "After it has run (tear sheet or link first)",
    "on_date": "On a date agreed with the client",
    "next_quarter": "The quarter after it runs",
    "next_year": "The financial year after it runs",
}


def fy_start_month(db: Session) -> int:
    return min(12, max(1, runtime_settings.get_int(db, "sales_financial_year_start_month") or 7))


def quarter_start(d: date, start_month: int) -> date:
    """First day of the (financial) quarter containing d."""
    offset = (d.month - start_month) % 3
    m = d.month - offset
    y = d.year
    if m < 1:
        m += 12
        y -= 1
    return date(y, m, 1)


def add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    return date(d.year + m // 12, m % 12 + 1, 1)


def year_start(d: date, start_month: int) -> date:
    y = d.year if d.month >= start_month else d.year - 1
    return date(y, start_month, 1)


def plan_date(plan: str, runs: date | None, agreed: date | None, today: date, start_month: int, after_days: int) -> date | None:
    """The date an item becomes due for invoicing under a plan, or None when it can't be worked out yet
    (no date for the issue, or no agreed date)."""
    if plan == "on_date":
        return agreed
    if runs is None:
        return today if plan == "asap" else None
    if plan == "on_publication":
        return runs
    if plan == "after_run":
        return runs + timedelta(days=after_days)
    if plan == "next_quarter":
        return add_months(quarter_start(runs, start_month), 3)
    if plan == "next_year":
        return add_months(year_start(runs, start_month), 12)
    # asap
    q = quarter_start(runs, start_month)
    return today if q <= today else q


def due_date(db: Session, deal, runs: date | None, override: date | None, today: date | None = None) -> date | None:
    if override:
        return override
    today = today or date.today()
    return plan_date(deal.invoice_plan or "asap", runs, deal.invoice_on, today, fy_start_month(db),
                     runtime_settings.get_int(db, "invoice_after_run_days"))


def quarter_warning(db: Session, deal, runs_dates: list[date]) -> str | None:
    """A set date in an earlier quarter than the item runs: allowed (clients sometimes ask), but worth knowing."""
    if deal.invoice_plan != "on_date" or not deal.invoice_on or not runs_dates:
        return None
    sm = fy_start_month(db)
    first = min(runs_dates)
    if quarter_start(deal.invoice_on, sm) < quarter_start(first, sm):
        return (f"Invoicing on {deal.invoice_on:%-d %b %Y} is a quarter before the first item runs ({first:%-d %b %Y}). "
                "That's fine if the client asked for it.")
    return None
