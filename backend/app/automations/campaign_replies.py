"""SALES-030 - replies to a mail merge that need something done.

Out-of-office, undeliverable and "I've left" replies are already handled by the mailbox scan (CS-001 to CS-003).
This reads the other replies to recent email mail merges and spots two more:
  - "please unsubscribe me" / "take me off your list": a card to unsubscribe them (in Brevo too, when it's connected),
  - "speak to my colleague" / "the best person is...": a card to add the person they point to as a contact at the
    same company, so the next pitch goes to the right person.
Only the words the person wrote are read, not the quoted email below them (the merge's own "unsubscribe" footer
would match otherwise). Free word checks decide first; the Brain is asked only to pull a referred person's name, role
and address out of the reply, up to "Brain checks per run". Nothing is changed until someone presses a button.

Which replies: emails in the sender's own inbox, from someone the mail merge reached, arriving after it went out.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas import MANUAL_SOURCE_DB
from app.automations import runtime_settings
from app.automations.mail_parsing import ParsedMessage, looks_like_bounce, looks_like_ooo, parse_message
from app.automations.registry import ExtraField, ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.automations.state import get_state, set_state
from app.db.session import SessionLocal
from app.models import Company, Contact, Email, Note, ReviewQueueItem, User
from app.models.messaging import MailMerge, MailMergeRecipient

logger = logging.getLogger("app.automations.campaign_replies")

UNSUB = "campaign_unsubscribe"
REFERRAL = "campaign_referral"
STATE = "campaign_replies"

# Where the quoted email starts in a reply: everything from here down is what they're replying to.
_QUOTE = re.compile(r"^\s*(>|-{2,}\s*original message|_{5,}|from:\s|sent from my |on .{4,120}wrote:|get outlook for)", re.I | re.M)
_UNSUB = re.compile(
    r"\b(unsubscribe|opt(?:-| )?out|remove (?:me|us|my (?:email|name|address|details))|take (?:me|us) off|"
    r"no longer (?:wish|want) to (?:receive|hear|get)|(?:please )?stop (?:emailing|sending|contacting)|"
    r"don'?t (?:email|contact|send) (?:me|us)|do not (?:email|contact|send) (?:me|us)|not interested,? please remove)\b", re.I)
_REFER = re.compile(
    r"\b((?:best|right|correct) person (?:to (?:speak|talk) to|for this|to contact|is)|(?:please )?(?:speak|talk|reach out) to my colleague|"
    r"(?:please )?contact my colleague|i'?(?:ve| have) (?:copied|cc'?d|cc'ed|forwarded|passed)|(?:has|have) (?:taken over|replaced me)|"
    r"(?:now )?(?:looks after|handles|deals with|is responsible for) (?:this|our|advertising|marketing)|"
    r"(?:you(?:'ll| will) )?(?:need|want) to (?:speak|talk) to|(?:please )?(?:direct|send) (?:this|future emails|it) to|"
    r"(?:in|from) (?:the )?future,? please (?:contact|email))\b", re.I)
_EMAIL = re.compile(r"[\w.+'-]+@[\w-]+(?:\.[\w-]+)+")

_PROMPT = (
    "Someone replied to a sales email from a magazine publisher and pointed to another person to contact instead. From "
    "their reply, pull out who to contact. Use only what the reply says; never invent a name, role or address. "
    'Return JSON: {"name": string or null, "role": string or null, "email": string or null}.'
)


def own_words(body: str | None) -> str:
    """What they wrote, without the email they're replying to."""
    text = body or ""
    m = _QUOTE.search(text)
    return (text[:m.start()] if m else text).strip()


def classify(msg: ParsedMessage) -> str | None:
    """UNSUB, REFERRAL or None, from the words they wrote. Auto-replies and bounces are the mailbox scan's."""
    if looks_like_bounce(msg) or looks_like_ooo(msg):
        return None
    words = own_words(msg.body_text)
    if _UNSUB.search(words) or _UNSUB.search(msg.subject or "") and len(words) < 200:
        return UNSUB
    if _REFER.search(words):
        return REFERRAL
    return None


def referred(msg: ParsedMessage, own_domains: set[str], use_brain: bool) -> dict:
    """{"name", "role", "email", "ai"} for the person the reply points to, as far as it can tell."""
    words = own_words(msg.body_text)
    sender = (msg.from_address or "").lower()
    emails = [e for e in dict.fromkeys(e.lower().rstrip(".") for e in _EMAIL.findall(words))
              if e != sender and e.split("@")[1] not in own_domains]
    emails += [a.lower() for a in msg.to_addresses if a.lower() != sender and a.lower().split("@")[1] not in own_domains
               and a.lower() not in emails]   # someone they copied in
    out = {"name": None, "role": None, "email": emails[0] if emails else None, "ai": False}
    if use_brain:
        from app.automations.llm import extract_json
        got = extract_json(_PROMPT, f"Reply from {msg.from_name or sender}:\n\n{words[:2000]}", max_tokens=200,
                           purpose="campaign_replies.referral") or {}
        email = (got.get("email") or "").strip().lower()
        if email and email in words.lower():   # only an address the reply really contains
            out["email"] = email
        out.update(name=(got.get("name") or "").strip() or None, role=(got.get("role") or "").strip() or None, ai=bool(got))
    return out


def _recent_merges(db: Session, now: datetime) -> list[MailMerge]:
    back = runtime_settings.get_int(db, "campaign_reply_lookback_days")
    return list(db.scalars(select(MailMerge).where(
        MailMerge.output == "email", MailMerge.sent > 0, MailMerge.from_email.isnot(None),
        func.coalesce(MailMerge.finished_at, MailMerge.created_at) >= now - timedelta(days=back))))


def _recipients(db: Session, merges: list[MailMerge]) -> dict[str, tuple[MailMerge, uuid.UUID]]:
    """{email (lower case): (the latest merge it went to, the contact)} for everyone these merges reached."""
    out: dict[str, tuple[MailMerge, uuid.UUID]] = {}
    by_id = {m.id: m for m in merges}
    rows = db.execute(select(MailMergeRecipient.merge_id, MailMergeRecipient.email, MailMergeRecipient.contact_id).where(
        MailMergeRecipient.merge_id.in_(list(by_id)), MailMergeRecipient.status == "sent", MailMergeRecipient.email.isnot(None)))
    for merge_id, email, cid in rows:
        m, key = by_id[merge_id], email.lower()
        if key not in out or (out[key][0].created_at < m.created_at):
            out[key] = (m, cid)
    return out


def _details(db: Session, m: MailMerge, contact: Contact | None, msg: ParsedMessage) -> list[dict]:
    company = db.get(Company, contact.company_id) if contact and contact.company_id else None
    d = [{"label": "Reply from", "value": f"{msg.from_name or msg.from_address} ({msg.from_address})",
          **({"href": f"/contacts/{contact.id}"} if contact else {})}]
    if company:
        d.append({"label": "Company", "value": company.name, "href": f"/companies/{company.id}"})
    d += [{"label": "To your mail merge", "value": f"{m.subject or '(no subject)'} - sent {(m.finished_at or m.created_at):%-d %b %Y}",
           "href": f"/mail-merge/{m.id}"},
          {"label": "Received", "value": f"{msg.received_at:%-d %b %Y, %H:%M}"}]
    return d


def queue(db: Session, kind: str, m: MailMerge, contact_id: uuid.UUID | None, msg: ParsedMessage, who: dict | None = None) -> ReviewQueueItem:
    contact = db.get(Contact, contact_id) if contact_id else None
    sender = db.get(User, m.created_by_user_id) if m.created_by_user_id else None
    name = (contact.full_name if contact else None) or msg.from_name or msg.from_address
    details = _details(db, m, contact, msg)
    payload = {
        "details": details, "message_id": msg.message_id, "merge_id": str(m.id),
        "contact_id": str(contact.id) if contact else None, "reader_email": msg.from_address,
        "original_text": own_words(msg.body_text)[:3000] or msg.body_text[:3000], "original_label": "Their reply",
        "owner_user_id": str(m.created_by_user_id) if m.created_by_user_id else None,
        "related_entities": ([{"type": "company", "id": str(contact.company_id), "label": details[1]["value"]}]
                             if contact and contact.company_id and len(details) > 1 and details[1]["label"] == "Company" else []),
        "facets": {"salesperson": (sender.name or sender.email) if sender else "No one",
                   "matched": "On the database" if contact else "Not on the database"},
        "sort_date": msg.received_at.date().isoformat(),
    }
    if kind == UNSUB:
        payload["summary"] = f"{name} asked to be taken off your emails"
    else:
        who = who or {}
        label = who.get("name") or who.get("email") or "someone else"
        payload["summary"] = f"{name} says to contact {label} instead"
        details.append({"label": "Who to contact", "value": " · ".join(x for x in (who.get("name"), who.get("role"), who.get("email")) if x)
                        or "The reply doesn't say clearly - read it below and type their details in"})
        payload["field_defaults"] = {"full_name": who.get("name") or "", "email": who.get("email") or "", "job_title": who.get("role") or ""}
        payload["ai_drafted"] = bool(who.get("ai"))
        payload["facets"]["found"] = "Address found" if who.get("email") else "No address in the reply"
    item = ReviewQueueItem(id=uuid.uuid4(), kind=kind, status="pending", entity_type="contact" if contact else None,
                           entity_id=contact.id if contact else None, payload=payload)
    db.add(item)
    return item


def scan() -> None:
    from app.services.calendar_sync import internal_domains
    from app.graph_client import GraphRequestError, list_messages_since

    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        merges = _recent_merges(db, now)
        if not merges:
            return
        sent_to = _recipients(db, merges)
        seen = set(db.scalars(select(ReviewQueueItem.payload["message_id"].astext).where(
            ReviewQueueItem.kind.in_([UNSUB, REFERRAL]))))
        st = get_state(db, STATE)
        cursors = dict(st.get("cursors") or {})
        own = internal_domains(db)
        brain_left = runtime_settings.get_int(db, "campaign_reply_llm_max_per_run")
        queued = 0
        for box in sorted({m.from_email.lower() for m in merges}):
            first = min(m.created_at for m in merges if m.from_email.lower() == box)
            since = max(datetime.fromisoformat(cursors[box]), first) if box in cursors else first
            try:
                raw = list_messages_since(box, since.strftime("%Y-%m-%dT%H:%M:%SZ"), max_pages=20)
            except GraphRequestError as exc:
                logger.warning("campaign replies: inbox %s couldn't be read (HTTP %s)", box, exc.status_code)
                continue
            newest = since
            for r in raw:
                msg = parse_message(r)
                newest = max(newest, msg.received_at)
                frm = (msg.from_address or "").lower()
                if msg.message_id in seen or frm not in sent_to:
                    continue
                m, cid = sent_to[frm]
                if msg.received_at < (m.finished_at or m.created_at) - timedelta(minutes=5):
                    continue
                kind = classify(msg)
                if not kind:
                    continue
                who = None
                if kind == REFERRAL:
                    who = referred(msg, own, use_brain=brain_left > 0)
                    brain_left -= 1
                queue(db, kind, m, cid, msg, who)
                seen.add(msg.message_id)
                queued += 1
            cursors[box] = newest.isoformat()
            db.commit()
        set_state(db, STATE, {"cursors": cursors})
        db.commit()
        logger.info("campaign replies: %d cards", queued)
    finally:
        db.close()


def _actor(input_data: dict) -> uuid.UUID | None:
    a = input_data.get("_actor_user_id")
    return uuid.UUID(a) if a else None


def _note(db: Session, contact_id: uuid.UUID, body: str, actor: uuid.UUID | None) -> None:
    db.add(Note(id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()), entity_type="contact",
                entity_id=contact_id, note_type="Mail merge reply", body=body, act_created_at=datetime.now(timezone.utc),
                created_by_user_id=actor))


def _contact(db: Session, item: ReviewQueueItem) -> Contact:
    cid = item.payload.get("contact_id")
    c = db.get(Contact, uuid.UUID(cid)) if cid else None
    if not c:
        raise ValueError("They're not on the database any more (they may have been merged or deleted). Find them in Contacts and change it there.")
    return c


def _subject(db: Session, item: ReviewQueueItem) -> str:
    m = db.get(MailMerge, uuid.UUID(item.payload["merge_id"])) if item.payload.get("merge_id") else None
    return f'"{m.subject}"' if m and m.subject else "a mail merge"


def _handle_unsub(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "not_unsubscribe":
        return
    if action_id != "unsubscribe":
        raise ValueError("That button isn't available on this card.")
    from app.automations.brevo_sync import push_unsubscribe
    from app.services.field_audit import record_field_changes

    actor = _actor(input_data)
    c = _contact(db, item)
    # every record with the address they wrote from, in every title's database
    email = (item.payload.get("reader_email") or "").lower()
    people = {c.id: c, **{x.id: x for x in db.scalars(select(Contact).join(Email, Email.contact_id == Contact.id)
                                                      .where(func.lower(Email.address) == email))}} if email else {c.id: c}
    for p in people.values():
        if not p.is_unsubscribed:
            record_field_changes(db, entity_type="contact", entity_id=p.id, before={"is_unsubscribed": False},
                                 updates={"is_unsubscribed": True}, changed_by_user_id=actor)
            p.is_unsubscribed = True
        _note(db, p.id, f"Asked to be taken off BMI's emails, in their reply to {_subject(db, item)}. Unsubscribed.", actor)
    line = push_unsubscribe(db, list(people.values()), everything=True, source_db=None)
    item.payload = {**item.payload, "details": [*item.payload.get("details", []), {"label": "Done", "value": f"Unsubscribed ({len(people)} record{'s' if len(people) != 1 else ''})"},
                                                {"label": "Brevo", "value": line}]}


def _handle_referral(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "ignore":
        return
    if action_id != "add_contact":
        raise ValueError("That button isn't available on this card.")
    from app.automations.contact_match import find_contact_by_email

    actor = _actor(input_data)
    referrer = _contact(db, item)
    name = (input_data.get("full_name") or "").strip()
    email = (input_data.get("email") or "").strip()
    title = (input_data.get("job_title") or "").strip() or None
    if not name:
        raise ValueError("Type their name first.")
    if email and ("@" not in email or " " in email):
        raise ValueError(f"“{email}” doesn't look like an email address.")
    existing = find_contact_by_email(db, email) if email else None
    if existing:
        new = existing
        _note(db, new.id, f"{referrer.full_name or 'A colleague'} said to contact them instead, in a reply to {_subject(db, item)}.", actor)
    else:
        first, _, last = name.partition(" ")
        new = Contact(id=uuid.uuid4(), source_db=referrer.source_db, source_act_id=str(uuid.uuid4()), first_name=first,
                      last_name=last or None, full_name=name, job_title=title, company_id=referrer.company_id)
        db.add(new)
        db.flush()
        if email:
            db.add(Email(id=uuid.uuid4(), source_db=referrer.source_db, source_act_id=str(uuid.uuid4()), contact_id=new.id,
                         address=email, is_primary=True))
        _note(db, new.id, f"Added because {referrer.full_name or 'a colleague'} said to contact them instead, in a reply to {_subject(db, item)}.", actor)
    _note(db, referrer.id, f"Said to contact {name}{f' ({email})' if email else ''} instead, in their reply to {_subject(db, item)}.", actor)
    item.payload = {**item.payload, "details": [*item.payload.get("details", []),
                                                {"label": "Done", "value": f"{'Already on the database' if existing else 'Added'}: {name}", "href": f"/contacts/{new.id}"}]}


register(ReviewKind(
    kind=UNSUB,
    label="Unsubscribe requests (mail merge replies)",
    description="Someone replied to one of your mail merges asking to be taken off your emails.",
    actions=[
        ReviewAction(id="unsubscribe", label="Unsubscribe them", style="primary", outcome="approved"),
        ReviewAction(id="not_unsubscribe", label="Not an unsubscribe", style="secondary", outcome="dismissed", reopenable=True),
    ],
    handler=_handle_unsub,
    audience="sales",
    facets=(("salesperson", "Salesperson"), ("matched", "On the database")),
    date_sort_label="date of the reply",
))

register(ReviewKind(
    kind=REFERRAL,
    label="Referrals (mail merge replies)",
    description="Someone replied to one of your mail merges saying to contact a colleague instead.",
    actions=[
        ReviewAction(id="add_contact", label="Add them as a contact", style="primary", outcome="approved",
                     extra_fields=[ExtraField(key="full_name", label="Their name"),
                             ExtraField(key="email", label="Their email", required=False),
                             ExtraField(key="job_title", label="Job title", required=False)]),
        ReviewAction(id="ignore", label="Nothing to add", style="secondary", outcome="dismissed", reopenable=True),
    ],
    handler=_handle_referral,
    audience="sales",
    facets=(("salesperson", "Salesperson"), ("found", "Address"), ("matched", "On the database")),
    date_sort_label="date of the reply",
))

register_job(ScheduledJob(
    id="campaign_reply_scan",
    label="Mail merge replies",
    description="Every 30 minutes, reads replies to recent mail merges for unsubscribe requests and \"speak to my colleague\" referrals.",
    cron="*/30 * * * *",
    func=scan,
    enabled_flag="automations_campaign_replies_enabled",
))
