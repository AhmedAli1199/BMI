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
from app.models import Company, Note, ReviewQueueItem, SalesEdition, SalesOrder, SalesRep, SalesTitle, User
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
    "space again - friendly, professional, 3-5 sentences. If a link to their previous ad is given, include it "
    "exactly as given. If this year's price is given, state it exactly as given; if no price is given, do not "
    "mention any price. Never invent prices, dates, figures or links. Write in the first person as the salesperson; "
    "sign off with the salesperson's first name if given. Return JSON of the exact shape "
    "{\"subject\": string, \"body\": string}; body is the email text only."
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


def _renewal_draft(client: str, title: str, last_label: str, size: str | None, extra: str = "", *,
                   price: str | None = None, link: str | None = None, sender: str | None = None) -> tuple[str, bool]:
    words = describe_size(size)
    what = f"{words} in {last_label}" if words else f"space in {last_label}"
    if is_configured():
        prompt = _RENEWAL_PROMPT + (f"\n\nThe reviewer asked for this revision - follow it: {extra}" if extra else "")
        facts = [f"Advertiser: {client}", f"Title: {title}", f"Last year they booked: {what}"]
        if link:
            facts.append(f"Link to their previous ad: {link}")
        if price:
            facts.append(f"This year's price for the same: {price}")
        if sender:
            facts.append(f"Salesperson: {sender}")
        result = extract_json(prompt, "\n".join(facts), purpose="sor_renewal.draft")
        subject, body = (result or {}).get("subject", "").strip(), (result or {}).get("body", "").strip()
        if subject and body:
            return f"Subject: {subject}\n\n{body}", True
    paras = [f"Hi,\n\nThank you again for booking {what} last year."
             + (f" You can see it again here: {link}" if link else "")]
    paras.append(f"The new {title} edition is now open for bookings, and I wanted to give you first refusal on "
                 f"the same space before it goes." + (f" This year the same placement is {price}." if price else ""))
    paras.append("Would you like me to reserve it for you again?")
    paras.append("Best regards" + (f"\n{sender}" if sender else ""))
    body = "\n\n".join(paras)
    return f"Subject: {title} - securing your space again\n\n{body}", False


def _split_draft(draft: str) -> tuple[str, str]:
    """"Subject: X\n\nbody" -> (X, body)."""
    text = (draft or "").strip()
    if text.lower().startswith("subject:"):
        first, _, rest = text.partition("\n")
        return first[len("subject:"):].strip(), rest.strip()
    return "", text


def _renewal_facts(db: Session, title: SalesTitle, ed: SalesEdition, order: SalesOrder, target_year: int) -> dict:
    """Price, link, owner and recipient for one renewal - each one either
    known for certain or flagged as missing, never guessed."""
    from app.sales import renewals as rn

    rate = rn.current_price(db, title.id, target_year, order.size)
    link = rn.placement_link(title, ed, order)
    owner_id = rn.owner_user_id(db, order)
    owner = db.get(User, owner_id) if owner_id else None
    recipient = rn.best_recipient(db, order.company_id)
    return {
        "price": _money(rate.price_gbp) if rate else None,
        "price_note": f"{_money(rate.price_gbp)} ({rate.product}, {target_year} rate card)" if rate
        else f"Not on the {target_year} rate card - add it, then Regenerate (the draft quotes no price)",
        "link": link.url, "link_level": link.level, "link_note": link.note,
        "owner_user_id": str(owner_id) if owner_id else None,
        "owner_name": owner.name if owner else None,
        "suggested_to": recipient[0] if recipient else "",
        "suggested_to_name": recipient[1] if recipient else "",
    }


def _renewal_details(order: SalesOrder, last_label: str, total: float, count: int, rep: SalesRep | None,
                     facts: dict, was_ai: bool) -> list[dict]:
    return [
        {"key": "client", "label": "Advertiser", "value": order.client_name},
        {"key": "last", "label": "Last booking", "value": f"{order.size or 'Space'} in {last_label}"
                                                          + (f", booked {order.booked_on:%d %b %Y}" if order.booked_on else "")},
        {"key": "value", "label": "Spent with this title last year", "value": f"{_money(total)} across {count} booking(s)"},
        {"key": "rep", "label": "Their salesperson", "value": rep.name if rep else "-"},
        {"key": "price", "label": "This year's price", "value": facts["price_note"]},
        {"key": "link", "label": "Previous ad online", "value": facts["link"] or facts["link_note"]},
        {"key": "to", "label": "Suggested recipient", "value": (f"{facts['suggested_to_name']} <{facts['suggested_to']}>".strip()
                                                               if facts["suggested_to"] else "No contact with an email at this company yet")},
        {"key": "draft_source", "label": "Draft", "value": "AI-drafted" if was_ai else "Templated (no AI configured)"},
    ]


def queue_renewal(db: Session, title: SalesTitle, order: SalesOrder, ed: SalesEdition, total: float, count: int,
                  target_year: int, *, reason: str, due: date | None, seen: set[str], reps: dict) -> ReviewQueueItem | None:
    """One renewal item, unless this advertiser already has one for this
    title this year (from the anniversary scan or an edition's renewal
    pass - the same key, so nobody is approached twice)."""
    key = f"{title.id}:{order.client_name.strip().lower()}:{target_year}"
    if key in seen:
        return None
    last_label = _edition_label(db, ed)
    facts = _renewal_facts(db, title, ed, order, target_year)
    rep = reps.get(order.rep_id)
    draft, was_ai = _renewal_draft(order.client_name, title.name, last_label, order.size,
                                   price=facts["price"], link=facts["link"],
                                   sender=(facts["owner_name"] or (rep.name if rep else "") or "").split(" ")[0] or None)
    item = ReviewQueueItem(
        id=uuid.uuid4(), kind=RENEWAL_KIND, source_db=title.crm_source_db,
        entity_type="company" if order.company_id else None, entity_id=order.company_id,
        payload={
            "summary": f"Renewal due: {order.client_name} - {title.name} (booked {_money(total)} last year)",
            "details": _renewal_details(order, last_label, total, count, rep, facts, was_ai),
            "original_text": draft,
            "original_label": "Draft email",
            "related_entities": [{"type": "company", "id": str(order.company_id), "label": order.client_name}] if order.company_id else [],
            "client_name": order.client_name, "title_name": title.name, "title_id": str(title.id),
            "edition_id": str(ed.id), "order_id": str(order.id),
            "last_edition_label": last_label, "size": order.size, "target_year": target_year,
            "company_id": str(order.company_id) if order.company_id else None,
            "owner_user_id": facts["owner_user_id"], "owner_name": facts["owner_name"],
            "suggested_to": facts["suggested_to"],
            "total": total, "count": count, "reason": reason,
            "dedupe_key": key, "due_date": due.isoformat() if due else None,
        },
    )
    db.add(item)
    seen.add(key)
    return item


def _close_if_rebooked(db: Session, item: ReviewQueueItem) -> None:
    from app.sales.renewals import rebooked

    p = item.payload
    year = p.get("target_year") or date.today().year
    if p.get("title_id") and rebooked(db, uuid.UUID(p["title_id"]), year, p.get("client_name", ""),
                                      uuid.UUID(p["company_id"]) if p.get("company_id") else None):
        raise ValueError(f"{p.get('client_name')} has already booked {p.get('title_name')} for {year} - "
                         "no renewal needed. Use “Skip this year” to clear it.")


def _log_renewal(db: Session, item: ReviewQueueItem, text: str, note_type: str) -> None:
    company_id = item.payload.get("company_id")
    if company_id and db.get(Company, company_id):
        db.add(Note(
            id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()),
            entity_type="company", entity_id=company_id, note_type=note_type,
            body=text, act_created_at=datetime.now(timezone.utc),
        ))


def _handle_renewal(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    draft = (input_data.get("note") or "").strip() or item.payload.get("original_text") or ""
    if action_id == "approve":
        _close_if_rebooked(db, item)
        _log_renewal(db, item, draft, "Renewal outreach")
    elif action_id == "send":
        _close_if_rebooked(db, item)
        _send_renewal(db, item, draft, input_data)
    elif action_id != "skip":
        raise ValueError(f"Unknown action {action_id!r} for {RENEWAL_KIND}")


def _send_renewal(db: Session, item: ReviewQueueItem, draft: str, input_data: dict) -> None:
    """Sends the (possibly edited) draft from the reviewer's own Outlook -
    it lands in their Sent Items and replies come back to them - then logs
    it on the company."""
    import re as _re

    from app.models.messaging import MailAccount
    from app.services import outlook
    from app.services.mail_merge import to_html

    to = (input_data.get("to") or item.payload.get("suggested_to") or "").strip()
    if not _re.fullmatch(r"[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+", to):
        raise ValueError("Enter the email address to send this to.")
    actor = input_data.get("_actor_user_id")
    acct = db.scalar(select(MailAccount).where(MailAccount.user_id == uuid.UUID(actor))) if actor else None
    if not acct:
        raise ValueError("Connect your Outlook first (Settings › Email) - renewals are sent from your own mailbox. "
                         "Or use “Approve & log to CRM” and send it yourself.")
    subject, body = _split_draft(draft)
    if not subject:
        subject = f"{item.payload.get('title_name', 'BMI')} - securing your space again"
    try:
        outlook.send_mail(db, acct, to=[to], subject=subject, html_body=to_html(body))
    except outlook.OutlookAuthError as exc:
        raise ValueError(f"{exc} Reconnect Outlook in Settings, then try again.") from exc
    except outlook.RateLimited as exc:
        raise ValueError("Outlook is asking us to slow down - try again in a minute.") from exc
    except RuntimeError as exc:
        raise ValueError(str(exc)) from exc
    _log_renewal(db, item, f"Sent to {to} from {acct.email}\n\nSubject: {subject}\n\n{body}", "Renewal sent")
    item.payload = {**item.payload, "sent_to": to, "sent_from": acct.email}


def _redraft_renewal(db: Session, item: ReviewQueueItem, extra: str) -> str:
    """Rebuilds from current facts too, so a price added to the rate card
    (or a link set up) after the item was queued shows up on Regenerate."""
    p = item.payload
    title = db.get(SalesTitle, uuid.UUID(p["title_id"])) if p.get("title_id") else None
    ed = db.get(SalesEdition, uuid.UUID(p["edition_id"])) if p.get("edition_id") else None
    order = db.get(SalesOrder, uuid.UUID(p["order_id"])) if p.get("order_id") else None
    facts = {"price": None, "link": None, "owner_name": p.get("owner_name")}
    if title and ed and order:
        facts = _renewal_facts(db, title, ed, order, p.get("target_year") or date.today().year)
        rep = db.get(SalesRep, order.rep_id) if order.rep_id else None
        item.payload = {**p, "details": _renewal_details(order, p.get("last_edition_label", ""), p.get("total", 0),
                                                        p.get("count", 1), rep, facts, True),
                        "suggested_to": p.get("suggested_to") or facts["suggested_to"]}
    draft, _ = _renewal_draft(p.get("client_name", ""), p.get("title_name", ""), p.get("last_edition_label", ""),
                              p.get("size"), extra, price=facts.get("price"), link=facts.get("link"),
                              sender=(facts.get("owner_name") or "").split(" ")[0] or None)
    return draft


register(ReviewKind(
    kind=RENEWAL_KIND,
    label="Renewal Outreach",
    description="Last year's advertisers who haven't rebooked yet - with a drafted renewal email quoting their previous placement, a link to it and this year's price.",
    actions=[
        ReviewAction(id="send", label="Send from my Outlook", style="primary", outcome="approved",
                     extra_fields=[ExtraField(key="to", label="Send to", placeholder="name@company.com", required=False)]),
        ReviewAction(id="approve", label="Log to CRM only", style="secondary", outcome="approved"),
        ReviewAction(id="skip", label="Skip this year", style="secondary", outcome="rejected"),
    ],
    handler=_handle_renewal,
    redraft=_redraft_renewal,
    audience="sales",
))


def _notify_owners(db: Session, items: list[ReviewQueueItem]) -> None:
    """One "N renewals ready" notification per rep, not one per item."""
    from collections import Counter

    from app.services.notify import create_notification

    per_owner = Counter(i.payload.get("owner_user_id") for i in items if i.payload.get("owner_user_id"))
    for owner_id, n in per_owner.items():
        create_notification(db, uuid.UUID(owner_id), "renewal", f"{n} renewal email{'s' if n != 1 else ''} ready to review",
                            "Drafted from last year's bookings - check, edit and send from the Today page.",
                            "/automations/today", email=False)


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
        queued: list[ReviewQueueItem] = []
        for title in db.scalars(select(SalesTitle).where(SalesTitle.active.is_(True)).order_by(SalesTitle.sort_order)):
            rows, _, _ = renewal_candidates(db, title.id, today.year)
            for r in rows:
                if len(queued) >= max_per_run:
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
                item = queue_renewal(db, title, order, ed, r["total"], r["count"], today.year,
                                     reason="anniversary", due=anniversary, seen=seen, reps=reps)
                if item:
                    queued.append(item)
        _notify_owners(db, queued)
        db.commit()
        logger.info("sor renewal scan: %d renewal(s) queued", len(queued))
    finally:
        db.close()


def start_renewal_pass(db: Session, edition: SalesEdition) -> dict:
    """The spec's "open renewal pass for {title, edition}": everyone who
    advertised in this edition's equivalent last cycle and hasn't booked
    this title again this year gets a renewal draft now, whatever the
    anniversary scan would have done. Anyone already queued this year is
    skipped (same key), so running it twice - or after the scan - never
    double-approaches anyone. Caller commits."""
    from app.sales.analytics import equivalent_editions
    from app.sales.matching import normalise
    from app.sales.renewals import rebooked

    title = db.get(SalesTitle, edition.title_id)
    prev = equivalent_editions(db, [edition]).get(edition.id)
    if not title or not prev:
        raise ValueError("There's no equivalent edition last year to renew from.")
    rows = db.scalars(select(SalesOrder).where(SalesOrder.edition_id == prev.id, SalesOrder.status == BOOKED,
                                               SalesOrder.value_gbp > 0)).all()
    groups: dict[str, list[SalesOrder]] = {}
    for o in rows:
        groups.setdefault(normalise(o.client_name) or o.client_name.strip().lower(), []).append(o)
    seen = set(db.scalars(select(ReviewQueueItem.payload["dedupe_key"].astext).where(ReviewQueueItem.kind == RENEWAL_KIND)).all())
    reps = {r.id: r for r in db.scalars(select(SalesRep))}
    queued: list[ReviewQueueItem] = []
    already_booked = already_queued = 0
    for orders in groups.values():
        last = max(orders, key=lambda o: o.booked_on or date.min)
        if rebooked(db, title.id, edition.year, last.client_name, last.company_id):
            already_booked += 1
            continue
        item = queue_renewal(db, title, last, prev, sum(float(o.value_gbp) for o in orders), len(orders), edition.year,
                             reason=f"renewal pass for {edition.name}", due=edition.edition_date, seen=seen, reps=reps)
        if item:
            queued.append(item)
        else:
            already_queued += 1
    _notify_owners(db, queued)
    return {"previous_edition": _edition_label(db, prev), "advertisers": len(groups), "queued": len(queued),
            "already_booked": already_booked, "already_queued": already_queued}


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
