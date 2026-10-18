"""Packages still to be allocated - Matt's doc: "often the sales team will sell a package, that isn't always broken
down on the order ... activity may not yet be confirmed as to where it is going."

A booking line can have items marked "to be allocated": sold and priced (they count in the booking's total and on the
confirmation as "dates to be confirmed"), but with no issue yet, so nothing goes on the order register for them and
no issue counts their money until someone picks the issue. app/sales/deals.py keeps the count, value and earliest
"decide by" date on the booking.

This module reminds the salesperson before it matters: once the line's "decide by" date, or the next booking deadline
of that title, is within the lead time, they get one Review Queue item with the booking linked. Choosing the issues
(editing the booking) closes the reminder by itself.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.automations.registry import ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.db.session import SessionLocal
from app.models import Company, ReviewQueueItem, SalesDeal, SalesEdition, SalesRep, SalesTitle

logger = logging.getLogger("app.automations.allocations")

KIND = "allocation_due"
SNOOZE_DAYS = 7


def _money(v) -> str:
    return f"£{float(v or 0):,.2f}"


def _waiting(d: SalesDeal) -> list[tuple[dict, int, float]]:
    """(line, items still to allocate, their value) for each line that has any."""
    from app.sales.deals import is_unallocated

    out = []
    for ln in d.lines or []:
        ps = [p for p in ln.get("placements") or [] if is_unallocated(p)]
        if ps:
            out.append((ln, len(ps), sum(float(p.get("value_gbp") or 0) for p in ps)))
    return out


def _next_deadline(db: Session, title_ids: set, today: date) -> SalesEdition | None:
    """The soonest issue of these titles still taking bookings."""
    if not title_ids:
        return None
    return db.scalars(select(SalesEdition).where(SalesEdition.title_id.in_(title_ids), SalesEdition.ad_deadline.isnot(None),
                                                 SalesEdition.ad_deadline >= today, SalesEdition.status != "closed")
                      .order_by(SalesEdition.ad_deadline)).first()


def _due(db: Session, d: SalesDeal, today: date) -> tuple[date | None, SalesEdition | None]:
    titles = {uuid.UUID(str(ln["title_id"])) for ln, _n, _v in _waiting(d) if ln.get("title_id")}
    nxt = _next_deadline(db, titles, today)
    dates = [x for x in (d.allocate_by, nxt.ad_deadline if nxt else None) if x]
    return (min(dates) if dates else None), nxt


def _payload(db: Session, d: SalesDeal, today: date) -> dict:
    from app.api.routes.sales import edition_label

    due, nxt = _due(db, d, today)
    rep = db.get(SalesRep, d.rep_id) if d.rep_id else None
    company = db.get(Company, d.company_id) if d.company_id else None
    titles = {t.id: t for t in db.scalars(select(SalesTitle))}
    lines, names = [], set()
    for ln, n, v in _waiting(d):
        t = titles.get(uuid.UUID(str(ln["title_id"]))) if ln.get("title_id") else None
        if t:
            names.add(t.name)
        by = f", decide by {date.fromisoformat(str(ln['allocate_by'])[:10]):%-d %b %Y}" if ln.get("allocate_by") else ""
        lines.append(f"{n} × {ln.get('description') or ln.get('size') or 'Item'}{f' - {t.name}' if t else ''} - {_money(v)}{by}")
    details = [
        {"label": "Booking", "value": f"{d.number} ({d.status})", "href": f"/sales/deals/{d.id}"},
        {"label": "Client", "value": company.name if company else d.client_name, **({"href": f"/companies/{company.id}"} if company else {})},
        {"label": "Still to allocate", "value": "\n".join(lines)},
        {"label": "Value not yet in any issue", "value": _money(d.unallocated_gbp)},
    ]
    if d.allocate_by:
        details.append({"label": "Decide by", "value": f"{d.allocate_by:%-d %b %Y}"})
    if nxt:
        details.append({"label": "Next booking deadline", "value": f"{edition_label(titles[nxt.title_id], nxt)}: {nxt.ad_deadline:%-d %b %Y}",
                        "href": f"/sales/editions/{nxt.id}"})
    details.append({"label": "Salesperson", "value": rep.name if rep else "House account"})
    late = bool(due and due < today)
    return {
        "summary": f"Choose the issues for {d.unallocated_count} item{'s' if d.unallocated_count != 1 else ''} on booking {d.number} "
                   f"({d.client_name}, {_money(d.unallocated_gbp)})",
        "details": details,
        "deal_id": str(d.id),
        "related_entities": [{"type": "company", "id": str(company.id), "label": company.name}] if company else [],
        "facets": {"salesperson": rep.name if rep else "House account", "title": ", ".join(sorted(names)) or "No title",
                   "when": "Past the date" if late else "Coming up"},
        "sort_date": due.isoformat() if due else None,
        "owner_user_id": str(rep.user_id) if rep and rep.user_id else None,
        "dedupe_key": f"{KIND}:{d.id}",
    }


def _pending(db: Session, d: SalesDeal) -> list[ReviewQueueItem]:
    return list(db.scalars(select(ReviewQueueItem).where(ReviewQueueItem.kind == KIND, ReviewQueueItem.status == "pending",
                                                         ReviewQueueItem.payload["deal_id"].astext == str(d.id))))


def settle(db: Session, d: SalesDeal) -> None:
    """After a booking is saved: close its reminder once everything is allocated, otherwise keep it up to date."""
    items = _pending(db, d)
    if not items:
        return
    if d.unallocated_count and d.status != "cancelled":
        for it in items:
            it.payload = _payload(db, d, date.today())
        return
    now = datetime.now(timezone.utc)
    for it in items:
        it.status, it.resolved_action, it.reviewed_at = "approved", "allocated", now
        it.review_note = "Every item now has an issue." if d.status != "cancelled" else "The booking was cancelled."


def scan() -> None:
    today = date.today()
    db = SessionLocal()
    try:
        lead = runtime_settings.get_int(db, "orders_allocate_remind_days")
        snoozed = {r[0] for r in db.execute(select(ReviewQueueItem.payload["deal_id"].astext).where(
            ReviewQueueItem.kind == KIND, ReviewQueueItem.resolved_action == "later",
            ReviewQueueItem.reviewed_at >= datetime.now(timezone.utc) - timedelta(days=SNOOZE_DAYS)))}
        queued = 0
        for d in db.scalars(select(SalesDeal).where(SalesDeal.unallocated_count > 0, SalesDeal.status != "cancelled")):
            if str(d.id) in snoozed or _pending(db, d):
                continue
            due, _nxt = _due(db, d, today)
            if not due or (due - today).days > lead:
                continue
            title = next((db.get(SalesTitle, uuid.UUID(str(ln["title_id"]))) for ln, _n, _v in _waiting(d) if ln.get("title_id")), None)
            db.add(ReviewQueueItem(id=uuid.uuid4(), kind=KIND, source_db=title.crm_source_db if title else None, status="pending",
                                   entity_type="company" if d.company_id else None, entity_id=d.company_id, payload=_payload(db, d, today)))
            queued += 1
        db.commit()
        logger.info("allocation reminders: %d queued", queued)
    finally:
        db.close()


def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    d = db.get(SalesDeal, uuid.UUID(item.payload["deal_id"]))
    if action_id == "later":
        return
    if action_id == "done":
        if d and d.unallocated_count and d.status != "cancelled":
            raise ValueError(f"Booking {d.number} still has {d.unallocated_count} item{'s' if d.unallocated_count != 1 else ''} "
                             "with no issue. Open the booking and choose the issues first.")
        return
    raise ValueError(f"Unknown action {action_id!r} for {KIND}")


register(ReviewKind(
    kind=KIND,
    label="Items to allocate",
    description="Bookings with items sold but not yet given an issue, as their 'decide by' date or the title's next booking deadline gets close.",
    actions=[
        ReviewAction(id="done", label="All allocated", style="primary", outcome="approved"),
        ReviewAction(id="later", label="Remind me next week", style="secondary", outcome="snoozed"),
    ],
    handler=_handle,
    audience="sales",
    facets=(("salesperson", "Salesperson"), ("title", "Title"), ("when", "When")),
    date_sort_label="decide-by date",
))

register_job(ScheduledJob(
    id="allocation_reminder_scan",
    label="Items to allocate",
    description="Reminds salespeople about booked items that still have no issue, before the deadline.",
    cron="15 7 * * 1-5",
    func=scan,
    enabled_flag="automations_allocation_reminders_enabled",
))
