"""Ready to invoice (15 Oct call): when booked items reach the date they should be invoiced - from the booking's
"when to invoice" (app/sales/invoicing.py) or a date accounts set themselves - accounts get one card per booking
listing what's due. Nothing is invoiced automatically: the card says what to raise, with everything needed for it,
and records what accounts did ("Invoiced", "Remind me on…", "No invoice needed").

One card per booking at a time; it's refreshed whenever the booking or its dates change, and closes itself when
nothing on it is due any more (invoiced in Xero and matched, moved to a later date, cancelled).
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.automations.registry import ExtraField, ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.db.session import SessionLocal
from app.models import ReviewQueueItem, SalesDeal, SalesEdition, SalesOrder, SalesRep, SalesTitle
from app.sales import invoicing as inv

logger = logging.getLogger("app.automations.invoice_due")
KIND = "invoice_due"


def _money(v) -> str:
    return f"£{float(v or 0):,.2f}"


def due_items(db: Session, d: SalesDeal, today: date | None = None) -> list[tuple[SalesOrder, SalesEdition, date]]:
    """Booked, paid-for items on this booking that aren't invoiced and are due by today."""
    today = today or date.today()
    if d.status != "confirmed":
        return []
    out = []
    rows = db.execute(select(SalesOrder, SalesEdition).join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
                      .where(SalesOrder.deal_id == d.id, SalesOrder.status == "booked", SalesOrder.invoice_number.is_(None),
                             SalesOrder.xero_invoice_id.is_(None), SalesOrder.value_gbp > 0, SalesOrder.added_value.is_(False))).all()
    for o, ed in rows:
        if "No invoice needed" in (o.invoice_note or ""):
            continue
        due = inv.due_date(db, d, o.item_date or ed.edition_date, o.invoice_due_on, today)
        if due is not None and due <= today:
            out.append((o, ed, due))
    return sorted(out, key=lambda x: (x[2], x[1].edition_date or date.max))


def _payload(db: Session, d: SalesDeal, rows: list[tuple[SalesOrder, SalesEdition, date]]) -> dict:
    from app.api.routes.sales import edition_label

    titles = {t.id: t for t in db.scalars(select(SalesTitle))}
    rep = db.get(SalesRep, d.rep_id) if d.rep_id else None
    total = sum(float(o.value_gbp or 0) for o, _, _ in rows)
    lines = []
    for o, ed, due in rows:
        runs = o.item_date or ed.edition_date
        lines.append(f"{o.description or o.size or 'Item'} - {edition_label(titles[ed.title_id], ed)}"
                     f"{f' (runs {runs:%-d %b %Y})' if runs else ''} - {_money(o.value_gbp)}")
    when = inv.PLANS.get(d.invoice_plan or "asap", d.invoice_plan)
    if d.invoice_plan == "on_date" and d.invoice_on:
        when = f"On {d.invoice_on:%-d %b %Y} (agreed with the client)"
    if any(o.invoice_due_on for o, _, _ in rows):
        when += " · a date set by accounts"
    details = [
        {"label": "Booking", "value": f"{d.number} - {d.client_name}", "href": f"/sales/deals/{d.id}"},
        {"label": "Due to invoice", "value": "\n".join(lines)},
        {"label": "Total before VAT", "value": _money(total)},
        {"label": "When to invoice", "value": when},
    ]
    if d.invoice_instructions:
        details.append({"label": "Invoice instructions", "value": d.invoice_instructions})
    details.append({"label": "Invoice to", "value": " · ".join(x for x in (d.invoice_to or d.client_name, d.invoice_email) if x)})
    if d.po_number:
        details.append({"label": "PO number", "value": d.po_number})
    else:
        details.append({"label": "PO number", "value": "None on the booking yet"})
    if d.agency_name:
        details.append({"label": "Agency", "value": f"{d.agency_name} ({float(d.agency_pct or 0):.0%} commission)"})
    if d.invoice_currency and d.invoice_currency != "GBP":
        details.append({"label": "Invoice in", "value": d.invoice_currency})
    if d.company_id:
        details.append({"label": "Client in the CRM", "value": d.client_name, "href": f"/companies/{d.company_id}"})
    details.append({"label": "Salesperson", "value": rep.name if rep else "House account"})
    title_names = sorted({titles[ed.title_id].name for _, ed, _ in rows})
    first_due = rows[0][2]
    return {
        "summary": f"Ready to invoice: {d.client_name}, booking {d.number} ({_money(total)})",
        "details": details,
        "deal_id": str(d.id),
        "order_ids": [str(o.id) for o, _, _ in rows],
        "related_entities": [{"type": "company", "id": str(d.company_id), "label": d.client_name}] if d.company_id else [],
        "facets": {"salesperson": rep.name if rep else "House account", "title": ", ".join(title_names),
                   "when": inv.PLANS.get(d.invoice_plan or "asap", d.invoice_plan),
                   "overdue": "Overdue a week or more" if (date.today() - first_due).days >= 7 else "Due now"},
        "sort_date": first_due.isoformat(),
        "dedupe_key": f"{KIND}:{d.id}",
    }


def _pending(db: Session, d: SalesDeal) -> ReviewQueueItem | None:
    return db.scalars(select(ReviewQueueItem).where(ReviewQueueItem.kind == KIND, ReviewQueueItem.status == "pending",
                                                    ReviewQueueItem.payload["deal_id"].astext == str(d.id))).first()


def refresh(db: Session, d: SalesDeal, notify: bool = True) -> ReviewQueueItem | None:
    """Bring this booking's card up to date: create it, update it, or close it."""
    if not runtime_settings.get_bool(db, "automations_invoice_reminders_enabled"):
        return None
    rows = due_items(db, d)
    item = _pending(db, d)
    if not rows:
        if item:
            item.status, item.resolved_action, item.reviewed_at = "approved", "nothing_due", datetime.now(timezone.utc)
            item.review_note = "Nothing on this booking is due to invoice any more."
        return None
    payload = _payload(db, d, rows)
    if item:
        item.payload = payload
        return item
    title_id = rows[0][1].title_id
    title = db.get(SalesTitle, title_id)
    item = ReviewQueueItem(id=uuid.uuid4(), kind=KIND, source_db=title.crm_source_db if title else None, status="pending",
                           entity_type="company" if d.company_id else None, entity_id=d.company_id, payload=payload)
    db.add(item)
    if notify:
        from app.sales.accounts import tell_accounts
        tell_accounts(db, KIND, f"Ready to invoice: {d.client_name}", payload["summary"], f"/automations/review?kind={KIND}")
    return item


def _items(db: Session, item: ReviewQueueItem) -> list[SalesOrder]:
    ids = [uuid.UUID(x) for x in item.payload.get("order_ids") or []]
    return db.scalars(select(SalesOrder).where(SalesOrder.id.in_(ids))).all() if ids else []


def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    d = db.get(SalesDeal, uuid.UUID(item.payload["deal_id"]))
    if not d:
        raise ValueError("This booking no longer exists.")
    actor = input_data.get("_actor_user_id")
    from app.sales.accounts import can_approve
    if not can_approve(db, uuid.UUID(actor) if actor else None):
        raise ValueError("Only accounts can record invoicing.")
    items = _items(db, item)
    if action_id == "invoiced":
        number = (input_data.get("invoice_number") or "").strip()
        if not number:
            raise ValueError("Enter the invoice number from Xero.")
        for o in items:
            if not o.invoice_number:
                o.invoice_number, o.invoice_value_gbp, o.invoiced_on = number[:60], o.value_gbp, date.today()
        return
    if action_id == "remind":
        raw = (input_data.get("remind_on") or "").strip()
        try:
            when = date.fromisoformat(raw)
        except ValueError as e:
            raise ValueError("Choose the date to be reminded on.") from e
        if when <= date.today():
            raise ValueError("Choose a date after today.")
        for o in items:
            o.invoice_due_on = when
        return
    if action_id == "week":
        for o in items:
            o.invoice_due_on = date.today() + timedelta(days=7)
        return
    if action_id == "no_invoice":
        note = (input_data.get("note") or "").strip()
        for o in items:
            o.invoice_note = "; ".join(filter(None, [o.invoice_note, f"No invoice needed: {note}" if note else "No invoice needed"]))
        return
    raise ValueError(f"Unknown action {action_id!r} for {KIND}")


register(ReviewKind(
    kind=KIND,
    label="Ready to invoice",
    description="Booked items that have reached the date they should be invoiced (from the booking's \"when to invoice\", or a date accounts set). Make the draft invoice in Xero in one click, record one you made yourself, or choose a later date.",
    actions=[
        ReviewAction(id="invoiced", label="Already invoiced in Xero", style="secondary", outcome="approved", extra_fields=[
            ExtraField(key="invoice_number", label="Invoice number from Xero", placeholder="INV-3050"),
        ]),
        ReviewAction(id="remind", label="Remind me on…", style="secondary", outcome="rejected", extra_fields=[
            ExtraField(key="remind_on", label="Remind me on", field_type="date"),
        ]),
        ReviewAction(id="week", label="Not yet - next week", style="secondary", outcome="rejected"),
        ReviewAction(id="no_invoice", label="No invoice needed", style="secondary", outcome="rejected", requires_note=True),
    ],
    handler=_handle,
    audience="admin",
    approver="accounts",
    facets=(("salesperson", "Salesperson"), ("title", "Title"), ("when", "When to invoice"), ("overdue", "Due")),
    date_sort_label="due date",
))


def scan() -> None:
    db = SessionLocal()
    try:
        if not runtime_settings.get_bool(db, "automations_invoice_reminders_enabled"):
            return
        made = 0
        for d in db.scalars(select(SalesDeal).where(SalesDeal.status == "confirmed")):
            had = _pending(db, d)
            if refresh(db, d) is not None and had is None:
                made += 1
        db.commit()
        logger.info("invoice reminders: %d new card(s)", made)
    finally:
        db.close()


register_job(ScheduledJob(
    id="invoice_due_scan",
    label="Ready to invoice",
    description="Each morning: tells accounts which booked items have reached their invoice date.",
    cron="5 7 * * 1-5",
    func=scan,
    enabled_flag="automations_invoice_reminders_enabled",
))
