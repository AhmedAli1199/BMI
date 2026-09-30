"""Automations that run on the Sales Order Register (app/models/sales.py):

- sor_client_match - "is this SOR client the CRM company X?" (the queue
  side of app/sales/matching.py). One item per client name; approving
  links every booking for that client.
- sor_invoice_missing - a booked order whose edition has published / the
  event has happened, still with no invoice number. Replaces eyeballing
  the sheet's "Total difference" cell. Approving records the invoice.
- renewal_due (SALES-021) - an advertiser who booked a title last year,
  coming up to the anniversary of that booking, who hasn't rebooked the
  title this year. Queues a drafted renewal email quoting their actual
  previous placement, for the rep to send.

Same contract as every other automation here: these only ever queue a
review item; nothing is invoiced, linked or emailed without a person
approving it.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas import MANUAL_SOURCE_DB
from app.automations import runtime_settings
from app.automations.llm import extract_json, is_configured
from app.automations.registry import ExtraField, ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.db.session import SessionLocal
from app.models import Company, Note, ReviewQueueItem, SalesEdition, SalesOrder, SalesRep, SalesTitle
from app.sales.analytics import BOOKED
from app.sales.matching import MATCH_KIND, match_clients

logger = logging.getLogger("app.automations.sales_orders")


def _edition_label(db: Session, ed: SalesEdition) -> str:
    from app.api.routes.sales import edition_label

    return edition_label(db.get(SalesTitle, ed.title_id), ed)


def _money(v) -> str:
    return f"£{float(v or 0):,.2f}".replace(".00", "")


# ---- sor_client_match -------------------------------------------------------

def _handle_client_match(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    client = (item.payload.get("client_name") or "").strip().lower()
    orders = db.scalars(select(SalesOrder).where(
        SalesOrder.company_id.is_(None), func.lower(func.trim(SalesOrder.client_name)) == client)).all()
    if action_id == "link":
        company = db.get(Company, item.payload.get("company_id"))
        if not company:
            raise ValueError("That company no longer exists in the CRM.")
        for o in orders:
            o.company_id = company.id
            o.match_dismissed = False
    elif action_id == "not_a_match":
        for o in orders:
            o.match_dismissed = True
    else:
        raise ValueError(f"Unknown action {action_id!r} for {MATCH_KIND}")


register(ReviewKind(
    kind=MATCH_KIND,
    label="Order Register Client Matching",
    description="Clients typed into the order register that look like an existing CRM company - confirm once and every booking for them is linked.",
    actions=[
        ReviewAction(id="link", label="Yes - link all their bookings", style="primary", outcome="approved"),
        ReviewAction(id="not_a_match", label="Not the same company", style="secondary", outcome="rejected"),
    ],
    handler=_handle_client_match,
    audience="admin",
))


def scan_client_matches() -> None:
    db = SessionLocal()
    try:
        linked, queued = match_clients(db, max_queued=runtime_settings.get_int(db, "sor_match_max_per_run"))
        db.commit()
        logger.info("sor client match: %d booking(s) linked, %d suggestion(s) queued", linked, queued)
    finally:
        db.close()


# ---- sor_invoice_missing ----------------------------------------------------

INVOICE_KIND = "sor_invoice_missing"


def _handle_invoice(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    order = db.get(SalesOrder, item.payload.get("order_id"))
    if not order:
        raise ValueError("This booking no longer exists.")
    if action_id == "record_invoice":
        number = (input_data.get("invoice_number") or "").strip()
        if not number:
            raise ValueError("Enter the invoice number.")
        raw_value = (input_data.get("invoice_value") or "").replace("£", "").replace(",", "").strip()
        try:
            value = float(raw_value) if raw_value else float(order.value_gbp)
        except ValueError as e:
            raise ValueError("Invoice value must be a number, e.g. 1250 or 1250.50.") from e
        order.invoice_number = number[:60]
        order.invoice_value_gbp = value
        order.invoiced_on = date.today()
    elif action_id == "no_invoice_needed":
        note = (input_data.get("note") or "").strip()
        order.invoice_note = "; ".join(filter(None, [order.invoice_note, f"No invoice needed: {note}" if note else "No invoice needed"]))
    elif action_id == "later":
        pass  # stays uninvoiced; the scan re-queues it after the snooze window
    else:
        raise ValueError(f"Unknown action {action_id!r} for {INVOICE_KIND}")


register(ReviewKind(
    kind=INVOICE_KIND,
    label="Uninvoiced Bookings",
    description="Bookings whose issue has published or event has run, still without an invoice number in the order register.",
    actions=[
        ReviewAction(id="record_invoice", label="Record invoice", style="primary", outcome="approved", extra_fields=[
            ExtraField(key="invoice_number", label="Invoice number", placeholder="INV-3050"),
            ExtraField(key="invoice_value", label="Invoice value (£) - leave blank if it's the booking value", placeholder="", required=False),
        ]),
        ReviewAction(id="later", label="Not yet - remind me later", style="secondary", outcome="rejected"),
        ReviewAction(id="no_invoice_needed", label="No invoice needed", style="secondary", outcome="rejected", requires_note=True),
    ],
    handler=_handle_invoice,
    audience="admin",
))


def scan_uninvoiced() -> None:
    today = date.today()
    db = SessionLocal()
    try:
        grace = runtime_settings.get_int(db, "sor_invoice_grace_days")
        snooze = runtime_settings.get_int(db, "sor_invoice_snooze_days")
        max_per_run = runtime_settings.get_int(db, "sor_invoice_max_per_run")
        cutoff = today - timedelta(days=grace)

        recent = {}
        for order_id, status, action, reviewed_at in db.execute(select(
            ReviewQueueItem.payload["order_id"].astext, ReviewQueueItem.status, ReviewQueueItem.resolved_action,
            ReviewQueueItem.reviewed_at).where(ReviewQueueItem.kind == INVOICE_KIND)).all():
            recent.setdefault(order_id, []).append((status, action, reviewed_at))

        rows = db.execute(
            select(SalesOrder, SalesEdition).join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
            .where(SalesOrder.status == BOOKED, SalesOrder.value_gbp > 0, SalesOrder.invoice_number.is_(None),
                   SalesEdition.edition_date.isnot(None), SalesEdition.edition_date <= cutoff,
                   SalesEdition.edition_date >= today - timedelta(days=400))
            .order_by(SalesEdition.edition_date)
        ).all()
        reps = {r.id: r for r in db.scalars(select(SalesRep))}
        queued = 0
        for order, ed in rows:
            if queued >= max_per_run:
                break
            if "No invoice needed" in (order.invoice_note or ""):
                continue
            history = recent.get(str(order.id), [])
            if any(s == "pending" for s, _, _ in history):
                continue
            if any(a == "later" and r and r.date() > today - timedelta(days=snooze) for _, a, r in history):
                continue
            label = _edition_label(db, ed)
            days = (today - ed.edition_date).days
            rep = reps.get(order.rep_id)
            title = db.get(SalesTitle, ed.title_id)
            db.add(ReviewQueueItem(
                id=uuid.uuid4(), kind=INVOICE_KIND, source_db=title.crm_source_db,
                entity_type="company" if order.company_id else None, entity_id=order.company_id,
                payload={
                    "summary": f"No invoice yet: {order.client_name} - {label} ({_money(order.value_gbp)})",
                    "details": [
                        {"key": "client", "label": "Client", "value": order.client_name},
                        {"key": "edition", "label": "Edition", "value": label},
                        {"key": "edition_date", "label": "Published / held", "value": f"{ed.edition_date:%d %b %Y} ({days} days ago)"},
                        {"key": "value", "label": "Booking value", "value": _money(order.value_gbp)},
                        {"key": "size", "label": "What was sold", "value": order.size or "-"},
                        {"key": "rep", "label": "Salesperson", "value": rep.name if rep else "-"},
                        {"key": "note", "label": "Sheet note", "value": order.invoice_note or "-"},
                    ],
                    "related_entities": [{"type": "company", "id": str(order.company_id), "label": order.client_name}] if order.company_id else [],
                    "order_id": str(order.id),
                    "edition_id": str(ed.id),
                    "due_date": ed.edition_date.isoformat(),
                },
            ))
            queued += 1
        db.commit()
        logger.info("sor invoice chase: %d item(s) queued of %d uninvoiced candidate(s)", queued, len(rows))
    finally:
        db.close()


# ---- renewal_due (SALES-021) ------------------------------------------------

RENEWAL_KIND = "renewal_due"

_RENEWAL_PROMPT = (
    "You draft a short renewal email a BMI Publishing salesperson can send to an advertiser who booked with one of "
    "BMI's titles last year and hasn't rebooked yet. Mention their actual previous placement (the edition and what "
    "they booked) naturally, say the new edition is now open for bookings, and ask if they'd like to secure their "
    "space again - friendly, professional, 3-5 sentences, no invented prices, dates or statistics. Return JSON of "
    "the exact shape {\"subject\": string, \"body\": string}; body is the email text only."
)


_SIZE_WORDS = {"fp": "a full page", "page": "a full page", "1": "a full page", "dps": "a double-page spread",
               "0.5": "a half page", "1/2": "a half page", "1/2 page": "a half page", "0.25": "a quarter page",
               "1/4": "a quarter page", "banner": "a banner", "listing": "a listing", "one ticket": "a ticket",
               "partner": "a partnership", "digital": "a digital package"}


def describe_size(size: str | None) -> str | None:
    """The sheet's shorthand ("FP", "0.5", "DPS") in words a client reads."""
    if not size:
        return None
    return _SIZE_WORDS.get(size.strip().lower(), size.strip())


def _renewal_draft(client: str, title: str, last_label: str, size: str | None, extra: str = "") -> tuple[str, bool]:
    words = describe_size(size)
    what = f"{words} in {last_label}" if words else f"space in {last_label}"
    if is_configured():
        prompt = _RENEWAL_PROMPT + (f"\n\nThe reviewer asked for this revision - follow it: {extra}" if extra else "")
        result = extract_json(prompt, f"Advertiser: {client}\nTitle: {title}\nLast year they booked: {what}",
                              purpose="sor_renewal.draft")
        subject, body = (result or {}).get("subject", "").strip(), (result or {}).get("body", "").strip()
        if subject and body:
            return f"Subject: {subject}\n\n{body}", True
    body = (f"Hi,\n\nThank you again for booking {what} last year. The new {title} edition is now open for "
            f"bookings, and I wanted to give you first refusal on the same space before it goes.\n\n"
            f"Would you like me to reserve it for you again?\n\nBest regards")
    return f"Subject: {title} - securing your space again\n\n{body}", False


def _handle_renewal(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "approve":
        company_id = item.payload.get("company_id")
        draft = (input_data.get("note") or "").strip() or item.payload.get("original_text") or ""
        if company_id and db.get(Company, company_id):
            db.add(Note(
                id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()),
                entity_type="company", entity_id=company_id, note_type="Renewal outreach",
                body=draft, act_created_at=datetime.now(timezone.utc),
            ))
    elif action_id != "skip":
        raise ValueError(f"Unknown action {action_id!r} for {RENEWAL_KIND}")


def _redraft_renewal(db: Session, item: ReviewQueueItem, extra: str) -> str:
    p = item.payload
    draft, _ = _renewal_draft(p.get("client_name", ""), p.get("title_name", ""), p.get("last_edition_label", ""), p.get("size"), extra)
    return draft


register(ReviewKind(
    kind=RENEWAL_KIND,
    label="Renewal Outreach",
    description="Last year's advertisers coming up to the anniversary of their booking who haven't rebooked yet - with a drafted renewal email quoting their previous placement.",
    actions=[
        ReviewAction(id="approve", label="Approve & log to CRM", style="primary", outcome="approved"),
        ReviewAction(id="skip", label="Skip this year", style="secondary", outcome="rejected"),
    ],
    handler=_handle_renewal,
    redraft=_redraft_renewal,
    audience="sales",
))


def scan_renewals() -> None:
    """For every title: last year's advertisers (not yet rebooked this
    year) whose last-year booking date is within the lead window of its
    anniversary. One item per advertiser per title per year, ever."""
    today = date.today()
    db = SessionLocal()
    try:
        from app.api.routes.sales import renewal_candidates

        lead = runtime_settings.get_int(db, "sor_renewal_lead_days")
        max_per_run = runtime_settings.get_int(db, "sor_renewal_max_per_run")
        seen = set(db.scalars(select(ReviewQueueItem.payload["dedupe_key"].astext).where(ReviewQueueItem.kind == RENEWAL_KIND)).all())
        reps = {r.id: r for r in db.scalars(select(SalesRep))}
        queued = 0
        for title in db.scalars(select(SalesTitle).where(SalesTitle.active.is_(True)).order_by(SalesTitle.sort_order)):
            rows, _, _ = renewal_candidates(db, title.id, today.year)
            for r in rows:
                if queued >= max_per_run:
                    break
                order, ed = r["order"], r["edition"]
                anchor = order.booked_on or ed.edition_date
                if not anchor:
                    continue
                try:
                    anniversary = anchor.replace(year=anchor.year + 1)
                except ValueError:
                    anniversary = anchor + timedelta(days=365)
                if not (anniversary - timedelta(days=lead) <= today <= anniversary + timedelta(days=90)):
                    continue
                key = f"{title.id}:{order.client_name.strip().lower()}:{today.year}"
                if key in seen:
                    continue
                last_label = _edition_label(db, ed)
                draft, was_ai = _renewal_draft(order.client_name, title.name, last_label, order.size)
                rep = reps.get(order.rep_id)
                db.add(ReviewQueueItem(
                    id=uuid.uuid4(), kind=RENEWAL_KIND, source_db=title.crm_source_db,
                    entity_type="company" if order.company_id else None, entity_id=order.company_id,
                    payload={
                        "summary": f"Renewal due: {order.client_name} - {title.name} (booked {_money(r['total'])} last year)",
                        "details": [
                            {"key": "client", "label": "Advertiser", "value": order.client_name},
                            {"key": "last", "label": "Last booking", "value": f"{order.size or 'Space'} in {last_label}"
                                                                              + (f", booked {order.booked_on:%d %b %Y}" if order.booked_on else "")},
                            {"key": "value", "label": "Spent with this title last year", "value": f"{_money(r['total'])} across {r['count']} booking(s)"},
                            {"key": "rep", "label": "Their salesperson", "value": rep.name if rep else "-"},
                            {"key": "draft_source", "label": "Draft", "value": "AI-drafted" if was_ai else "Templated (no AI configured)"},
                        ],
                        "original_text": draft,
                        "related_entities": [{"type": "company", "id": str(order.company_id), "label": order.client_name}] if order.company_id else [],
                        "client_name": order.client_name, "title_name": title.name, "title_id": str(title.id),
                        "last_edition_label": last_label, "size": order.size,
                        "company_id": str(order.company_id) if order.company_id else None,
                        "dedupe_key": key, "due_date": anniversary.isoformat(),
                    },
                ))
                seen.add(key)
                queued += 1
        db.commit()
        logger.info("sor renewal scan: %d renewal(s) queued", queued)
    finally:
        db.close()


register_job(ScheduledJob(
    id="sor_client_match_scan",
    label="Order register client matching",
    description="Links order-register clients to CRM companies - exact name matches automatically, likely matches queued for a person to confirm.",
    cron="30 5 * * *",
    func=scan_client_matches,
    enabled_flag="automations_sor_client_match_scan_enabled",
))
register_job(ScheduledJob(
    id="sor_invoice_chase_scan",
    label="Uninvoiced booking scan",
    description="Finds booked orders whose issue has published or event has run, still with no invoice number.",
    cron="0 7 * * 1-5",
    func=scan_uninvoiced,
    enabled_flag="automations_sor_invoice_chase_scan_enabled",
))
register_job(ScheduledJob(
    id="sor_renewal_scan",
    label="Renewal outreach scan",
    description="Drafts renewal emails for last year's advertisers approaching the anniversary of their booking who haven't rebooked (SALES-021).",
    cron="30 6 * * 1-5",
    func=scan_renewals,
    enabled_flag="automations_sor_renewal_scan_enabled",
))
