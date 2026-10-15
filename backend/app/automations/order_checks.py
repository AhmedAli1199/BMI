"""Accounts check on bookings - Matt's safeguard from the 8 Oct meeting, reshaped on the 15 Oct call: the salesperson
sends the confirmation to the client and presses Confirm once the client has said yes; then someone in accounts
(Samantha) looks over what was typed - the client name, the CRM company it's linked to, the addresses, the contact
and the items - before it's invoiced, because mistakes there end up on invoices. Pencilled bookings aren't checked.

Every confirmed booking (and every checked one whose client, addresses or items change) gets one review item. "Looks right" marks the order checked; "Needs a fix" sends the note to the salesperson, and the order comes
back for checking once they save it again. While the "Confirmation waits for the check" setting is on, the
confirmation can't be sent or marked as sent until the order is checked (app/api/routes/deals.py).

Nothing here is automatic judgement - it only puts the order in front of a person, with every record linked.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.automations.registry import ReviewAction, ReviewKind, register
from app.models import Company, ReviewQueueItem, SalesDeal, SalesRep, SalesTitle, User
from app.services.notify import create_notification

KIND = "order_check"

# What the check is about; a change to any of these after a check means it needs checking again.
CHECKED_FIELDS = ("client_name", "company_id", "contact_id", "contact_name", "contact_email", "confirmation_address", "invoice_to",
                  "invoice_email", "po_number", "agency_name", "agency_pct")


def snapshot(d: SalesDeal) -> dict:
    lines = [(ln.get("description"), ln.get("title_id"), ln.get("qty"), ln.get("unit_price"),
              tuple(sorted(str(p.get("edition_id")) for p in ln.get("placements") or [])))
             for ln in d.lines or []]
    def norm(v):
        if v is None:
            return None
        if isinstance(v, (int, float)) or hasattr(v, "as_tuple"):   # numbers compare by value (0.0000 == 0)
            return round(float(v), 2)
        return str(v)

    return {**{k: norm(getattr(d, k)) for k in CHECKED_FIELDS}, "lines": repr(lines), "total": norm(d.total_gbp)}


def enabled(db: Session) -> bool:
    return runtime_settings.get_bool(db, "orders_accounts_check")


def blocks_sending(db: Session, d: SalesDeal) -> str | None:
    """The plain reason a confirmation can't go out yet, or None."""
    if not (enabled(db) and runtime_settings.get_bool(db, "orders_check_before_sending")) or d.checked_at:
        return None
    if d.check_note:
        return f"Accounts asked for a fix before this goes out: “{d.check_note}”. Change the booking and save it - it goes back for checking."
    return "This booking is waiting for the accounts check. The confirmation can go out as soon as it's marked as looking right."


def _money(v) -> str:
    return f"£{float(v or 0):,.2f}"


def _payload(db: Session, d: SalesDeal) -> dict:
    from app.api.routes.sales import edition_label
    from app.models import SalesEdition

    rep = db.get(SalesRep, d.rep_id) if d.rep_id else None
    company = db.get(Company, d.company_id) if d.company_id else None
    titles = {t.id: t for t in db.scalars(select(SalesTitle))}
    items = []
    title_names = set()
    for ln in d.lines or []:
        eds = [db.get(SalesEdition, uuid.UUID(str(p["edition_id"]))) for p in ln.get("placements") or [] if p.get("edition_id")]
        eds = [e for e in eds if e]
        for e in eds:
            title_names.add(re.sub(r"\s*\(.*\)", "", titles[e.title_id].name))
        where = ", ".join(edition_label(titles[e.title_id], e) for e in eds) or "no issue chosen"
        items.append(f"{ln.get('description') or ln.get('size') or 'Item'} - {where} - {_money(ln.get('total_gbp'))}")
    name_differs = company and company.name.strip().lower() != (d.client_name or "").strip().lower()
    details = [
        {"label": "Booking", "value": f"{d.number} ({d.status})", "href": f"/sales/deals/{d.id}"},
        {"label": "Client on the booking", "value": d.client_name},
        {"label": "CRM company", "value": company.name if company else "Not linked - check it's a new client",
         **({"href": f"/companies/{company.id}"} if company else {})},
        {"label": "Contact", "value": " · ".join(x for x in (d.contact_name, d.contact_email) if x) or "None given",
         **({"href": f"/contacts/{d.contact_id}"} if d.contact_id else {})},
        {"label": "Confirmation goes to", "value": d.confirmation_address or "No address given"},
        {"label": "Invoice to", "value": " · ".join(x for x in (d.invoice_to, d.invoice_email) if x) or "Same as the client"},
    ]
    if d.po_number:
        details.append({"label": "PO number", "value": d.po_number})
    if d.agency_name:
        details.append({"label": "Agency", "value": f"{d.agency_name} ({float(d.agency_pct or 0):.0%} commission)"})
    details.append({"label": "Items", "value": "\n".join(items) or "None"})
    details.append({"label": "Total before VAT", "value": _money(d.total_gbp)})
    details.append({"label": "Salesperson", "value": rep.name if rep else "House account"})
    from app.sales.invoicing import PLANS
    when = PLANS.get(d.invoice_plan or "asap", d.invoice_plan)
    if d.invoice_plan == "on_date" and d.invoice_on:
        when = f"On {d.invoice_on:%-d %b %Y}"
    details.append({"label": "When to invoice", "value": when + (f" · {d.invoice_currency}" if d.invoice_currency and d.invoice_currency != "GBP" else "")})
    if d.invoice_instructions:
        details.append({"label": "Invoice instructions", "value": d.invoice_instructions})
    if name_differs:
        details.insert(1, {"label": "Worth a look", "value": f"The client is typed as “{d.client_name}” but linked to “{company.name}”."})
    return {
        "summary": f"Check booking {d.number} for {d.client_name} ({_money(d.total_gbp)}) before it's invoiced",
        "details": details,
        "deal_id": str(d.id),
        "related_entities": [{"type": "company", "id": str(company.id), "label": company.name}] if company else [],
        "facets": {"salesperson": rep.name if rep else "House account", "title": ", ".join(sorted(title_names)) or "No issue yet",
                   "client": "Linked to a CRM company" if company else "Not linked to the CRM"},
        "sort_date": d.booked_on.isoformat() if d.booked_on else None,
        "owner_user_id": None,
        "dedupe_key": f"order_check:{d.id}",
    }


def request_check(db: Session, d: SalesDeal, before: dict | None = None) -> None:
    """After an order is saved: put it (back) in front of accounts if it needs checking. `before` is the
    snapshot taken before the save; a checked order whose checked details changed is checked again."""
    if not enabled(db) or d.status == "cancelled":
        return
    if d.status != "confirmed":
        # Pencilled: nothing to check until the client has said yes.
        withdraw(db, d, "Back to pencilled.")
        return
    if d.checked_at and before is not None and before != snapshot(d):
        d.checked_at = d.checked_by_user_id = None
    if d.checked_at:
        return
    pending = db.scalars(select(ReviewQueueItem).where(ReviewQueueItem.kind == KIND, ReviewQueueItem.status == "pending",
                                                       ReviewQueueItem.payload["deal_id"].astext == str(d.id))).first()
    title = None
    for ln in d.lines or []:
        if ln.get("title_id"):
            title = db.get(SalesTitle, uuid.UUID(str(ln["title_id"])))
            break
    payload = _payload(db, d)
    if before is not None and d.check_note:
        # Saved again after "Needs a fix": back to accounts, with what they asked for last time.
        payload["details"].insert(1, {"label": "Asked to fix last time", "value": d.check_note})
        d.check_note = None
    if pending:
        pending.payload = payload   # always shows the latest version of the order
        return
    db.add(ReviewQueueItem(id=uuid.uuid4(), kind=KIND, source_db=title.crm_source_db if title else None, status="pending",
                           entity_type="company" if d.company_id else None, entity_id=d.company_id, payload=payload))
    from app.sales.accounts import tell_accounts
    tell_accounts(db, KIND, f"Booking {d.number} confirmed: {d.client_name}", f"{_money(d.total_gbp)} before VAT, ready for your check.",
                  "/automations/review?kind=order_check", skip=d.created_by_user_id)


def withdraw(db: Session, d: SalesDeal, why: str) -> None:
    now = datetime.now(timezone.utc)
    for it in db.scalars(select(ReviewQueueItem).where(ReviewQueueItem.kind == KIND, ReviewQueueItem.status == "pending",
                                                       ReviewQueueItem.payload["deal_id"].astext == str(d.id))):
        it.status, it.resolved_action, it.reviewed_at, it.review_note = "rejected", "withdrawn", now, why


def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    d = db.get(SalesDeal, uuid.UUID(item.payload["deal_id"]))
    if not d:
        raise ValueError("This booking no longer exists.")
    actor = input_data.get("_actor_user_id")
    from app.sales.accounts import can_approve
    if not can_approve(db, uuid.UUID(actor) if actor else None):
        raise ValueError("Only accounts can check bookings.")
    if action_id == "approve":
        d.checked_at, d.checked_by_user_id, d.check_note = datetime.now(timezone.utc), uuid.UUID(actor) if actor else None, None
        from app.sales import handoffs
        handoffs.process(db, d)   # now editorial / production can start
        return
    if action_id == "fix":
        note = (input_data.get("note") or "").strip()
        if not note:
            raise ValueError("Say what needs fixing, so the salesperson knows.")
        d.checked_at, d.checked_by_user_id, d.check_note = None, None, note[:500]
        who = {u for u in (d.created_by_user_id,) if u}
        rep = db.get(SalesRep, d.rep_id) if d.rep_id else None
        if rep and rep.user_id:
            who.add(rep.user_id)
        checker = db.get(User, uuid.UUID(actor)) if actor else None
        for uid in who:
            create_notification(db, uid, "order_check", f"Booking {d.number} needs a fix before it's invoiced",
                                f"{checker.name if checker else 'Accounts'}: {note}", link=f"/sales/deals/{d.id}")
        return
    raise ValueError(f"Unknown action {action_id!r} for {KIND}")


register(ReviewKind(
    kind=KIND,
    label="Booking check",
    description="A confirmed (or changed) booking, for accounts to check the client, CRM company, addresses, items and when to invoice before it's invoiced. Looks right locks it; changes then go through accounts.",
    actions=[
        ReviewAction(id="approve", label="Looks right", style="primary", outcome="approved"),
        ReviewAction(id="fix", label="Needs a fix", style="secondary", outcome="rejected", requires_note=True),
    ],
    handler=_handle,
    audience="admin",
    approver="accounts",
    facets=(("salesperson", "Salesperson"), ("title", "Title"), ("client", "CRM company")),
    date_sort_label="booking date",
))
