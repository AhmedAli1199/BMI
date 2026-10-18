"""The accounts check of an issue's order register once it has gone to press - Matt's doc: Samantha "checks the SOR
weekly or once a mag has gone to press", to "reconcile and cross check what has been booked and should be invoiced",
because "bookings may be missed off the SOR but an order created or vice versa".

A few days after an issue's copy deadline (or its date, for an event or anything without one), accounts get one
Review Queue item for it, listing every item there that's worth a look, each linked:
  - typed straight into the register with no booking behind it (so no confirmation went out);
  - not matching its booking (a different value, or booked on one and pencilled or cancelled on the other);
  - still pencilled, now the issue has gone to press;
  - on a confirmed booking whose confirmation was never sent;
  - packages for this title that are still to be allocated (they may belong in this issue);
and, for information, how many filler ads it carries and how many items are still to invoice.

Nothing is changed here - it only puts the issue in front of a person.
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
from app.models import ReviewQueueItem, SalesDeal, SalesEdition, SalesOrder, SalesTitle

logger = logging.getLogger("app.automations.sor_checks")

KIND = "sor_issue_check"
SNOOZE_DAYS = 7
MAX_ROWS = 40       # rows shown on one card; the rest are counted
LOOK_BACK_DAYS = 45


def _money(v) -> str:
    return f"£{float(v or 0):,.2f}"


def _item_text(o: SalesOrder) -> str:
    what = o.description or o.size or "item"
    return f"{o.client_name} - {what} - {_money(o.value_gbp)}"


def findings(db: Session, ed: SalesEdition) -> dict:
    """Everything worth a look in one issue's order register: {"rows": [detail rows], "problems": n, ...}."""
    from app.sales import deals as dl

    items = list(db.scalars(select(SalesOrder).where(SalesOrder.edition_id == ed.id).order_by(SalesOrder.client_name)))
    live = [o for o in items if o.status in ("booked", "pencilled")]
    deals = {d.id: d for d in db.scalars(select(SalesDeal).where(SalesDeal.id.in_({o.deal_id for o in items if o.deal_id})))} if items else {}
    values: dict[str, float] = {}
    for d in deals.values():
        try:
            for ln in dl.price_deal(d).lines:
                for p in ln["placements"]:
                    if p.get("order_id"):
                        values[str(p["order_id"])] = float(p.get("value_gbp") or 0)
        except dl.OrderError:
            continue
    rows: list[dict] = []
    problems = 0

    def add(label: str, value: str, href: str) -> None:
        nonlocal problems
        problems += 1
        if len(rows) < MAX_ROWS:
            rows.append({"label": label, "value": value, "href": href})

    for o in live:
        if not o.deal_id and not o.source_file:
            add("No booking behind it", f"{_item_text(o)}. It was added to the register directly, so no confirmation went out.",
                f"/sales/orders/{o.id}")
    for o in items:
        d = deals.get(o.deal_id) if o.deal_id else None
        if not d:
            continue
        want = dl.ITEM_STATUS[d.status]
        if o.status in ("booked", "pencilled", "cancelled") and o.status != want and not (o.status == "cancelled" and want == "booked"):
            add("Doesn't match its booking", f"{_item_text(o)}: {o.status} here, but booking {d.number} is {d.status}.", f"/sales/deals/{d.id}")
        elif str(o.id) in values and abs(values[str(o.id)] - float(o.value_gbp or 0)) > 0.005:
            add("Doesn't match its booking", f"{_item_text(o)}, but booking {d.number} has it at {_money(values[str(o.id)])}.", f"/sales/deals/{d.id}")
    for o in live:
        if o.status == "pencilled":
            add("Still pencilled", f"{_item_text(o)}. Confirm it or let the space go.", f"/sales/deals/{o.deal_id}" if o.deal_id else f"/sales/orders/{o.id}")
    for d in sorted({deals[o.deal_id] for o in live if o.deal_id in deals and deals[o.deal_id].status == "confirmed"
                     and not deals[o.deal_id].sent_at}, key=lambda x: x.number):
        add("Confirmation not sent", f"Booking {d.number} for {d.client_name} is confirmed, but its confirmation was never sent.", f"/sales/deals/{d.id}")
    for d in db.scalars(select(SalesDeal).where(SalesDeal.unallocated_count > 0, SalesDeal.status != "cancelled").order_by(SalesDeal.number)):
        n = sum(1 for ln in d.lines or [] if str(ln.get("title_id")) == str(ed.title_id)
                for p in ln.get("placements") or [] if dl.is_unallocated(p))
        if n:
            add("Package still to allocate", f"Booking {d.number} for {d.client_name} has {n} item{'s' if n != 1 else ''} for this title "
                "with no issue yet - should any be in this one?", f"/sales/deals/{d.id}")
    fillers = [o for o in live if o.filler]
    uninvoiced = [o for o in live if o.status == "booked" and float(o.value_gbp or 0) > 0 and not o.invoice_number]
    booked = sum(float(o.value_gbp or 0) for o in live if o.status == "booked")
    return {"rows": rows, "problems": problems, "fillers": len(fillers),
            "filler_pages": round(sum(float(o.pages or 0) for o in fillers), 2), "uninvoiced": len(uninvoiced),
            "items": len(live), "booked_gbp": booked}


def _payload(db: Session, ed: SalesEdition, title: SalesTitle) -> dict:
    from app.api.routes.sales import edition_label

    label = edition_label(title, ed)
    f = findings(db, ed)
    head = [
        {"label": "Issue", "value": f"{label} ({f['items']} item{'s' if f['items'] != 1 else ''}, {_money(f['booked_gbp'])} booked)", "href": f"/sales/editions/{ed.id}"},
    ]
    if f["uninvoiced"]:
        head.append({"label": "Still to invoice", "value": f"{f['uninvoiced']} item{'s' if f['uninvoiced'] != 1 else ''}",
                     "href": f"/sales/editions/{ed.id}?invoiced=false"})
    if f["fillers"]:
        head.append({"label": "Filler ads", "value": f"{f['fillers']} ({f['filler_pages']:g} pages)",
                     "href": f"/sales/editions/{ed.id}?filler=true"})
    more = f["problems"] - len(f["rows"])
    tail = [{"label": "And more", "value": f"{more} more - open the issue to see them all.", "href": f"/sales/editions/{ed.id}"}] if more > 0 else []
    when = ed.copy_deadline or ed.edition_date
    summary = (f"Check the order register for {label}: {f['problems']} thing{'s' if f['problems'] != 1 else ''} to look at"
               if f["problems"] else f"Check the order register for {label}: nothing looks out of place")
    return {
        "summary": summary,
        "details": head + f["rows"] + tail,
        "edition_id": str(ed.id),
        "facets": {"title": title.name, "state": "Needs a look" if f["problems"] else "Nothing out of place"},
        "sort_date": (ed.edition_date or when).isoformat() if (ed.edition_date or when) else None,
        "owner_user_id": None,
        "dedupe_key": f"{KIND}:{ed.id}",
    }


def _gone_to_press(ed: SalesEdition) -> date | None:
    return ed.copy_deadline or ed.edition_date


def scan() -> None:
    today = date.today()
    db = SessionLocal()
    try:
        after = runtime_settings.get_int(db, "sor_issue_check_after_days")
        history: dict[str, list[tuple[str, str | None, datetime | None]]] = {}
        for eid, status, action, at in db.execute(select(ReviewQueueItem.payload["edition_id"].astext, ReviewQueueItem.status,
                                                         ReviewQueueItem.resolved_action, ReviewQueueItem.reviewed_at)
                                                  .where(ReviewQueueItem.kind == KIND)):
            history.setdefault(eid, []).append((status, action, at))
        titles = {t.id: t for t in db.scalars(select(SalesTitle))}
        has_items = select(SalesOrder.edition_id).where(SalesOrder.status.in_(("booked", "pencilled"))).distinct()
        eds = db.scalars(select(SalesEdition).where(SalesEdition.id.in_(has_items)))
        queued = 0
        snooze_from = datetime.now(timezone.utc) - timedelta(days=SNOOZE_DAYS)
        for ed in eds:
            pressed = _gone_to_press(ed)
            if not pressed or not (today - timedelta(days=LOOK_BACK_DAYS) <= pressed <= today - timedelta(days=after)):
                continue
            past = history.get(str(ed.id), [])
            # Once per issue; "Look again later" brings it back after a week.
            if any(s == "pending" or a != "later" or (at and at >= snooze_from) for s, a, at in past):
                continue
            title = titles[ed.title_id]
            db.add(ReviewQueueItem(id=uuid.uuid4(), kind=KIND, source_db=title.crm_source_db, status="pending", payload=_payload(db, ed, title)))
            queued += 1
        db.commit()
        logger.info("order register issue checks: %d queued", queued)
    finally:
        db.close()


def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    from app.sales.accounts import can_approve

    actor = input_data.get("_actor_user_id")
    if not can_approve(db, uuid.UUID(actor) if actor else None):
        raise ValueError("Only accounts can sign off the order register check.")
    if action_id in ("done", "later"):
        return
    raise ValueError(f"Unknown action {action_id!r} for {KIND}")


register(ReviewKind(
    kind=KIND,
    label="Issue gone to press",
    description="Once an issue has gone to press: anything in its order register worth a look before invoicing - items with no booking, "
                "items that don't match their booking, pencilled items, unsent confirmations and packages still to allocate.",
    actions=[
        ReviewAction(id="done", label="All checked", style="primary", outcome="approved"),
        ReviewAction(id="later", label="Look again next week", style="secondary", outcome="snoozed"),
    ],
    handler=_handle,
    audience="admin",
    approver="accounts",
    facets=(("title", "Title"), ("state", "What it found")),
    date_sort_label="issue date",
))

register_job(ScheduledJob(
    id="sor_issue_check_scan",
    label="Issue gone to press check",
    description="Puts each issue's order register in front of accounts a few days after its copy deadline.",
    cron="45 6 * * 1-5",
    func=scan,
    enabled_flag="automations_sor_issue_check_enabled",
))
