"""Subscription sign-ups from the four website forms (CS-012 registration checks, CS-014 overseas readers).

Clare (27 Oct): Selling Travel and TBTM sign up on Wufoo forms, Onboard Hospitality digital on an Elementor form on
its WordPress site, and OBH print on Stova. Shani and Kay are emailed each one, check it, and add or update the
reader in Act!. Each form now also sends the entry here (Wufoo and Elementor both have a built-in "Webhook"
setting; anything else can post JSON), at its own secret address shown in Automations > Subscription sign-ups.

Every entry becomes one Review Queue card with the checks they do by hand: is this person already on the database
(the "re-subscribe" case), is it a personal email address (worth checking they work in the trade, most of all for
print), and for Selling Travel and TBTM print, is the address outside the UK (print is UK only - offer digital).
"Add to the database" creates the contact in the title's database, optionally in its newsletter group; "Already on
file" and "Skip" change nothing. Nothing is ever emailed to the reader.
"""
from __future__ import annotations

import json
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.automations.group_allowlist import NEWSLETTER_GROUP
from app.automations.registry import ExtraField, ReviewAction, ReviewKind, register
from app.automations.state import get_state, set_state
from app.models import Company, Contact, Email, GroupMembership, Note, ReviewQueueItem

KIND = "subscription_signup"
TOKENS_STATE = "subscription_form_tokens"
MAX_ANSWERS = 60


@dataclass(frozen=True)
class SignupForm:
    key: str
    title: str
    tool: str
    source_db: str
    uk_only_print: bool   # the title only posts print copies to UK addresses


FORMS: dict[str, SignupForm] = {f.key: f for f in (
    SignupForm("selling-travel", "Selling Travel", "Wufoo", "sellingtravel", True),
    SignupForm("tbtm", "The Business Travel Magazine", "Wufoo", "prospects", True),
    SignupForm("obh-digital", "Onboard Hospitality (digital)", "WordPress (Elementor)", "onboard", False),
    SignupForm("obh-print", "Onboard Hospitality (print)", "Stova", "onboard", False),
)}

UK = {"uk", "u.k.", "united kingdom", "great britain", "gb", "england", "scotland", "wales", "northern ireland"}
PERSONAL_DOMAINS = {"gmail.com", "googlemail.com", "hotmail.com", "hotmail.co.uk", "outlook.com", "live.com", "live.co.uk",
                    "yahoo.com", "yahoo.co.uk", "icloud.com", "me.com", "aol.com", "btinternet.com", "sky.com",
                    "virginmedia.com", "msn.com", "protonmail.com", "mail.com", "gmx.com", "talktalk.net"}


# ---- addresses ------------------------------------------------------------------------------------------------

def tokens(db: Session) -> dict[str, str]:
    """Each form's secret (made the first time it's asked for, then kept)."""
    have = get_state(db, TOKENS_STATE)
    missing = {k: secrets.token_urlsafe(24) for k in FORMS if not have.get(k)}
    if missing:
        have = {**have, **missing}
        set_state(db, TOKENS_STATE, have)
    return have


def form_for(db: Session, key: str, token: str) -> SignupForm | None:
    f = FORMS.get(key)
    want = get_state(db, TOKENS_STATE).get(key)
    return f if f and want and secrets.compare_digest(want, token) else None


# ---- reading an entry -----------------------------------------------------------------------------------------

def _clean(v) -> str:
    if isinstance(v, list):
        return ", ".join(_clean(x) for x in v if _clean(x))
    if isinstance(v, dict):
        return " ".join(_clean(x) for x in v.values() if _clean(x)).strip()
    return str(v).strip() if v is not None else ""


def _wufoo(data: dict) -> tuple[str | None, dict[str, str]] | None:
    """Wufoo posts Field1, Field2... and, when "Include Field and Form Structures" is ticked, FieldStructure (the
    question for each FieldN, with SubFields for name and address parts)."""
    if not any(re.fullmatch(r"Field\d+", k) for k in data):
        return None
    titles: dict[str, str] = {}
    try:
        structure = json.loads(data.get("FieldStructure") or "{}")
    except ValueError:
        structure = {}
    for f in (structure.get("Fields") or []) if isinstance(structure, dict) else []:
        title = _clean(f.get("Title")) or f.get("ID")
        subs = f.get("SubFields") or []
        for s in subs:
            if s.get("ID"):
                titles[s["ID"]] = f"{title} ({_clean(s.get('Label'))})" if s.get("Label") else title
        if f.get("ID") and not subs:
            titles[f["ID"]] = title
    answers = {}
    for k in sorted((k for k in data if re.fullmatch(r"Field\d+", k)), key=lambda k: int(k[5:])):
        if _clean(data[k]):
            answers[titles.get(k, k)] = _clean(data[k])[:1000]
    return _clean(data.get("EntryId")) or None, answers


def _elementor(data: dict) -> tuple[str | None, dict[str, str]] | None:
    """Elementor posts each question by its label, plus form_id and form_name; with "Advanced data" on it sends
    fields[<id>][title] and fields[<id>][value] instead."""
    adv: dict[str, dict] = {}
    for k, v in data.items():
        m = re.fullmatch(r"fields\[([^\]]+)\]\[(title|value|raw_value)\]", k)
        if m:
            adv.setdefault(m[1], {})[m[2]] = v
    if adv:
        answers = {(_clean(f.get("title")) or fid): _clean(f.get("value") or f.get("raw_value"))[:1000] for fid, f in adv.items()}
        return None, {q: a for q, a in answers.items() if a}
    if "form_id" in data or "form_name" in data:
        skip = {"form_id", "form_name"}
        return None, {k: _clean(v)[:1000] for k, v in data.items() if k not in skip and not k.startswith(("form[", "meta[")) and _clean(v)}
    return None


def parse(content_type: str, raw: bytes, form: dict | None = None) -> tuple[str | None, dict[str, str]]:
    """(entry reference, {question: answer}) from a Wufoo or Elementor post, or plain JSON (Stova, a test)."""
    if form:
        for reader in (_wufoo, _elementor):
            got = reader(form)
            if got:
                ref, answers = got
                return ref, dict(list(answers.items())[:MAX_ANSWERS])
        # anything else, e.g. Stova's API Registration Trigger: AttendeeID, EventID, Scenario, and with "include
        # attendee details" on, First Name, Last Name, Email, Category and Sub Category
        if form.get("AWT"):
            return None, {}   # a signed (JWT) Stova message - turn "Sign Payload" off for this address
        ref = form.get("AttendeeID") or form.get("EntryId") or form.get("submission_id")
        skip = {"AttendeeID", "EventID", "Scenario"}
        return (_clean(ref) or None), {k: _clean(v)[:1000] for k, v in list(form.items())[:MAX_ANSWERS] if k not in skip and _clean(v)}
    try:
        data = json.loads(raw or b"{}")
    except ValueError:
        return None, {}
    if not isinstance(data, dict):
        return None, {}
    if isinstance(data.get("fields"), dict):   # Elementor's advanced data sent as JSON
        answers = {(_clean(f.get("title")) if isinstance(f, dict) else "") or str(k): _clean(f.get("value") if isinstance(f, dict) else f)
                   for k, f in data["fields"].items()}
        return None, {q: a[:1000] for q, a in answers.items() if a}
    ref = data.get("entry_id") or data.get("submission_id") or data.get("id")
    src = data.get("answers") if isinstance(data.get("answers"), dict) else {k: v for k, v in data.items() if k not in ("entry_id", "submission_id", "id")}
    answers = {str(k): _clean(v)[:1000] for k, v in src.items() if _clean(v)}
    return (_clean(ref) or None), dict(list(answers.items())[:MAX_ANSWERS])


_GUESS = {
    "email": ("email", "e-mail"),
    "first": ("first name", "forename", "name (first)"),
    "last": ("last name", "surname", "family name", "name (last)"),
    "name": ("full name", "your name", "name"),
    "company": ("company", "organisation", "organization", "employer", "business name", "agency", "airline"),
    "job_title": ("job title", "position", "role", "job"),
    "country": ("country",),
    "postcode": ("postcode", "post code", "zip", "postal"),
    "edition": ("print", "digital", "format", "edition", "copy"),
}


def guess(answers: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for field, words in _GUESS.items():
        for q, a in answers.items():
            ql = q.lower()
            if field == "name" and any(w in ql for w in ("company", "first", "last", "surname", "business")):
                continue
            if any(w in ql for w in words):
                out.setdefault(field, a)
    if "email" not in out:
        m = next((re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", a) for a in answers.values() if "@" in a), None)
        if m:
            out["email"] = m.group(0)
    if not out.get("name"):
        out["name"] = " ".join(x for x in (out.get("first"), out.get("last")) if x)
    return {k: v.strip() for k, v in out.items() if v and v.strip()}


def wants_print(f: SignupForm, answers: dict[str, str]) -> bool:
    if f.key == "obh-print":
        return True
    if f.key == "obh-digital":
        return False
    return any("print" in f"{q} {a}".lower() for q, a in answers.items())


def checks(db: Session, f: SignupForm, g: dict[str, str], answers: dict[str, str]) -> tuple[Contact | None, list[str]]:
    """(the contact already on the database, if any, and what's worth checking - in plain words)."""
    notes: list[str] = []
    contact = None
    email = (g.get("email") or "").lower()
    if not email:
        notes.append("No email address on the entry.")
    else:
        em = db.scalars(select(Email).where(func.lower(Email.address) == email, Email.contact_id.isnot(None))).first()
        contact = db.get(Contact, em.contact_id) if em else None
        if contact:
            notes.append(f"Already on the database as {contact.full_name or email} - they may be re-subscribing. Check what they already get.")
        if email.split("@")[-1] in PERSONAL_DOMAINS:
            notes.append("Personal email address - check they work in the trade" + (", as they want a printed copy." if wants_print(f, answers) else "."))
    country = (g.get("country") or "").strip().lower()
    if f.uk_only_print and wants_print(f, answers) and country and country not in UK:
        notes.append(f"Overseas address ({g['country']}) asking for print: {f.title} only posts to UK addresses - offer the digital edition.")
    return contact, notes


def receive(db: Session, f: SignupForm, ref: str | None, answers: dict[str, str]) -> ReviewQueueItem | None:
    """One card per entry (a re-sent entry with the same reference is ignored)."""
    if ref and db.scalars(select(ReviewQueueItem.id).where(ReviewQueueItem.kind == KIND, ReviewQueueItem.payload["form"].astext == f.key,
                                                          ReviewQueueItem.payload["entry_ref"].astext == ref)).first():
        return None
    g = guess(answers)
    contact, notes = checks(db, f, g, answers)
    who = g.get("name") or g.get("email") or "Someone"
    details = [{"label": "Form", "value": f"{f.title} sign-up ({f.tool})"}]
    if contact:
        details.append({"label": "On the database", "value": contact.full_name or g.get("email", ""), "href": f"/contacts/{contact.id}"})
    details += [{"label": "Check", "value": n} for n in notes]
    details += [{"label": q, "value": a} for q, a in answers.items()]
    check = ("Already on the database" if contact else "Overseas, print" if any(n.startswith("Overseas") for n in notes)
             else "Check they're in the trade" if any(n.startswith("Personal") for n in notes)
             else "Missing email" if not g.get("email") else "Looks fine")
    item = ReviewQueueItem(
        id=uuid.uuid4(), kind=KIND, source_db=f.source_db, status="pending",
        entity_type="contact" if contact else None, entity_id=contact.id if contact else None,
        payload={
            "summary": f"New {f.title} sign-up: {who}" + (f" ({g['company']})" if g.get("company") else ""),
            "details": details, "form": f.key, "entry_ref": ref, "answers": answers, "guess": g, "checks": notes,
            "contact_id": str(contact.id) if contact else None,
            "related_entities": [{"type": "contact", "id": str(contact.id), "label": contact.full_name or "Contact"}] if contact else [],
            "facets": {"form": f.title, "check": check},
            "sort_date": date.today().isoformat(),
            "field_defaults": {"name": g.get("name", ""), "email": g.get("email", ""), "company_name": g.get("company", ""),
                               "job_title": g.get("job_title", ""), "newsletter": "true"},
        },
    )
    db.add(item)
    return item


# ---- the card's buttons ---------------------------------------------------------------------------------------

def _add(db: Session, item: ReviewQueueItem, input_data: dict) -> None:
    from app.automations.inbound_capture import _find_group, _find_or_create_company

    f = FORMS.get(item.payload.get("form") or "")
    if not f:
        raise ValueError("This card doesn't say which form it came from, so it can't be added.")
    g = item.payload.get("guess") or {}
    email = (input_data.get("email") or g.get("email") or "").strip()
    name = (input_data.get("name") or g.get("name") or "").strip()
    if not name:
        raise ValueError("Type their name - the form didn't give one.")
    if email and db.scalars(select(Email.id).where(func.lower(Email.address) == email.lower(), Email.contact_id.isnot(None))).first():
        raise ValueError("Someone with that email address is already on the database. Use Already on file instead.")
    company_name = (input_data.get("company_name") or g.get("company") or "").strip()
    company = _find_or_create_company(db, f.source_db, company_name) if company_name else None
    parts = name.split(maxsplit=1)
    contact = Contact(id=uuid.uuid4(), source_db=f.source_db, source_act_id=str(uuid.uuid4()), first_name=parts[0],
                      last_name=parts[1] if len(parts) > 1 else None, full_name=name,
                      job_title=(input_data.get("job_title") or g.get("job_title") or "").strip() or None,
                      company_id=company.id if company else None, custom_fields={})
    db.add(contact)
    db.flush()
    if email:
        db.add(Email(id=uuid.uuid4(), source_db=f.source_db, source_act_id=str(uuid.uuid4()), contact_id=contact.id,
                     type_label="Business", address=email, is_primary=True))
    if (input_data.get("newsletter") or "").lower() == "true":
        group = _find_group(db, f.source_db, NEWSLETTER_GROUP.get(f.source_db, ""))
        if group:
            db.add(GroupMembership(id=uuid.uuid4(), group_id=group.id, contact_id=contact.id))
    answers = "\n".join(f"{q}: {a}" for q, a in (item.payload.get("answers") or {}).items())
    db.add(Note(id=uuid.uuid4(), source_db=f.source_db, source_act_id=str(uuid.uuid4()), entity_type="contact", entity_id=contact.id,
                note_type="Subscription", body=f"Signed up on the {f.title} form ({f.tool}).\n\n{answers}",
                act_created_at=datetime.now(timezone.utc)))
    item.entity_type, item.entity_id = "contact", contact.id
    item.payload = {**item.payload, "contact_id": str(contact.id),
                    "details": [{"label": "Added", "value": name, "href": f"/contacts/{contact.id}"}, *item.payload["details"]]}


def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "add":
        _add(db, item, input_data)
        return
    if action_id in ("on_file", "skip"):
        return
    raise ValueError("That button isn't available on this card.")


register(ReviewKind(
    kind=KIND,
    label="Subscription sign-ups",
    description="New sign-ups from the Selling Travel, TBTM and Onboard Hospitality subscribe forms, checked for people already on the database, personal email addresses and overseas print requests.",
    actions=[
        ReviewAction(id="add", label="Add to the database", style="primary", outcome="approved", extra_fields=[
            ExtraField(key="name", label="Name"),
            ExtraField(key="email", label="Email", required=False),
            ExtraField(key="company_name", label="Company", required=False),
            ExtraField(key="job_title", label="Job title", required=False),
            ExtraField(key="newsletter", label="Add to the title's newsletter group", field_type="bool"),
        ]),
        ReviewAction(id="on_file", label="Already on file", style="secondary", outcome="approved"),
        ReviewAction(id="skip", label="Skip", style="secondary", outcome="dismissed", reopenable=True, requires_note=True),
    ],
    handler=_handle,
    audience="admin",
    facets=(("form", "Form"), ("check", "Check")),
    date_sort_label="date received",
))
