"""Online booking forms - Matt's email: "some products where customers currently use an online booking form (Jotform
and Stova) from which the salesperson then transfers the information manually to the SOR" (Onboard Awards entries,
The Business Travel People Awards, The Business Travel Quiz).

Each form is set up once in Bookings settings (app/models/deal.py BookingForm): what an entry is, which title and
issue or event it's for, and the price. The form's own web address goes into Jotform (Settings > Integrations >
Webhooks) or Stova; every entry then arrives here as a Review Queue item with the answers laid out and the client
matched to the CRM where possible. "Create booking" makes a confirmed booking from it (the client booked it
themselves), which goes to accounts' check - priced, on the order register
and sent for the accounts check like any other - so nobody types it in twice.

Jotform posts the entry as a form (rawRequest holds the answers as JSON). Anything else (Stova, or a test) can post
plain JSON: {"submission_id": "...", "answers": {"Company": "...", "Email": "...", ...}} or just the answers.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.automations.registry import ExtraField, ReviewAction, ReviewKind, register
from app.models import BookingForm, Company, Contact, Email, ReviewQueueItem, SalesDeal, SalesEdition, SalesRate, SalesRep, SalesTitle

KIND = "online_booking"
MAX_ANSWERS = 60

_GUESS = {
    "company": ("company", "organisation", "organization", "business", "employer", "airline", "agency", "firm"),
    "email": ("email", "e-mail"),
    "name": ("full name", "your name", "contact name", "name"),
    "phone": ("phone", "mobile", "telephone", "tel"),
    "quantity": ("number of", "quantity", "qty", "how many", "tickets", "seats", "places", "entries", "tables"),
    "category": ("category", "award", "entry for"),
}


def _words(key: str) -> str:
    key = re.sub(r"^q\d+_", "", key)
    key = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", key).replace("_", " ").strip()
    return key[:1].upper() + key[1:] if key else key


def _text(v) -> str:
    if isinstance(v, dict):
        return " ".join(_text(x) for x in v.values() if _text(x)).strip()
    if isinstance(v, list):
        return ", ".join(_text(x) for x in v if _text(x))
    return str(v).strip() if v is not None else ""


def parse(content_type: str, raw: bytes, form: dict | None = None) -> tuple[str | None, dict[str, str]]:
    """(submission reference, {question: answer}) from a Jotform post or a plain JSON post."""
    answers: dict[str, str] = {}
    ref = None
    data: dict = {}
    if form:
        data = dict(form)
        ref = data.get("submissionID") or data.get("submission_id")
        if data.get("rawRequest"):
            try:
                inner = json.loads(data["rawRequest"])
            except ValueError:
                inner = {}
            for k, v in inner.items():
                if re.match(r"^q\d+_", k) and _text(v):
                    answers[_words(k)] = _text(v)[:1000]
        if not answers:
            for k, v in data.items():
                if k not in ("formID", "submissionID", "rawRequest", "pretty", "ip", "type", "formTitle") and _text(v):
                    answers[_words(k)] = _text(v)[:1000]
    else:
        try:
            data = json.loads(raw or b"{}")
        except ValueError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        ref = data.get("submission_id") or data.get("submissionID") or data.get("id")
        src = data.get("answers") if isinstance(data.get("answers"), dict) else {k: v for k, v in data.items() if k not in ("submission_id", "submissionID", "id")}
        for k, v in src.items():
            if _text(v):
                answers[_words(str(k))] = _text(v)[:1000]
    return (str(ref)[:120] if ref else None), dict(list(answers.items())[:MAX_ANSWERS])


def guess(answers: dict[str, str]) -> dict[str, str]:
    """Picks out the company, name, email, phone, how many and category from the answers by their questions."""
    out: dict[str, str] = {}
    for field, words in _GUESS.items():
        for q, a in answers.items():
            ql = q.lower()
            if field == "name" and ("company" in ql or "event" in ql or "award" in ql):
                continue
            if any(w in ql for w in words):
                out[field] = a
                break
    if "email" not in out:
        m = next((re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", a) for a in answers.values() if "@" in a), None)
        if m:
            out["email"] = m.group(0)
    if "quantity" in out:
        m = re.search(r"\d+", out["quantity"])
        out["quantity"] = m.group(0) if m else ""
    return {k: v for k, v in out.items() if v}


def _match(db: Session, g: dict[str, str]) -> tuple[Company | None, Contact | None]:
    contact = company = None
    if g.get("email"):
        em = db.scalars(select(Email).where(func.lower(Email.address) == g["email"].lower())).first()
        if em and em.contact_id:
            contact = db.get(Contact, em.contact_id)
            company = db.get(Company, contact.company_id) if contact and contact.company_id else None
        elif em and em.company_id:
            company = db.get(Company, em.company_id)
    if not company and g.get("company"):
        company = db.scalars(select(Company).where(func.lower(Company.name) == g["company"].strip().lower())).first()
    return company, contact


def _what(db: Session, form: BookingForm) -> str:
    from app.api.routes.sales import edition_label

    ed = db.get(SalesEdition, form.edition_id) if form.edition_id else None
    t = db.get(SalesTitle, ed.title_id if ed else form.title_id) if (ed or form.title_id) else None
    where = edition_label(t, ed) if ed and t else (f"{t.name}, issue to be allocated" if t else "no title set")
    price = f", £{float(form.unit_price):,.2f} each" if form.unit_price is not None else ""
    return f"{form.description or form.name} - {where}{price}"


def receive(db: Session, form: BookingForm, ref: str | None, answers: dict[str, str]) -> ReviewQueueItem | None:
    """Queues one entry (once - a resent entry with the same reference is ignored)."""
    if ref and db.scalars(select(ReviewQueueItem.id).where(ReviewQueueItem.kind == KIND, ReviewQueueItem.payload["form_id"].astext == str(form.id),
                                                          ReviewQueueItem.payload["submission_ref"].astext == ref)).first():
        return None
    g = guess(answers)
    company, contact = _match(db, g)
    who = g.get("company") or (company.name if company else None) or g.get("name") or "Someone"
    qty = g.get("quantity")
    details = [{"label": "Form", "value": f"{form.name} ({form.source.capitalize()})"},
               {"label": "Becomes", "value": f"{qty + ' × ' if qty else ''}{_what(db, form)}"}]
    details.append({"label": "CRM company", "value": company.name if company else "Not found in the CRM - check it's a new client",
                    **({"href": f"/companies/{company.id}"} if company else {})})
    if contact:
        details.append({"label": "CRM contact", "value": contact.full_name or g.get("name") or "Contact", "href": f"/contacts/{contact.id}"})
    details += [{"label": q, "value": a} for q, a in answers.items()]
    form.received = (form.received or 0) + 1
    form.last_received_at = datetime.now(timezone.utc)
    title = db.get(SalesTitle, form.title_id) if form.title_id else None
    item = ReviewQueueItem(
        id=uuid.uuid4(), kind=KIND, source_db=title.crm_source_db if title else None, status="pending",
        entity_type="company" if company else None, entity_id=company.id if company else None,
        payload={
            "summary": f"Online booking from {who}: {qty + ' × ' if qty else ''}{form.description or form.name}",
            "details": details,
            "form_id": str(form.id), "submission_ref": ref, "answers": answers, "guess": g,
            "company_id": str(company.id) if company else None, "contact_id": str(contact.id) if contact else None,
            "related_entities": [{"type": "company", "id": str(company.id), "label": company.name}] if company else [],
            "facets": {"form": form.name, "client": "Found in the CRM" if company else "New client"},
            "sort_date": date.today().isoformat(),
            "owner_user_id": None,
        },
    )
    db.add(item)
    return item


def make_booking(db: Session, item: ReviewQueueItem, input_data: dict) -> SalesDeal:
    """A confirmed booking from the entry (the client booked it themselves), through the same path as one made by hand."""
    from fastapi import HTTPException

    from app.api.routes import deals as routes
    from app.automations import order_checks as oc
    from app.sales import accounts as acc
    from app.sales import deals as dl

    form = db.get(BookingForm, uuid.UUID(item.payload["form_id"]))
    if not form:
        raise ValueError("This booking form has been deleted, so there's nothing to book it against.")
    g = item.payload.get("guess") or {}
    raw_qty = (input_data.get("quantity") or g.get("quantity") or "1").strip()
    if not raw_qty.isdigit() or not 1 <= int(raw_qty) <= 999:
        raise ValueError("How many should be a whole number, like 1 or 4.")
    qty = int(raw_qty)
    ed = db.get(SalesEdition, form.edition_id) if form.edition_id else None
    title_id = ed.title_id if ed else form.title_id
    if not title_id:
        raise ValueError(f"The “{form.name}” form isn't linked to a title yet. Set it up in Bookings settings first.")
    rate = db.get(SalesRate, form.rate_id) if form.rate_id else None
    price = float(form.unit_price) if form.unit_price is not None else (float(rate.price_gbp) if rate and rate.price_gbp is not None else None)
    if price is None:
        raise ValueError(f"The “{form.name}” form has no price yet. Add one in Bookings settings first.")
    company = db.get(Company, uuid.UUID(item.payload["company_id"])) if item.payload.get("company_id") else None
    client = (input_data.get("client_name") or "").strip() or g.get("company") or (company.name if company else "") or g.get("name") or ""
    if not client:
        raise ValueError("Type the client's name - the form didn't say who it's for.")
    answers = item.payload.get("answers") or {}
    detail = "; ".join(f"{q}: {a}" for q, a in answers.items() if q.lower().startswith(("category", "award", "entry")))[:1000] or None
    rep = db.get(SalesRep, form.rep_id) if form.rep_id else None
    p = routes.DealIn(
        company_id=company.id if company else None, client_name=client[:256],
        contact_id=uuid.UUID(item.payload["contact_id"]) if item.payload.get("contact_id") else None,
        contact_name=(g.get("name") or None), contact_email=(g.get("email") or None),
        rep_id=rep.id if rep else None, title_id=title_id, status="confirmed",
        notes=f"From the online form “{form.name}”" + (f" (entry {item.payload['submission_ref']})" if item.payload.get("submission_ref") else "") + ".",
        lines=[routes.LineIn(title_id=title_id, rate_id=rate.id if rate else None, description=(form.description or form.name)[:300],
                             detail=detail, qty=1, unit_price=price, list_price=float(rate.price_gbp) if rate and rate.price_gbp is not None else None,
                             placements=[routes.PlacementIn(edition_id=ed.id) if ed else routes.PlacementIn(tba=True) for _ in range(qty)])],
    )
    actor = input_data.get("_actor_user_id")
    who = routes._Who(uuid.UUID(actor) if actor else None)
    d = SalesDeal(id=uuid.uuid4(), number=dl.next_number(db), status="confirmed", created_by_user_id=who.user_uuid, lines=[], split=[],
                  confirmed_at=datetime.now(timezone.utc))
    try:
        routes._apply(db, d, p)
        db.add(d)
        routes._save(db, d, p, who)
    except HTTPException as exc:
        raise ValueError(str(exc.detail)) from exc
    oc.request_check(db, d)
    acc.tell_accounts_new(db, d, who.user_uuid)
    item.payload = {**item.payload, "deal_id": str(d.id),
                    "details": [{"label": "Booking made", "value": f"{d.number} (confirmed)", "href": f"/sales/deals/{d.id}"}, *item.payload["details"]]}
    return d


def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "create":
        make_booking(db, item, input_data)
        return
    if action_id == "not_booking":
        return
    raise ValueError(f"Unknown action {action_id!r} for {KIND}")


register(ReviewKind(
    kind=KIND,
    label="Online bookings",
    description="Entries from online booking forms (Jotform, Stova) - awards entries, event seats, quiz teams - ready to become bookings without retyping.",
    actions=[
        ReviewAction(id="create", label="Create booking", style="primary", outcome="approved", extra_fields=[
            ExtraField(key="client_name", label="Client name, if different from the form", required=False),
            ExtraField(key="quantity", label="How many, if different from the form", placeholder="1", required=False),
        ]),
        ReviewAction(id="not_booking", label="Not a booking", style="secondary", outcome="rejected", requires_note=True),
    ],
    handler=_handle,
    audience="sales",
    facets=(("form", "Form"), ("client", "Client")),
    date_sort_label="date received",
))
