"""CS-013 - subscription changes: readers emailing to unsubscribe, subscribe, change their address or details, switch
between print and digital, or asking a question about their copy - read from the subscriptions inbox and put in the
Review Queue for the data team. Nothing changes on a record, and nothing is sent, until someone presses the card's button.

How an email gets here, cheapest first:
  1. It's in one of the inboxes listed in "Subscription changes > Inboxes to read" (e.g. enquiries@).
  2. Not an automatic message, bounce, out-of-office or newsletter, and not from a colleague (unless they're passing
     a reader's email on).
  3. It mentions a subscription, the magazine, a copy, an address, unsubscribing... (a keyword check, free).
  4. The Brain reads it and says what kind of change it is, which title, and the new details. Without the Brain only
     plain "unsubscribe" or "remove me" emails are queued, marked as unchecked.

Two kinds of card:
  - subscription_change: the change, with a button that makes it on the reader's record (each logged in the field
    history and as a note). An unsubscribe is made in Brevo too, where the newsletters go out from, once Brevo is
    connected (app/automations/brevo_sync.py); the card says what happened there.
  - reader_query: a question about their copy or subscription, with a reply drafted to edit and send from Outlook.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.automations.group_allowlist import NEWSLETTER_GROUP
from app.automations.mail_parsing import ParsedMessage, looks_like_bounce, looks_like_ooo, parse_message
from app.automations.registry import ExtraField, ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.automations.sender_patterns import contains_unsubscribe_text, is_automated_sender
from app.automations.state import get_state, set_state
from app.db.session import SessionLocal
from app.models import Address, Company, Contact, Email, Group, GroupMembership, Note, ReviewQueueItem

logger = logging.getLogger("app.automations.subscription_changes")

KIND = "subscription_change"
QUERY_KIND = "reader_query"

CHANGES = {"unsubscribe": "Unsubscribe", "subscribe": "Subscribe", "change_address": "Change of address",
           "change_details": "Change of details", "change_title": "Change of title", "format": "Print or digital"}
# Which button leads on each change; the other change buttons are hidden on that card.
ACTION_FOR = {"unsubscribe": "unsubscribe", "subscribe": "subscribe", "change_address": "update_address",
              "change_details": "update_details", "change_title": "noted", "format": "noted"}
CHANGE_ACTIONS = ("unsubscribe", "subscribe", "update_address", "update_details")

# The titles and the database each one's readers are in.
TITLES = (("sellingtravel", "Selling Travel", re.compile(r"selling\s*travel", re.I)),
          ("prospects", "The Business Travel Magazine", re.compile(r"business\s*travel\s*mag|\btbtm\b", re.I)),
          ("onboard", "Onboard Hospitality", re.compile(r"on\s*board\s*hospitality|\bobh\b", re.I)))
TITLE_NAME = {k: n for k, n, _ in TITLES}

_KEYWORDS = re.compile(r"\b(un-?subscri\w*|subscri\w*|opt(ed)? out|remove (me|us|my)|take (me|us) off|stop (sending|receiving)|"
                       r"no longer (wish|want|work)|mailing list|newsletter|magazine|cop(y|ies)|issue|print(ed)?|digital|"
                       r"e-?edition|moved|new address|change of address|delivery|deliver\w*|post(ed|al)?)\b", re.I)
_PLAIN_UNSUB = re.compile(r"\b(un-?subscribe|remove me|take me off|opt me out|stop sending)\b", re.I)
_FORWARDED = re.compile(r"(-{2,}\s*forwarded message|^from:\s.+$|passed (this|it) on|forwarding (this|on))", re.I | re.M)

_PROMPT = (
    "You read one email that arrived in the subscriptions inbox of BMI Publishing, a UK publisher of travel-trade "
    "magazines (Selling Travel, The Business Travel Magazine, Onboard Hospitality) and their newsletters. Decide whether "
    "a reader is asking about their subscription. Return JSON: {\"kind\": one of unsubscribe|subscribe|change_address|"
    "change_details|change_title|format|reader_query|none, \"magazine\": Selling Travel|The Business Travel Magazine|"
    "Onboard Hospitality|null, \"everything\": true only if they want to stop everything from BMI, \"reader_email\": the "
    "reader's address (for a passed-on email, the original sender's), \"reader_name\": their name, "
    "\"new_address\": {\"line1\", \"line2\", \"city\", \"postcode\", \"country\"} or null, \"new_details\": {\"name\", "
    "\"job_title\", \"company\", \"email\"} with only what changes, or null, \"new_title\": the title they want instead, "
    "or null, \"format\": print|digital|null (what they want now), \"summary\": one plain sentence}. "
    "unsubscribe = stop receiving; subscribe = start receiving; change_details = new job, name, company or email; "
    "change_title = swap one magazine for another; format = switch between print and digital; reader_query = a "
    "question or problem about their copy (not arrived, damaged, missing issue, how to read online). An advertiser, a "
    "PR pitch, a supplier, an invoice or anything else is none. Never invent a value - use null."
)

_REPLY_PROMPT = (
    "Write a short, friendly reply from BMI Publishing's subscriptions team to the reader's email below. Thank them, "
    "answer in their own terms, and say what happens next. If it needs looking into, say we're checking and will come "
    "back to them. No prices, dates or promises you can't be sure of. British English, plain text, no sign-off line."
)

QUERY_FALLBACK = ("Thank you for getting in touch about your copy of {title}. We're looking into this and will come back to "
                  "you shortly.")


# ---- reading the inbox --------------------------------------------------------------------------------

def candidate(msg: ParsedMessage, mailbox: str, domains: set[str]) -> bool:
    """The free checks, before any Brain."""
    sender = (msg.from_address or "").lower()
    if not sender or sender == mailbox.lower() or is_automated_sender(sender):
        return False
    if looks_like_bounce(msg) or looks_like_ooo(msg) or msg.headers.get("list-unsubscribe"):
        return False
    if sender.split("@")[-1] in domains and not _FORWARDED.search(msg.body_text or ""):
        return False   # internal chat, unless a colleague is passing a reader's email on
    body = msg.body_text or ""
    # a reader's reply quotes the newsletter's own "unsubscribe" footer; only their own words count
    own = body.split("\n>", 1)[0] if contains_unsubscribe_text(body) else body
    return bool(_KEYWORDS.search(f"{msg.subject}\n{own}"))


def classify(msg: ParsedMessage) -> dict | None:
    from app.automations.llm import extract_json, is_configured

    if not is_configured():
        if not _PLAIN_UNSUB.search(f"{msg.subject}\n{(msg.body_text or '')[:1500]}"):
            return None
        return {"kind": "unsubscribe", "magazine": None, "everything": False, "reader_email": msg.from_address,
                "reader_name": msg.from_name, "summary": "Asks to unsubscribe - picked up from the words used, not checked by the Brain.",
                "unchecked": True}
    out = extract_json(_PROMPT, f"From: {msg.from_name or ''} <{msg.from_address}>\nSubject: {msg.subject}\n\n{(msg.body_text or '')[:6000]}",
                       max_tokens=500, purpose="subscription_changes.classify")
    if not isinstance(out, dict) or out.get("kind") not in (*CHANGES, "reader_query"):
        return None
    return out


def title_key(magazine: str | None) -> str | None:
    return next((k for k, _, rx in TITLES if magazine and rx.search(magazine)), None)


def find_reader(db: Session, email: str | None, source_db: str | None) -> Contact | None:
    """The reader's record: the one with this email in the title's database, or the only one anywhere."""
    if not email:
        return None
    found = list(db.scalars(select(Contact).join(Email, Email.contact_id == Contact.id)
                            .where(func.lower(Email.address) == email.strip().lower()).distinct()))
    if source_db:
        in_db = [c for c in found if c.source_db == source_db]
        if len(in_db) == 1:
            return in_db[0]
    return found[0] if len(found) == 1 else None


def _addr_text(a: dict | None) -> str:
    return ", ".join(str(a[k]).strip() for k in ("line1", "line2", "city", "postcode", "country") if a and a.get(k))


def _details(db: Session, info: dict, msg: ParsedMessage, contact: Contact | None, key: str | None) -> list[dict]:
    reader = info.get("reader_email") or msg.from_address
    d = [{"label": "From", "value": " ".join(x for x in (info.get("reader_name") or msg.from_name, f"<{reader}>") if x)},
         {"label": "On the database", "value": contact.full_name or reader, "href": f"/contacts/{contact.id}"} if contact
         else {"label": "On the database", "value": "Not found by this email address - type the one on their record below"},
         {"label": "Subject", "value": msg.subject or "(no subject)"},
         {"label": "Magazine", "value": TITLE_NAME.get(key, "Not said")}]
    company = db.get(Company, contact.company_id) if contact and contact.company_id else None
    if company:
        d.append({"label": "Company", "value": company.name, "href": f"/companies/{company.id}"})
    if info.get("summary"):
        d.append({"label": "In short", "value": info["summary"]})
    if _addr_text(info.get("new_address")):
        d.append({"label": "New address", "value": _addr_text(info["new_address"])})
    nd = {k: v for k, v in (info.get("new_details") or {}).items() if v}
    for k, label in (("name", "New name"), ("job_title", "New job title"), ("company", "New company"), ("email", "New email")):
        if nd.get(k):
            d.append({"label": label, "value": str(nd[k])})
    if info.get("new_title"):
        d.append({"label": "Wants instead", "value": str(info["new_title"])})
    if info.get("format"):
        d.append({"label": "Wants", "value": "The printed magazine" if info["format"] == "print" else "The digital edition"})
    if info.get("unchecked"):
        d.append({"label": "Worth knowing", "value": "The Brain isn't switched on, so this was picked up from the words used. Check it really is a request to unsubscribe."})
    return d


def queue(db: Session, mailbox: str, msg: ParsedMessage, info: dict) -> ReviewQueueItem:
    kind = info["kind"]
    key = title_key(info.get("magazine"))
    reader = (info.get("reader_email") or msg.from_address or "").strip()
    contact = find_reader(db, reader, key)
    key = key or (contact.source_db if contact and contact.source_db in TITLE_NAME else None)
    who = info.get("reader_name") or msg.from_name or reader
    received = msg.received_at
    email_text = f"From: {msg.from_name or ''} <{msg.from_address}>\nSubject: {msg.subject}\n\n{(msg.body_text or '')[:4000]}"
    base = {
        "details": _details(db, info, msg, contact, key), "mailbox": mailbox, "message_id": msg.message_id,
        "conversation_id": msg.conversation_id, "title_key": key, "reader_email": reader, "request": info,
        "contact_id": str(contact.id) if contact else None,
        "related_entities": [{"type": "contact", "id": str(contact.id), "label": contact.full_name or reader}] if contact else [],
        "sort_date": received.date().isoformat() if received else date.today().isoformat(),
    }
    if kind == "reader_query":
        payload = {**base, "summary": f"{who} has a question about {TITLE_NAME.get(key, 'their copy')}",
                   "original_text": draft_reply(msg, key), "original_label": "Drafted reply", "source_context": email_text,
                   "suggested_to": reader,
                   "facets": {"magazine": TITLE_NAME.get(key, "Not said"), "record": "On the database" if contact else "Not found"}}
        q_kind = QUERY_KIND
    else:
        lead = ACTION_FOR[kind]
        a = info.get("new_address") or {}
        nd = info.get("new_details") or {}
        payload = {**base, "summary": f"{CHANGES[kind]}: {who}" + (f" ({TITLE_NAME[key]})" if key else ""),
                   "original_text": email_text, "original_label": "Their email",
                   "primary_action": lead, "hidden_actions": [x for x in CHANGE_ACTIONS if x != lead],
                   "field_defaults": {"email": reader, "everything": "true" if info.get("everything") else "false",
                                      "name": nd.get("name") or info.get("reader_name") or msg.from_name or "",
                                      "line1": a.get("line1") or "", "line2": a.get("line2") or "", "city": a.get("city") or "",
                                      "postcode": a.get("postcode") or "", "country": a.get("country") or "",
                                      "job_title": nd.get("job_title") or "", "company_name": nd.get("company") or "",
                                      "new_email": nd.get("email") or ""},
                   "facets": {"change": CHANGES[kind], "magazine": TITLE_NAME.get(key, "Not said"),
                              "record": "On the database" if contact else "Not found"}}
        q_kind = KIND
    item = ReviewQueueItem(id=uuid.uuid4(), kind=q_kind, source_db=key, status="pending",
                           entity_type="contact" if contact else None, entity_id=contact.id if contact else None, payload=payload)
    db.add(item)
    return item


def draft_reply(msg: ParsedMessage, key: str | None, extra: str = "") -> str:
    from app.automations.llm import draft_text, is_configured

    title = TITLE_NAME.get(key, "our magazine")
    first = (msg.from_name or "").split(" ")[0] if msg.from_name and "@" not in msg.from_name else "there"
    plain_subject = re.sub(r"^((re|fw|fwd):\s*)+", "", msg.subject or "", flags=re.I)
    body = QUERY_FALLBACK.format(title=title)
    if is_configured():
        ask = f"{extra}\n\n" if extra else ""
        got = draft_text(_REPLY_PROMPT, f"{ask}THE READER'S EMAIL:\n{(msg.body_text or '')[:4000]}", max_tokens=300,
                         purpose="subscription_changes.reply")
        if got and len(got) < 1500:
            body = got.strip()
    return f"Subject: RE: {plain_subject}".strip() + f"\n\nDear {first},\n\n{body}\n\nKind regards,"


def scan() -> None:
    from app.graph_client import GraphRequestError, list_messages_since

    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        boxes = runtime_settings.get_csv(db, "subscription_change_mailboxes")
        if not boxes:
            logger.info("subscription changes: no inboxes listed - nothing to read")
            return
        domains = {d.strip().lower() for d in runtime_settings.get_csv(db, "email_summary_internal_domains")}
        cap = runtime_settings.get_int(db, "subscription_change_llm_max_per_run")
        used = 0
        seen = {r[0] for r in db.execute(select(ReviewQueueItem.payload["message_id"].astext)
                                         .where(ReviewQueueItem.kind.in_((KIND, QUERY_KIND)))) if r[0]}
        for box in boxes:
            key = f"subscription_changes:{box.lower()}"
            st = get_state(db, key)
            since = datetime.fromisoformat(st["last_processed_at"]) if st.get("last_processed_at") else \
                now - timedelta(minutes=runtime_settings.get_int(db, "subscription_change_lookback_minutes"))
            try:
                raw = list_messages_since(box, since.strftime("%Y-%m-%dT%H:%M:%SZ"))
            except GraphRequestError as exc:
                logger.error("subscription changes: inbox %s couldn't be read (HTTP %s)", box, exc.status_code)
                continue
            skip = set(st.get("last_message_ids", []))
            msgs = sorted((parse_message(m) for m in raw if m.get("id") not in skip), key=lambda m: m.received_at)
            done_upto, queued = None, 0
            for msg in msgs:
                if msg.message_id in seen or not candidate(msg, box, domains):
                    done_upto = msg
                    continue
                if used >= cap:
                    break
                used += 1
                info = classify(msg)
                done_upto = msg
                if info and info.get("kind") != "none":
                    queue(db, box, msg, info)
                    seen.add(msg.message_id)
                    queued += 1
            if done_upto:
                set_state(db, key, {"last_processed_at": done_upto.received_at.isoformat(), "last_message_ids": [done_upto.message_id]})
            db.commit()
            logger.info("subscription changes: %s - %d read, %d queued", box, len(msgs), queued)
    finally:
        db.close()


# ---- the card's buttons ---------------------------------------------------------------------------------

def _actor(input_data: dict) -> uuid.UUID | None:
    a = input_data.get("_actor_user_id")
    return uuid.UUID(a) if a else None


def _reader(db: Session, item: ReviewQueueItem, input_data: dict) -> Contact:
    p = item.payload
    email = (input_data.get("email") or p.get("reader_email") or "").strip()
    same = email.lower() == (p.get("reader_email") or "").lower()
    contact = db.get(Contact, uuid.UUID(p["contact_id"])) if same and p.get("contact_id") else find_reader(db, email, p.get("title_key"))
    if not contact:
        raise ValueError("No one on the database has that email address (or more than one does). Type the address on their record, or open the contact and change it there.")
    return contact


def _note(db: Session, contact: Contact, body: str, actor: uuid.UUID | None) -> None:
    db.add(Note(id=uuid.uuid4(), source_db=contact.source_db, source_act_id=str(uuid.uuid4()), entity_type="contact",
                entity_id=contact.id, note_type="Subscription", body=body, act_created_at=datetime.now(timezone.utc),
                created_by_user_id=actor))


def _done(item: ReviewQueueItem, contact: Contact, value: str) -> None:
    item.entity_type, item.entity_id = "contact", contact.id
    item.payload = {**item.payload, "contact_id": str(contact.id),
                    "details": [{"label": "Done", "value": value, "href": f"/contacts/{contact.id}"}, *item.payload["details"]]}


def _newsletter_group(db: Session, source_db: str) -> Group | None:
    name = NEWSLETTER_GROUP.get(source_db)
    return db.scalars(select(Group).where(Group.source_db == source_db, func.lower(Group.name) == name.lower())).first() if name else None


def _unsubscribe(db: Session, item: ReviewQueueItem, input_data: dict) -> None:
    from app.services.field_audit import record_field_changes

    actor = _actor(input_data)
    everything = (input_data.get("everything") or "").lower() == "true"
    if everything:
        # every record with their address, in every title's database (one per title is normal, so no single match is needed)
        p = item.payload
        email = (input_data.get("email") or p.get("reader_email") or "").strip().lower()
        people = {c.id: c for c in db.scalars(select(Contact).join(Email, Email.contact_id == Contact.id)
                                              .where(func.lower(Email.address) == email))} if email else {}
        if not people and p.get("contact_id") and email == (p.get("reader_email") or "").lower():
            c = db.get(Contact, uuid.UUID(p["contact_id"]))
            people = {c.id: c} if c else {}
        if not people:
            raise ValueError("No one on the database has that email address. Type the address on their record, or open the contact and change it there.")
        contact = next(iter(people.values()))
        for c in people.values():
            if not c.is_unsubscribed:
                record_field_changes(db, entity_type="contact", entity_id=c.id, before={"is_unsubscribed": False},
                                     updates={"is_unsubscribed": True}, changed_by_user_id=actor)
                c.is_unsubscribed = True
            group = _newsletter_group(db, c.source_db)
            if group:
                db.execute(delete(GroupMembership).where(GroupMembership.group_id == group.id, GroupMembership.contact_id == c.id))
            _note(db, c, "Asked to stop everything from BMI - unsubscribed from every title (from their email to the subscriptions inbox).", actor)
        _done(item, contact, f"Unsubscribed from everything ({len(people)} record{'s' if len(people) != 1 else ''})")
        _brevo(db, item, list(people.values()), everything=True, source_db=None)
        return
    contact = _reader(db, item, input_data)
    key = item.payload.get("title_key") or contact.source_db
    group = _newsletter_group(db, contact.source_db)
    removed = db.execute(delete(GroupMembership).where(GroupMembership.group_id == group.id, GroupMembership.contact_id == contact.id)).rowcount if group else 0
    title = TITLE_NAME.get(key, "this title")
    _note(db, contact, f"Asked to unsubscribe from {title}" + (f" - taken off the {group.name} group." if removed else " - they weren't in its newsletter group.")
          + " (From their email to the subscriptions inbox.)", actor)
    _done(item, contact, f"Unsubscribed from {title}")
    _brevo(db, item, [contact], everything=False, source_db=contact.source_db)


def _brevo(db: Session, item: ReviewQueueItem, contacts: list[Contact], *, everything: bool, source_db: str | None) -> None:
    """The same unsubscribe in Brevo, where the newsletters go out from (app/automations/brevo_sync.py)."""
    from app.automations.brevo_sync import push_unsubscribe
    line = push_unsubscribe(db, contacts, everything=everything, source_db=source_db)
    details = item.payload["details"]
    item.payload = {**item.payload, "details": [details[0], {"label": "Brevo", "value": line}, *details[1:]]}


def _subscribe(db: Session, item: ReviewQueueItem, input_data: dict) -> None:
    p = item.payload
    actor = _actor(input_data)
    key = p.get("title_key")
    email = (input_data.get("email") or p.get("reader_email") or "").strip()
    contact = find_reader(db, email, key)
    if contact and key and contact.source_db != key:
        contact = None   # they're only in another title's database
    if not contact:
        if not key:
            raise ValueError("The email doesn't say which magazine they want. Add them from the contact page instead.")
        name = (input_data.get("name") or "").strip()
        if not name:
            raise ValueError("Type their name - they're not on this title's database yet, so they'll be added.")
        parts = name.split(maxsplit=1)
        contact = Contact(id=uuid.uuid4(), source_db=key, source_act_id=str(uuid.uuid4()), first_name=parts[0],
                          last_name=parts[1] if len(parts) > 1 else None, full_name=name, custom_fields={})
        db.add(contact)
        db.flush()
        if email:
            db.add(Email(id=uuid.uuid4(), source_db=key, source_act_id=str(uuid.uuid4()), contact_id=contact.id,
                         type_label="Business", address=email, is_primary=True))
    group = _newsletter_group(db, contact.source_db)
    if group and not db.scalars(select(GroupMembership.id).where(GroupMembership.group_id == group.id, GroupMembership.contact_id == contact.id)).first():
        db.add(GroupMembership(id=uuid.uuid4(), group_id=group.id, contact_id=contact.id))
    if contact.is_unsubscribed:
        from app.services.field_audit import record_field_changes
        record_field_changes(db, entity_type="contact", entity_id=contact.id, before={"is_unsubscribed": True},
                             updates={"is_unsubscribed": False}, changed_by_user_id=actor)
        contact.is_unsubscribed = False
    title = TITLE_NAME.get(contact.source_db, "the title")
    _note(db, contact, f"Asked to subscribe to {title} (from their email to the subscriptions inbox)." + (f" Added to the {group.name} group." if group else ""), actor)
    _done(item, contact, f"Subscribed to {title}")


def _update_address(db: Session, item: ReviewQueueItem, input_data: dict) -> None:
    from app.services.field_audit import record_field_changes

    contact = _reader(db, item, input_data)
    new = {k: (input_data.get(f) or "").strip() or None
           for k, f in (("line1", "line1"), ("line2", "line2"), ("city", "city"), ("postal_code", "postcode"), ("country", "country"))}
    if not new["line1"] and not new["postal_code"]:
        raise ValueError("Type at least the first line of the new address or its postcode.")
    addr = db.scalars(select(Address).where(Address.contact_id == contact.id).order_by(Address.is_primary.desc())).first()
    if not addr:
        addr = Address(id=uuid.uuid4(), source_db=contact.source_db, source_act_id=str(uuid.uuid4()), contact_id=contact.id,
                       type_label="Business", is_primary=True)
        db.add(addr)
        before = {f"address_{k}": None for k in new}
    else:
        before = {f"address_{k}": getattr(addr, k) for k in new}
    for k, v in new.items():
        setattr(addr, k, v)
    record_field_changes(db, entity_type="contact", entity_id=contact.id, before=before,
                         updates={f"address_{k}": v for k, v in new.items()}, changed_by_user_id=_actor(input_data))
    old = ", ".join(str(v) for v in before.values() if v) or "none on file"
    _note(db, contact, f"New address from their email to the subscriptions inbox: {_addr_text({**new, 'postcode': new['postal_code']})} (was: {old}).", _actor(input_data))
    _done(item, contact, "Address updated")


def _update_details(db: Session, item: ReviewQueueItem, input_data: dict) -> None:
    from app.automations.inbound_capture import _find_or_create_company
    from app.services.field_audit import record_field_changes

    contact = _reader(db, item, input_data)
    actor = _actor(input_data)
    updates: dict = {}
    name = (input_data.get("name") or "").strip()
    if name and name != (contact.full_name or ""):
        parts = name.split(maxsplit=1)
        updates.update(first_name=parts[0], last_name=parts[1] if len(parts) > 1 else None, full_name=name)
    job = (input_data.get("job_title") or "").strip()
    if job and job != (contact.job_title or ""):
        updates["job_title"] = job
    company = (input_data.get("company_name") or "").strip()
    if company:
        co = _find_or_create_company(db, contact.source_db, company)
        if co.id != contact.company_id:
            updates["company_id"] = co.id
    new_email = (input_data.get("new_email") or "").strip()
    if new_email and not re.fullmatch(r"[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+", new_email):
        raise ValueError("The new email address doesn't look right - check it and try again.")
    if not updates and not new_email:
        raise ValueError("Nothing to change - type the new details first.")
    before = {k: getattr(contact, k) for k in updates}
    for k, v in updates.items():
        setattr(contact, k, v)
    if updates:
        record_field_changes(db, entity_type="contact", entity_id=contact.id, before=before, updates=updates, changed_by_user_id=actor)
    if new_email:
        em = db.scalars(select(Email).where(Email.contact_id == contact.id).order_by(Email.is_primary.desc())).first()
        old = em.address if em else None
        if em:
            em.address = new_email
        else:
            db.add(Email(id=uuid.uuid4(), source_db=contact.source_db, source_act_id=str(uuid.uuid4()), contact_id=contact.id,
                         type_label="Business", address=new_email, is_primary=True))
        record_field_changes(db, entity_type="contact", entity_id=contact.id, before={"email": old}, updates={"email": new_email},
                             changed_by_user_id=actor)
    changed = ", ".join([*(k.replace("_", " ") for k in updates if k not in ("first_name", "last_name")), *(["email"] if new_email else [])])
    _note(db, contact, f"Details changed from their email to the subscriptions inbox: {changed.replace('company id', 'company')}.", actor)
    _done(item, contact, "Details updated")


def _noted(db: Session, item: ReviewQueueItem, input_data: dict) -> None:
    """A change the Brain can't make itself (another title, print or digital): noted on their record for the team."""
    p = item.payload
    try:
        contact = _reader(db, item, input_data)
    except ValueError:
        item.payload = {**p, "details": [{"label": "Done", "value": "Not found on the database, so nothing was noted"}, *p["details"]]}
        return
    req = p.get("request") or {}
    what = (f"wants {req['new_title']} instead" if req.get("new_title") else
            f"wants the {'printed magazine' if req.get('format') == 'print' else 'digital edition'}" if req.get("format") else req.get("summary") or "a subscription change")
    extra = (input_data.get("note") or "").strip()
    _note(db, contact, f"Subscription change from their email to the subscriptions inbox: {what}." + (f"\n\n{extra}" if extra else ""), _actor(input_data))
    _done(item, contact, "Noted on their record")


def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    handlers = {"unsubscribe": _unsubscribe, "subscribe": _subscribe, "update_address": _update_address,
                "update_details": _update_details, "noted": _noted}
    if action_id in handlers:
        handlers[action_id](db, item, input_data)
    elif action_id != "not_subscription":
        raise ValueError("That button isn't available on this card.")


def _send_reply(db: Session, item: ReviewQueueItem, input_data: dict) -> None:
    from app.automations import outlook_reply
    from app.automations.sales_orders import _split_draft

    p = item.payload
    draft = (input_data.get("note") or "").strip() or p.get("original_text") or ""
    subject, body = _split_draft(draft)
    to = (input_data.get("to") or p.get("suggested_to") or "").strip()
    outlook_reply.send(db, input_data.get("_actor_user_id"), to, subject, body, mailbox=p.get("mailbox"), message_id=p.get("message_id"))
    contact = db.get(Contact, uuid.UUID(p["contact_id"])) if p.get("contact_id") else None
    if contact:
        _note(db, contact, f"Replied to their question about their copy, sent to {to}.\n\n{body}", _actor(input_data))
    item.payload = {**p, "details": [{"label": "Reply sent", "value": to}, *p["details"]]}


def _handle_query(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "send":
        _send_reply(db, item, input_data)
    elif action_id not in ("replied", "not_subscription"):
        raise ValueError("That button isn't available on this card.")


def _redraft(db: Session, item: ReviewQueueItem, extra: str) -> str:
    from app.automations.llm import is_configured

    if not is_configured():
        raise ValueError("The Brain isn't switched on for this account, so it can't rewrite the reply. Edit it yourself instead.")
    p = item.payload
    head, _, body = (p.get("source_context") or "").partition("\n\n")
    subject = next((line[9:] for line in head.splitlines() if line.startswith("Subject: ")), "")
    return draft_reply(ParsedMessage(message_id=p.get("message_id") or "", internet_message_id=None, from_address=p.get("reader_email"),
                                     from_name=(p.get("request") or {}).get("reader_name"), subject=subject,
                                     received_at=datetime.now(timezone.utc), body_text=body), p.get("title_key"), extra)


EMAIL_FIELD = ExtraField(key="email", label="Their email on the database", placeholder="name@company.com")

register(ReviewKind(
    kind=KIND,
    label="Subscription changes",
    description="Readers emailing the subscriptions inbox to unsubscribe, subscribe, change their address or details, or switch title or between print and digital - each with a button that makes the change on their record.",
    actions=[
        ReviewAction(id="unsubscribe", label="Unsubscribe them", style="primary", outcome="approved", extra_fields=[
            EMAIL_FIELD, ExtraField(key="everything", label="From every title, not just this one", field_type="bool")]),
        ReviewAction(id="subscribe", label="Subscribe them", style="primary", outcome="approved", extra_fields=[
            EMAIL_FIELD, ExtraField(key="name", label="Name (if they're new)", required=False)]),
        ReviewAction(id="update_address", label="Update the address", style="primary", outcome="approved", extra_fields=[
            EMAIL_FIELD, ExtraField(key="line1", label="Address line 1", required=False),
            ExtraField(key="line2", label="Address line 2", required=False), ExtraField(key="city", label="Town or city", required=False),
            ExtraField(key="postcode", label="Postcode", required=False), ExtraField(key="country", label="Country", required=False)]),
        ReviewAction(id="update_details", label="Update their details", style="primary", outcome="approved", extra_fields=[
            EMAIL_FIELD, ExtraField(key="name", label="Name", required=False), ExtraField(key="job_title", label="Job title", required=False),
            ExtraField(key="company_name", label="Company", required=False), ExtraField(key="new_email", label="New email", required=False)]),
        ReviewAction(id="noted", label="Done it - note it on their record", style="secondary", outcome="approved", extra_fields=[
            ExtraField(key="email", label="Their email on the database", placeholder="name@company.com", required=False)]),
        ReviewAction(id="not_subscription", label="Not a subscription email", style="secondary", outcome="rejected", reopenable=True),
    ],
    handler=_handle,
    audience="admin",
    facets=(("change", "Change"), ("magazine", "Magazine"), ("record", "On the database")),
    date_sort_label="date received",
))

register(ReviewKind(
    kind=QUERY_KIND,
    label="Reader questions",
    description="Readers asking the subscriptions inbox about their copy (not arrived, damaged, how to read it online), with a reply drafted to edit and send.",
    actions=[
        ReviewAction(id="send", label="Send reply from my Outlook", style="primary", outcome="approved",
                     extra_fields=[ExtraField(key="to", label="Send to", placeholder="name@company.com", required=False)]),
        ReviewAction(id="replied", label="I'll reply myself", style="secondary", outcome="approved"),
        ReviewAction(id="not_subscription", label="Not a reader question", style="secondary", outcome="rejected", reopenable=True),
    ],
    handler=_handle_query,
    redraft=_redraft,
    audience="admin",
    facets=(("magazine", "Magazine"), ("record", "On the database")),
    date_sort_label="date received",
))

register_job(ScheduledJob(
    id="subscription_change_scan",
    label="Subscription changes",
    description="Reads the subscriptions inbox for readers unsubscribing, subscribing, changing their details or asking about their copy.",
    cron="*/10 * * * *",
    func=scan,
    enabled_flag="automations_subscription_changes_enabled",
))
