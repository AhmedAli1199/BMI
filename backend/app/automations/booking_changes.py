"""Changes to a checked booking go to accounts (Matt, 14 Oct: only Samantha should make or approve changes).

Once accounts has checked a booking (and someone has the Accounts permission - app/sales/accounts.py),
salespeople can't edit or cancel it directly. "Request a change" stores the whole booking as they'd like it
(or "cancel it") with their reason; accounts gets one card showing what changes - before and after - and the
knock-on effects: which issues it moves between, and whether anything affected has already been invoiced
(which then needs a credit note and a new invoice). "Approve" applies it exactly as asked and keeps the
booking checked; "Decline" sends accounts' note back. One request per booking at a time - a new one replaces it.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automations.registry import ReviewAction, ReviewKind, register
from app.models import ReviewQueueItem, SalesDeal, SalesEdition, SalesOrder, SalesRep, SalesTitle, User
from app.services.notify import create_notification

KIND = "booking_change"
LABELS = {"client_name": "Client", "contact_name": "Contact", "contact_email": "Contact email", "confirmation_address": "Confirmation address",
          "invoice_to": "Invoice to", "invoice_email": "Invoice email", "po_number": "PO number", "agency_name": "Agency",
          "agency_pct": "Agency commission", "discount_pct": "Discount", "package_price_gbp": "Package price", "invoice_plan": "When to invoice"}


def _money(v) -> str:
    return f"£{float(v or 0):,.2f}"


def _norm(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)) or hasattr(v, "as_tuple"):
        return round(float(v), 4)
    return str(v)


def _issue_names(db: Session, line: dict) -> list[str]:
    from app.api.routes.sales import edition_label
    out = []
    for p in line.get("placements") or []:
        if not p.get("edition_id"):
            continue
        e = db.get(SalesEdition, uuid.UUID(str(p["edition_id"])))
        t = db.get(SalesTitle, e.title_id) if e else None
        if e and t:
            out.append(edition_label(t, e))
    return out


def _line_text(db: Session, ln: dict) -> str:
    what = ln.get("description") or ln.get("size") or "Item"
    where = ", ".join(_issue_names(db, ln)) or "no issue chosen"
    price = ln.get("total_gbp")
    if price is None:
        price = float(ln.get("unit_price") or 0) * float(ln.get("qty") or 1)
    return f"{what} - {where} - {_money(price)}"


def describe(db: Session, d: SalesDeal, proposed: dict | None, cancel: bool) -> tuple[list[dict], list[str]]:
    """(card details, knock-on warnings) for a requested change."""
    from app.sales import deals as dl
    details: list[dict] = []
    knock: list[str] = []
    items = db.scalars(select(SalesOrder).where(SalesOrder.deal_id == d.id)).all()
    invoiced = [o for o in items if o.invoice_number and o.status != "cancelled"]
    if cancel:
        details.append({"label": "Change", "value": "Cancel the whole booking"})
        for o in invoiced:
            knock.append(f"{o.description or 'An item'} was already invoiced ({o.invoice_number}, {_money(o.value_gbp)}) - it stays booked unless you credit it.")
        return details, knock
    try:
        from app.api.routes.deals import FIELDS, DealIn, _lines_in
        p = DealIn(**proposed)
        tmp = SalesDeal(id=uuid.uuid4(), lines=[], split=[], **{k: getattr(p, k) for k in FIELDS})
        priced = dl.price_deal(tmp, _lines_in(p))
        new_total, priced_lines = priced.total_gbp, priced.lines
    except Exception:
        new_total, priced_lines = None, proposed.get("lines") or []
    for k, label in LABELS.items():
        old, new = _norm(getattr(d, k, None)), _norm(proposed.get(k))
        if old != new:
            details.append({"label": label, "value": f"{old or '—'}  →  {new or '—'}"})
    before = {ln.get("key") or str(i): ln for i, ln in enumerate(d.lines or [])}
    after_lines = priced_lines
    after = {ln.get("key") or f"new{i}": ln for i, ln in enumerate(after_lines)}
    for key, ln in before.items():
        if key not in after:
            details.append({"label": "Item removed", "value": _line_text(db, ln)})
    for key, ln in after.items():
        old = before.get(key)
        if not old:
            details.append({"label": "Item added", "value": _line_text(db, ln)})
        elif _line_text(db, old) != _line_text(db, ln):
            details.append({"label": "Item changed", "value": f"{_line_text(db, old)}\n→ {_line_text(db, ln)}"})
    old_issues = {n for ln in d.lines or [] for n in _issue_names(db, ln)}
    new_issues = {n for ln in after_lines for n in _issue_names(db, ln)}
    if old_issues != new_issues:
        if old_issues - new_issues:
            knock.append("Leaves " + ", ".join(sorted(old_issues - new_issues)) + " - those issues' figures drop.")
        if new_issues - old_issues:
            knock.append("Moves into " + ", ".join(sorted(new_issues - old_issues)) + " - check there's still space and the deadline.")
    for o in invoiced:
        line = next((ln for ln in d.lines or [] if any(str(p.get("order_id")) == str(o.id) for p in ln.get("placements") or [])), None)
        new_line = after.get(line.get("key")) if line else None
        if not new_line or _line_text(db, line) != _line_text(db, new_line):
            knock.append(f"{o.description or 'An item'} is already invoiced ({o.invoice_number}, {_money(o.value_gbp)}) - it will need a credit note and a new invoice.")
    if new_total is not None and round(new_total, 2) != round(float(d.total_gbp or 0), 2):
        details.append({"label": "Total before VAT", "value": f"{_money(d.total_gbp)}  →  {_money(new_total)}"})
    if not details:
        details.append({"label": "Change", "value": "Small details only (notes or instructions)"})
    return details, knock


def pending(db: Session, d: SalesDeal) -> ReviewQueueItem | None:
    return db.scalars(select(ReviewQueueItem).where(ReviewQueueItem.kind == KIND, ReviewQueueItem.status == "pending",
                                                    ReviewQueueItem.payload["deal_id"].astext == str(d.id))).first()


def request(db: Session, d: SalesDeal, *, proposed: dict | None, cancel: bool, cancel_reason: str | None, keep_run: bool,
            reason: str, user_id: uuid.UUID | None) -> ReviewQueueItem:
    now = datetime.now(timezone.utc)
    old = pending(db, d)
    if old:   # one request per booking at a time: the newest wins
        old.status, old.resolved_action, old.reviewed_at, old.review_note = "rejected", "withdrawn", now, "Replaced by a newer change request."
    who = db.get(User, user_id) if user_id else None
    rep = db.get(SalesRep, d.rep_id) if d.rep_id else None
    details, knock = describe(db, d, proposed, cancel)
    head = [{"label": "Booking", "value": f"{d.number} - {d.client_name} ({_money(d.total_gbp)})", "href": f"/sales/deals/{d.id}"},
            {"label": "Asked by", "value": f"{who.name if who else 'Someone'}: “{reason}”"}]
    if knock:
        details.append({"label": "Knock-on", "value": "\n".join(knock)})
    item = ReviewQueueItem(
        id=uuid.uuid4(), kind=KIND, status="pending", entity_type="company" if d.company_id else None, entity_id=d.company_id,
        payload={
            "summary": f"{'Cancel' if cancel else 'Change'} booking {d.number} for {d.client_name}" + (" - already invoiced items affected" if any("invoiced" in k for k in knock) else ""),
            "details": head + details,
            "deal_id": str(d.id), "proposed": proposed, "cancel": cancel, "cancel_reason": cancel_reason, "keep_run": keep_run,
            "reason": reason, "requested_by_user_id": str(user_id) if user_id else None,
            "related_entities": [],
            "facets": {"salesperson": rep.name if rep else "House account", "change": "Cancellation" if cancel else "Change",
                       "invoiced": "Affects invoiced items" if any("invoiced" in k for k in knock) else "Nothing invoiced yet"},
            "sort_date": now.date().isoformat(),
            "dedupe_key": f"{KIND}:{d.id}:{now.timestamp()}",
        })
    db.add(item)
    return item


def _requester(item: ReviewQueueItem) -> uuid.UUID | None:
    u = item.payload.get("requested_by_user_id")
    return uuid.UUID(u) if u else None


def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    from app.sales.accounts import can_approve
    d = db.get(SalesDeal, uuid.UUID(item.payload["deal_id"]))
    if not d:
        raise ValueError("This booking no longer exists.")
    actor = input_data.get("_actor_user_id")
    actor_id = uuid.UUID(actor) if actor else None
    if not can_approve(db, actor_id):
        raise ValueError("Only accounts can approve changes to a checked booking.")
    req = _requester(item)
    if action_id == "approve":
        from app.api.routes import deals as routes
        if item.payload.get("cancel"):
            routes.apply_status(db, d, "cancelled", item.payload.get("cancel_reason") or item.payload.get("reason"), item.payload.get("keep_run", True))
        else:
            if d.status == "cancelled":
                raise ValueError("This booking has been cancelled since the change was asked for.")
            routes.apply_change(db, d, routes.DealIn(**item.payload["proposed"]), actor_id)
        d.checked_at, d.checked_by_user_id, d.check_note = datetime.now(timezone.utc), actor_id, None   # accounts made it, so it stays checked
        if req:
            create_notification(db, req, "booking_change", f"Change to booking {d.number} approved",
                                "Accounts approved it. If the client needs an updated confirmation, send it from the booking.", link=f"/sales/deals/{d.id}")
        return
    if action_id == "decline":
        note = (input_data.get("note") or "").strip()
        if not note:
            raise ValueError("Say why, so the salesperson knows what to do next.")
        if req:
            create_notification(db, req, "booking_change", f"Change to booking {d.number} declined", note, link=f"/sales/deals/{d.id}")
        return
    raise ValueError("That action isn't available for change requests.")


register(ReviewKind(
    kind=KIND,
    label="Booking change",
    description="A salesperson wants to change or cancel a booking accounts has already checked - approve it and it's applied exactly as asked.",
    actions=[
        ReviewAction(id="approve", label="Approve and apply", style="primary", outcome="approved"),
        ReviewAction(id="decline", label="Decline", style="secondary", outcome="rejected", requires_note=True),
    ],
    handler=_handle,
    audience="admin",
    approver="accounts",
    facets=(("salesperson", "Salesperson"), ("change", "Kind of change"), ("invoiced", "Invoiced items")),
    date_sort_label="request date",
))
