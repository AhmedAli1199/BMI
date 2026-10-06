"""Invoice matching - links Xero invoices to bookings so nobody types
invoice numbers (see app/sales/invoice_match.py for how a match is judged).

Every hour, after the Xero sync:
1. a booking whose typed number matches a Xero invoice gets a real link;
2. every Xero sales invoice no booking has is matched against the bookings
   still waiting for an invoice;
3. a CLEAR match is applied on its own (number, value and date filled in,
   and "Linked automatically to Xero invoice N" written to the booking's
   history; the booking's edit panel offers Undo). It does NOT go in the
   review queue - that would only clutter it;
4. anything less clear becomes a review item - the invoice on one side,
   the candidate booking(s) with the reasons on the other - for a
   salesperson to confirm with one click;
5. invoices that fit no booking at all are listed on the Invoicing page as
   "in Xero, not in the register".

Nothing is ever written to Xero. Off by default: switch on "Xero invoice
matching" in the Automations settings (Run now works without that).
"""
from __future__ import annotations

import logging
import uuid
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.automations.registry import ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.automations.state import get_state, set_state
from app.db.session import SessionLocal
from app.models import ReviewQueueItem, SalesOrder, SalesRep, XeroInvoice
from app.sales import invoice_match as im
from app.services.xero import number_key

logger = logging.getLogger("app.automations.xero_matching")

KIND = "sor_invoice_match"
UNMATCHED_STATE = "xero_match_unmatched"
DECLINED_STATE = "xero_match_declined"   # invoices whose automatic link someone undid - never offered again


def _item(ctx: im.Context, inv: XeroInvoice, hyps: list[im.Hypothesis], reps: dict[uuid.UUID, SalesRep], *,
          status: str, reason: str | None) -> ReviewQueueItem:
    top = hyps[0]
    first = top.orders[0]
    ed = ctx.editions[first.edition_id]
    title = ctx.titles[ed.title_id]
    rep = reps.get(first.rep_id)
    names = ", ".join(sorted({o.client_name for o in top.orders}))
    candidates = im.candidate_payload(ctx, inv, hyps, {r.id: r.name for r in reps.values()})
    payload = {
        "summary": f"Invoice {inv.invoice_number} to {inv.contact_name} ({im._money(float(inv.sub_total or 0))} before VAT) - which booking is it for?"
                   if status == "pending" else f"Invoice {inv.invoice_number} linked to {names}",
        "invoice_id": str(inv.id),
        "invoice_match": {"invoice": im.invoice_facts(inv), "candidates": candidates, "reason": reason},
        "owner_user_id": str(rep.user_id) if rep and rep.user_id else None,
        "dedupe_key": f"xero_invoice:{inv.id}",
        "related_entities": [],
    }
    return ReviewQueueItem(
        id=uuid.uuid4(), kind=KIND, source_db=title.crm_source_db, status=status,
        entity_type="company" if first.company_id else None, entity_id=first.company_id, payload=payload)


def run_matching(db: Session, *, auto_link: bool | None = None, max_new: int | None = None) -> dict:
    """One matching pass. Returns counts: auto, review, no_fit, typed_links, deferred, withdrawn."""
    from app.services.xero import link_typed_numbers

    now = datetime.now(timezone.utc)
    counts: Counter = Counter()
    counts["typed_links"] = link_typed_numbers(db)
    auto_on = runtime_settings.get_bool(db, "xero_match_auto_link") if auto_link is None else auto_link
    max_new = runtime_settings.get_int(db, "xero_match_max_per_run") if max_new is None else max_new
    ctx = im.build_context(db)
    reps = {r.id: r for r in db.scalars(select(SalesRep))}
    unclaimed = im.unclaimed_invoices(db)
    unclaimed_ids = {i.id for i in unclaimed}

    existing = db.scalars(select(ReviewQueueItem).where(ReviewQueueItem.kind == KIND)).all()
    declined = set(get_state(db, DECLINED_STATE).get("ids", []))
    for it in list(existing):   # tidy: automatic links no longer get a review item - the booking's history says it
        if it.resolved_action == "auto_link":
            if uuid.UUID(it.payload["invoice_id"]) in unclaimed_ids:   # it was undone: remember that
                declined.add(it.payload["invoice_id"])
            db.delete(it)
            existing.remove(it)
    seen = {i.payload.get("invoice_id") for i in existing} | declined
    for it in existing:   # a waiting item whose invoice was linked by hand since: nothing left to decide
        if it.status == "pending" and uuid.UUID(it.payload["invoice_id"]) not in unclaimed_ids:
            it.status, it.resolved_action, it.reviewed_at = "approved", "linked_elsewhere", now
            it.review_note = "Someone typed this invoice number on a booking before it was reviewed."
            counts["withdrawn"] += 1

    work = [(inv, im.hypotheses(ctx, inv)) for inv in unclaimed if str(inv.id) not in seen]
    no_fit = [inv for inv, h in work if not h]
    counts["no_fit"] = len(no_fit)
    taken: set[uuid.UUID] = set()
    for inv, hyps in sorted((w for w in work if w[1]), key=lambda w: -w[1][0].score):
        top, rest = hyps[0], hyps[1:]
        ids = {o.id for o in top.orders}
        clear = im.is_clear(top, rest) and not any(o.invoice_number for o in top.orders) and not (ids & taken)
        if clear and auto_on:
            im.link_bookings(db, inv, top.orders, "auto", None)   # recorded on the booking's history, not in the queue
            taken |= ids
            counts["auto"] += 1
        elif counts["review"] >= max_new:
            counts["deferred"] += 1   # picked up on the next run
        else:
            reason = im.why_not_automatic(top, rest, inv, auto_on) if not (ids & taken) else \
                "Another invoice in this batch fits the same booking. Pick the right one."
            db.add(_item(ctx, inv, hyps, reps, status="pending", reason=reason))
            counts["review"] += 1
    set_state(db, UNMATCHED_STATE, {"ids": [str(i.id) for i in no_fit], "at": now.isoformat()})
    db.commit()
    return dict(counts)


def scan_invoice_matches() -> None:
    db = SessionLocal()
    try:
        result = run_matching(db)
        logger.info("xero invoice matching: %s", result)
    finally:
        db.close()


def remember_declined(db: Session, invoice_id: uuid.UUID) -> None:
    """An automatic link was undone: never offer that invoice again."""
    ids = set(get_state(db, DECLINED_STATE).get("ids", []))
    ids.add(str(invoice_id))
    set_state(db, DECLINED_STATE, {"ids": sorted(ids)})


def unmatched_invoice_ids(db: Session) -> tuple[list[uuid.UUID], str | None]:
    st = get_state(db, UNMATCHED_STATE)
    return [uuid.UUID(i) for i in st.get("ids", [])], st.get("at")


# ---- the review item ------------------------------------------------------------------

def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "none":
        return
    if action_id != "link":
        raise ValueError(f"Unknown action {action_id!r} for {KIND}")
    key = input_data.get("chosen_entity_id")
    match = item.payload.get("invoice_match") or {}
    cand = next((c for c in match.get("candidates", []) if c["key"] == key), None)
    if not cand:
        raise ValueError("Pick which booking this invoice is for.")
    inv = db.get(XeroInvoice, uuid.UUID(item.payload["invoice_id"]))
    if not inv or inv.status in ("VOIDED", "DELETED"):
        raise ValueError("That invoice has been voided or deleted in Xero, so there's nothing to link.")
    holder = db.scalars(select(SalesOrder).where(SalesOrder.xero_invoice_id == inv.id)).first()
    if holder:
        raise ValueError(f"This invoice is already linked to “{holder.client_name}”.")
    orders = []
    for b in cand["bookings"]:
        o = db.get(SalesOrder, uuid.UUID(b["id"]))
        if not o:
            raise ValueError(f"The booking for “{b['client']}” no longer exists.")
        if o.status != "booked":
            raise ValueError(f"The booking for “{o.client_name}” is {o.status} now, so it can't be linked.")
        if o.xero_invoice_id:
            raise ValueError(f"“{o.client_name}” already has invoice {o.invoice_number} - nothing to link.")
        orders.append(o)
    actor = input_data.get("_actor_user_id")
    im.link_bookings(db, inv, orders, "confirmed", uuid.UUID(actor) if actor else None)
    item.payload = {**item.payload, "linked": {"candidate": key, "booking_ids": [str(o.id) for o in orders], "auto": False}}


register(ReviewKind(
    kind=KIND,
    label="Invoice to booking",
    description=("A new invoice in Xero that isn't clearly any one booking's yet - with the likely bookings and the reasons "
                 "side by side, so you can link it in one click."),
    actions=[
        ReviewAction(id="link", label="Yes, link this invoice", style="primary", outcome="approved"),
        ReviewAction(id="none", label="None of these", style="secondary", outcome="rejected"),
    ],
    handler=_handle,
    audience="sales",
))

register_job(ScheduledJob(
    id="xero_invoice_match_scan", label="Xero invoice matching",
    description="Hourly, after the Xero sync: links each new invoice to its booking. Clear matches fill in the invoice number automatically; the rest wait in the review queue.",
    cron="40 * * * *", func=scan_invoice_matches, enabled_flag="automations_xero_match_enabled",
))
