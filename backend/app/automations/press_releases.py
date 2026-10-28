"""SALES-014 and SALES-015 - press releases to a media kit introduction.

Editors forward press releases to the commercial team with a note to get in touch, but usually no contact: just the
release itself. This reads them from the inbox the editors forward to and puts one card per release in the
publisher's Review Queue:

SALES-014, who to contact:
  1. It's in one of the inboxes in "Press releases > Inboxes to read", and reads like a release (press release, media
     release, notes to editors, embargoed, media contact...). Bounces, out-of-office replies and automatic messages are
     skipped.
  2. The Brain reads it: the company, the story, the magazine it fits, and every contact the release names (press
     office, marketing, others), plus the editor's note when it was forwarded. Without the Brain, the addresses in the
     release are listed, marked as not checked.
  3. The company and the people are looked up in the CRM. Someone in marketing or trade relations - in the release, or
     already in the CRM at that company - is suggested ahead of the press office, as they hold the budget.
  4. The card goes to whoever looks after that company, or else the magazine's publisher.

SALES-015, the introduction:
  The card carries the short note a publisher would write by hand: it mentions the story, links the brand's media
  pack (Media pack link on the brand's settings page in Editorial) and offers to talk if they're interested. The publisher edits it and
  sends it from their own Outlook; the contact (and company) is added to the CRM if they're new and the email is
  noted on them. The Brain may write the sentences about the story, but they're thrown away if they add a figure.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas import MANUAL_SOURCE_DB
from app.automations import runtime_settings
from app.automations.contact_match import find_contact_by_email
from app.automations.mail_parsing import ParsedMessage, looks_like_bounce, looks_like_ooo, parse_message
from app.automations.registry import ExtraField, ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.automations.sender_patterns import is_automated_sender
from app.automations.state import get_state, set_state
from app.db.session import SessionLocal
from app.models import Company, Contact, Note, ReviewQueueItem, SalesRep, SalesTitle, User

logger = logging.getLogger("app.automations.press_releases")

KIND = "press_release"
NO_LINK = "[media pack link]"

_RELEASE = re.compile(r"\b(press release|media release|news release|for immediate release|notes? to editors?|embargo\w*|"
                      r"media (contact|enquir\w+)|press (contact|office|enquir\w+)|for (further|more) information)\b", re.I)
_FORWARDED = re.compile(r"(-{2,}\s*forwarded message|^-{2,}\s*original message|^from:\s.+$)", re.I | re.M)
_EMAIL = re.compile(r"[\w.+'-]+@[\w-]+(?:\.[\w-]+)+")
_BUDGET_ROLE = re.compile(r"market\w*|trade|partner\w*|commercial|sales|brand|business development", re.I)

_PROMPT = (
    "You read one email at BMI Publishing (business travel, travel-trade and onboard-hospitality magazines). It is "
    "usually a press release an editor has forwarded to the sales team, sometimes with a note. Return JSON: "
    "{\"is_release\": bool (true only for a company's press or news release), \"company\": the company the news is "
    "about, \"headline\": the story in under 12 words, \"story\": one or two plain sentences on what's new, "
    "\"sector\": one of airline|hotel|tech|tmc|tourism|rail|travel_services|caterer|other|null, \"magazine\": the "
    "magazine from the list given that the story fits best, or null, \"editor_note\": the forwarding editor's own note, "
    "or null, \"contacts\": a list of every person the release names to contact, each {\"name\", \"role\" (job title "
    "as written), \"email\", \"phone\", \"kind\": press|marketing|other} - press for a PR agency or press office, "
    "marketing for marketing, trade relations, partnerships or sales}. Never invent a value - use null, and leave out "
    "a contact with no name and no email."
)

_INTRO_PROMPT = (
    "Write two or three sentences opening a short, warm email from a magazine publisher to someone at the company in "
    "the press release below. Mention their news in your own words and why it would interest the magazine's readers. "
    "British English. No prices, numbers, dates or promises. No greeting line and no sign-off. Plain text only."
)


# ---- reading the inbox --------------------------------------------------------------------------------

def candidate(msg: ParsedMessage, mailbox: str) -> bool:
    """The free checks, before any Brain."""
    sender = (msg.from_address or "").lower()
    if not sender or sender == mailbox.lower() or is_automated_sender(sender):
        return False
    if looks_like_bounce(msg) or looks_like_ooo(msg):
        return False
    return bool(_RELEASE.search(f"{msg.subject}\n{msg.body_text}"))


def _titles(db: Session) -> list[SalesTitle]:
    return list(db.scalars(select(SalesTitle).where(SalesTitle.active.is_(True))))


def classify(db: Session, msg: ParsedMessage, domains: set[str]) -> dict | None:
    from app.automations.llm import extract_json, is_configured

    if not is_configured():
        found = []
        for e in dict.fromkeys(_EMAIL.findall(msg.body_text or "")):
            if e.split("@")[-1].lower() not in domains and e.lower() != (msg.from_address or "").lower():
                found.append({"name": None, "role": None, "email": e, "phone": None, "kind": "other"})
        return {"is_release": True, "company": None, "headline": re.sub(r"^((re|fw|fwd):\s*)+", "", msg.subject or "", flags=re.I)[:120],
                "story": None, "sector": None, "magazine": None, "editor_note": None, "contacts": found[:6], "unchecked": True}
    names = "; ".join(t.name for t in _titles(db))
    out = extract_json(_PROMPT, f"Magazines: {names}\n\nFrom: {msg.from_name or ''} <{msg.from_address}>\nSubject: {msg.subject}\n\n"
                                f"{(msg.body_text or '')[:8000]}", max_tokens=700, purpose="press_releases.classify")
    if not isinstance(out, dict) or not out.get("is_release"):
        return None
    out["contacts"] = [c for c in (out.get("contacts") or []) if isinstance(c, dict) and (c.get("name") or c.get("email"))][:6]
    return out


def _find_company(db: Session, name: str | None, contacts: list[dict], source_db: str | None) -> Company | None:
    if name:
        rows = list(db.scalars(select(Company).where(func.lower(Company.name) == name.strip().lower())))
        pick = next((c for c in rows if c.source_db == source_db), None) or (rows[0] if rows else None)
        if pick:
            return pick
    for c in contacts:
        found = find_contact_by_email(db, c.get("email"))
        if found and found.company_id:
            return db.get(Company, found.company_id)
    return None


def people(db: Session, info: dict, company: Company | None) -> list[dict]:
    """Everyone worth contacting, best first: marketing or trade people (they hold the budget), then the press office.
    Each is {name, role, email, phone, kind, contact_id, from}."""
    out: list[dict] = []
    seen: set[str] = set()
    for c in info.get("contacts") or []:
        email = (c.get("email") or "").strip()
        found = find_contact_by_email(db, email) if email else None
        out.append({"name": c.get("name") or (found.full_name if found else None), "role": c.get("role"), "email": email or None,
                    "phone": c.get("phone"), "kind": c.get("kind") if c.get("kind") in ("press", "marketing") else "other",
                    "contact_id": str(found.id) if found else None, "from": "release"})
        if email:
            seen.add(email.lower())
    if company:
        from app.models import Email
        crm = db.execute(select(Contact, Email.address).join(Email, Email.contact_id == Contact.id)
                         .where(Contact.company_id == company.id, Contact.is_unsubscribed.is_(False)).limit(40)).all()
        for contact, address in crm:
            if address and address.lower() not in seen and _BUDGET_ROLE.search(contact.job_title or ""):
                out.append({"name": contact.full_name, "role": contact.job_title, "email": address, "phone": None, "kind": "marketing",
                            "contact_id": str(contact.id), "from": "crm"})
                seen.add(address.lower())
    rank = {"marketing": 0, "other": 1, "press": 2}
    out.sort(key=lambda p: (rank[p["kind"]], 0 if p["email"] else 1))
    return out


def _owner_for(db: Session, company: Company | None, title: SalesTitle | None) -> User | None:
    """Whoever looks after the company, or else the magazine's first publisher."""
    from app.sales.brands import brand_for_title_slug
    if company and company.owner_user_id:
        u = db.get(User, company.owner_user_id)
        if u:
            return u
    b = brand_for_title_slug(title.slug) if title else None
    for code in b.editors if b else ():
        rep = db.scalars(select(SalesRep).where(SalesRep.code == code, SalesRep.user_id.isnot(None))).first()
        if rep:
            return db.get(User, rep.user_id)
    return None


def media_pack(db: Session, title: SalesTitle | None) -> tuple[str | None, str | None, dict]:
    """(brand name, media pack link, the brand's facts) for the magazine."""
    from app.proposals.blocks import brand_of
    from app.services.mail_merge import shared_context
    b = brand_of(db, title.id) if title else None
    facts = shared_context(db, b.key) if b else {}
    return (b.name if b else None), (facts.get("media_pack") or None), facts


def compose(db: Session, info: dict, title: SalesTitle | None, owner: User | None, person: dict | None, release: str,
            subject: str, extra: str = "") -> tuple[str, bool]:
    """(draft, ai_used): the introduction, in the "Subject: ..." + body form the Review Queue edits and sends."""
    from app.automations.llm import draft_text, is_configured
    from app.proposals import style
    from app.proposals.drafting import numbers_in

    prof = style.effective(db, owner.id if owner else None)
    brand, link, facts = media_pack(db, title)
    brand = brand or "our magazine"
    headline = (info.get("headline") or "").strip()
    about = f"your news - {headline.rstrip('.')} -" if headline else "your recent news"
    opening = (f"I've just read {about} and it's exactly the kind of story {brand}'s readers follow"
               + (f", as {facts['readership']}" if facts.get("readership") else "") + ".")
    ai = False
    if is_configured():
        guide = f"Their style: {prof['tone']} {prof['summary']}" + (f" They never: {'; '.join(prof['never'])}." if prof["never"] else "")
        ask = f"{extra}\n\n" if extra else ""
        got = draft_text(_INTRO_PROMPT + f" The magazine is {brand}. " + guide, f"{ask}THE RELEASE:\n{release[:5000]}", max_tokens=200,
                         purpose="press_releases.intro")
        if got and not numbers_in(got) and len(got) < 700:
            opening, ai = got.strip(), True
    first = (person or {}).get("name") or ""
    greeting = prof["greeting"].replace("{first_name}", first.split(" ")[0] if first and "@" not in first else "there")
    company = info.get("company") or ""
    subj = f"{brand} and {company}" if company else f"Your news and {brand}"
    parts = [f"Subject: {subj}", "", greeting, "", opening, "",
             f"If you're looking to reach {brand}'s readers, our media pack has the details: {link or NO_LINK}", "",
             "If it's of interest, I'd be happy to talk through some ideas - just reply to this email.", "", style.sign_off(prof, owner)]
    return "\n".join(parts).strip(), ai


def _details(info: dict, msg: ParsedMessage, title: SalesTitle | None, company: Company | None, found: list[dict],
             brand: str | None, link: str | None, forwarded_by: str | None) -> list[dict]:
    d = [{"label": "Company", "value": company.name if company else (info.get("company") or "Not named") + (" - not in the CRM yet" if not company else ""),
          **({"href": f"/companies/{company.id}"} if company else {})},
         {"label": "Story", "value": info.get("headline") or msg.subject or "(no subject)"}]
    if info.get("story"):
        d.append({"label": "In short", "value": info["story"]})
    if title:
        d.append({"label": "Magazine", "value": title.name})
    if forwarded_by:
        d.append({"label": "Forwarded by", "value": forwarded_by})
    if info.get("editor_note"):
        d.append({"label": "Editor's note", "value": info["editor_note"]})
    for p in found:
        bits = [x for x in (p.get("role"), p.get("email"), p.get("phone")) if x]
        label = {"marketing": "Marketing contact", "press": "Press contact"}.get(p["kind"], "Contact")
        if p["from"] == "crm":
            label += " (in the CRM)"
        d.append({"label": label, "value": " - ".join([p.get("name") or "No name given", *bits]),
                  **({"href": f"/contacts/{p['contact_id']}"} if p.get("contact_id") else {})})
    if not found:
        d.append({"label": "Contact", "value": "The release names no one to contact - find someone at the company, then type their email when sending."})
    if not link:
        d.append({"label": "Worth knowing", "value": f"No media pack link is saved for {brand or 'this magazine'} - add it as Media pack link on the brand's settings page in Editorial, or type it into the draft."})
    if info.get("unchecked"):
        d.append({"label": "Worth knowing", "value": "The Brain isn't switched on, so this was picked up from the words it uses and the addresses in it. Check it really is a release."})
    return d


def _main_title(db: Session, title: SalesTitle | None) -> SalesTitle | None:
    """A brand's own magazine rather than its website or events title ("Selling Travel", not "Selling Travel Online")."""
    from app.sales.brands import brand_for_title_slug
    b = brand_for_title_slug(title.slug) if title else None
    main = db.scalars(select(SalesTitle).where(SalesTitle.slug == b.title_slugs[0])).first() if b else None
    return main or title


def queue(db: Session, mailbox: str, msg: ParsedMessage, info: dict, domains: set[str]) -> ReviewQueueItem:
    from app.automations.proposal_requests import _title_for, short_name

    title = _main_title(db, _title_for(db, info.get("magazine"), None) if info.get("magazine") else None)
    company = _find_company(db, info.get("company"), info.get("contacts") or [], title.crm_source_db if title else None)
    found = people(db, info, company)
    best = next((p for p in found if p.get("email")), None)
    owner = _owner_for(db, company, title)
    brand, link, _ = media_pack(db, title)
    sender = (msg.from_address or "").lower()
    forwarded_by = (msg.from_name or msg.from_address) if sender.split("@")[-1] in domains else None
    draft, ai = compose(db, info, title, owner, best, msg.body_text or "", msg.subject)
    received = msg.received_at
    company_name = company.name if company else info.get("company")
    contact_state = ("In the CRM" if best and best.get("contact_id") else "New contact" if best else "No contact found")
    item = ReviewQueueItem(
        id=uuid.uuid4(), kind=KIND, source_db=title.crm_source_db if title else None, status="pending",
        entity_type="company" if company else None, entity_id=company.id if company else None,
        payload={
            "summary": f"Press release: {company_name or 'a company'}" + (f" - {info['headline']}" if info.get("headline") else ""),
            "details": _details(info, msg, title, company, found, brand, link, forwarded_by),
            "original_text": draft, "original_label": "Drafted introduction",
            "source_context": f"From: {msg.from_name or ''} <{msg.from_address}>\nSubject: {msg.subject}\n\n{(msg.body_text or '')[:6000]}",
            "suggested_to": best["email"] if best else "",
            "people": found, "release": {k: info.get(k) for k in ("company", "headline", "story", "sector", "magazine", "editor_note")},
            "related_entities": ([{"type": "company", "id": str(company.id), "label": company.name}] if company else [])
                                + [{"type": "contact", "id": p["contact_id"], "label": p.get("name") or p.get("email") or "Contact"}
                                   for p in found if p.get("contact_id")],
            "open_href": f"/companies/{company.id}" if company else None,
            "mailbox": mailbox, "message_id": msg.message_id, "owner_user_id": str(owner.id) if owner else None,
            "title_id": str(title.id) if title else None, "ai_drafted": ai,
            # what proposal_requests._crm_records reads to add the client when the introduction goes out
            "request": {"client_company": company_name, "contact_name": best.get("name") if best else None,
                        "contact_email": best.get("email") if best else None},
            "field_defaults": {"name": (best or {}).get("name") or "", "email": (best or {}).get("email") or "",
                               "job_title": (best or {}).get("role") or "", "company_name": company_name or ""},
            "facets": {"magazine": short_name(title) if title else "Not sure", "contact": contact_state,
                       "company": "In the CRM" if company else "New company",
                       "salesperson": (owner.name or owner.email) if owner else "No owner"},
            "sort_date": received.date().isoformat() if received else date.today().isoformat(),
        },
    )
    db.add(item)
    return item


def scan() -> None:
    from app.graph_client import GraphRequestError, list_messages_since

    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        boxes = runtime_settings.get_csv(db, "press_release_mailboxes")
        if not boxes:
            logger.info("press releases: no inboxes listed - nothing to read")
            return
        domains = {d.strip().lower() for d in runtime_settings.get_csv(db, "email_summary_internal_domains")}
        cap = runtime_settings.get_int(db, "press_release_llm_max_per_run")
        used = 0
        seen = {r[0] for r in db.execute(select(ReviewQueueItem.payload["message_id"].astext).where(ReviewQueueItem.kind == KIND)) if r[0]}
        for box in boxes:
            key = f"press_releases:{box.lower()}"
            st = get_state(db, key)
            since = datetime.fromisoformat(st["last_processed_at"]) if st.get("last_processed_at") else \
                now - timedelta(minutes=runtime_settings.get_int(db, "press_release_lookback_minutes"))
            try:
                raw = list_messages_since(box, since.strftime("%Y-%m-%dT%H:%M:%SZ"))
            except GraphRequestError as exc:
                logger.error("press releases: inbox %s couldn't be read (HTTP %s)", box, exc.status_code)
                continue
            skip = set(st.get("last_message_ids", []))
            msgs = sorted((parse_message(m) for m in raw if m.get("id") not in skip), key=lambda m: m.received_at)
            done_upto, queued = None, 0
            for msg in msgs:
                if msg.message_id in seen or not candidate(msg, box):
                    done_upto = msg
                    continue
                if used >= cap:
                    break
                used += 1
                info = classify(db, msg, domains)
                done_upto = msg
                if info:
                    queue(db, box, msg, info, domains)
                    seen.add(msg.message_id)
                    queued += 1
            if done_upto:
                set_state(db, key, {"last_processed_at": done_upto.received_at.isoformat(), "last_message_ids": [done_upto.message_id]})
            db.commit()
            logger.info("press releases: %s - %d read, %d queued", box, len(msgs), queued)
    finally:
        db.close()


# ---- the card's buttons ---------------------------------------------------------------------------------

def _person_for(item: ReviewQueueItem, email: str) -> dict:
    return next((p for p in item.payload.get("people") or [] if (p.get("email") or "").lower() == email.lower()), {})


def _client(db: Session, item: ReviewQueueItem, email: str, name: str | None = None, job_title: str | None = None,
            company_name: str | None = None) -> tuple[Contact | None, Company | None]:
    """The contact and company in the CRM, added if they're new (only when someone acts on the card)."""
    from app.automations.proposal_requests import _crm_records

    p = item.payload
    person = _person_for(item, email)
    req = {**(p.get("request") or {}), "contact_email": email, "contact_name": name or person.get("name"),
           "client_company": company_name or (p.get("request") or {}).get("client_company")}
    item.payload = {**p, "suggested_to": email, "request": req}
    contact, company = _crm_records(db, item)
    role = job_title or person.get("role")
    if contact and role and not contact.job_title:
        contact.job_title = role[:256]
    return contact, company


def _note(db: Session, contact: Contact | None, company: Company | None, body: str, actor: str | None) -> None:
    target = ("contact", contact.id) if contact else ("company", company.id) if company else None
    if target:
        db.add(Note(id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()), entity_type=target[0], entity_id=target[1],
                    note_type="Media kit introduction", body=body, act_created_at=datetime.now(timezone.utc),
                    created_by_user_id=uuid.UUID(actor) if actor else None))


def _linked(item: ReviewQueueItem, label: str, contact: Contact | None, company: Company | None) -> None:
    extra = ([{"label": label, "value": contact.full_name or "Contact", "href": f"/contacts/{contact.id}"}] if contact else []) \
        + ([{"label": "Company", "value": company.name, "href": f"/companies/{company.id}"}] if company and not item.entity_id else [])
    if company:
        item.entity_type, item.entity_id = "company", company.id
    item.payload = {**item.payload, "details": [*extra, *item.payload["details"]],
                    "open_href": item.payload.get("open_href") or (f"/companies/{company.id}" if company else None)}


def _send(db: Session, item: ReviewQueueItem, input_data: dict) -> None:
    from app.automations import outlook_reply
    from app.automations.sales_orders import _split_draft

    p = item.payload
    draft = (input_data.get("note") or "").strip() or p.get("original_text") or ""
    if NO_LINK in draft:
        raise ValueError("Add the media pack link to the email first - it isn't saved for this magazine yet.")
    to = (input_data.get("to") or p.get("suggested_to") or "").strip()
    subject, body = _split_draft(draft)
    outlook_reply.send(db, input_data.get("_actor_user_id"), to, subject, body)   # a new email, not a reply to the editor
    contact, company = _client(db, item, to)
    _note(db, contact, company, f"Sent a media kit introduction after their press release ({p.get('release', {}).get('headline') or 'their news'}), to {to}.\n\n{body}",
          input_data.get("_actor_user_id"))
    _linked(item, "Introduction sent to", contact, company)


def _logged(db: Session, item: ReviewQueueItem, input_data: dict) -> None:
    p = item.payload
    to = (input_data.get("to") or p.get("suggested_to") or "").strip()
    if not to:
        raise ValueError("Type the email address you're sending it to, so it's logged on the right person.")
    contact, company = _client(db, item, to)
    draft = (input_data.get("note") or "").strip() or p.get("original_text") or ""
    _note(db, contact, company, f"Media kit introduction after their press release, sent another way to {to}.\n\n{draft}", input_data.get("_actor_user_id"))
    _linked(item, "Logged on", contact, company)


def _add_contact(db: Session, item: ReviewQueueItem, input_data: dict) -> None:
    email = (input_data.get("email") or "").strip()
    if not re.fullmatch(r"[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+", email):
        raise ValueError("Type their email address - it's how they're matched in the CRM.")
    if not (input_data.get("name") or "").strip() and not _person_for(item, email).get("name"):
        raise ValueError("Type their name.")
    contact, company = _client(db, item, email, (input_data.get("name") or "").strip() or None,
                               (input_data.get("job_title") or "").strip() or None, (input_data.get("company_name") or "").strip() or None)
    _note(db, contact, company, f"Added from a press release ({item.payload.get('release', {}).get('headline') or 'their news'}).", input_data.get("_actor_user_id"))
    _linked(item, "Added", contact, company)


def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "send":
        _send(db, item, input_data)
    elif action_id == "logged":
        _logged(db, item, input_data)
    elif action_id == "add_contact":
        _add_contact(db, item, input_data)
    elif action_id != "not_release":
        raise ValueError("That button isn't available on this card.")


def _redraft(db: Session, item: ReviewQueueItem, extra: str) -> str:
    p = item.payload
    owner = db.get(User, uuid.UUID(p["owner_user_id"])) if p.get("owner_user_id") else None
    title = db.get(SalesTitle, uuid.UUID(p["title_id"])) if p.get("title_id") else None
    to = (p.get("suggested_to") or "").lower()
    person = next((x for x in p.get("people") or [] if (x.get("email") or "").lower() == to), None)
    release = (p.get("source_context") or "").split("\n\n", 1)[-1]
    draft, _ = compose(db, p.get("release") or {}, title, owner, person, release, "", extra=extra)
    return draft


register(ReviewKind(
    kind=KIND,
    label="Press releases",
    description="Press releases the editors forward, with the company and who to contact found, and a media kit introduction drafted to send.",
    actions=[
        ReviewAction(id="send", label="Send the introduction", style="primary", outcome="approved",
                     extra_fields=[ExtraField(key="to", label="Send to", placeholder="name@company.com", required=False)]),
        ReviewAction(id="logged", label="I'll send it myself", style="secondary", outcome="approved"),
        ReviewAction(id="add_contact", label="Just add the contact", style="secondary", outcome="approved", extra_fields=[
            ExtraField(key="name", label="Name", required=False), ExtraField(key="email", label="Email"),
            ExtraField(key="job_title", label="Job title", required=False), ExtraField(key="company_name", label="Company", required=False)]),
        ReviewAction(id="not_release", label="Not a press release", style="secondary", outcome="rejected", reopenable=True),
    ],
    handler=_handle,
    redraft=_redraft,
    audience="sales",
    facets=(("magazine", "Magazine"), ("contact", "Contact"), ("company", "Company"), ("salesperson", "Salesperson")),
    date_sort_label="date received",
))

register_job(ScheduledJob(
    id="press_release_scan",
    label="Press releases",
    description="Reads the inboxes editors forward press releases to, finds who to contact and drafts a media kit introduction.",
    cron="*/15 * * * *",
    func=scan,
    enabled_flag="automations_press_releases_enabled",
))
