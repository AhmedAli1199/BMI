"""Proposal requests: emails asking for prices, a media pack or a proposal, spotted in a salesperson's inbox and
put in their Review Queue with a reply already drafted (Ahmed, 14 Oct 2026 - "the single most important thing").

How an email gets here, cheapest first:
  1. It's in one of the inboxes listed in "Proposal requests > Inboxes to read" (start with Kirsty's, then the rest).
  2. Not sent by the inbox's owner, not an automatic message, bounce, out-of-office or newsletter.
     A colleague passing on an enquiry ("Bev the editor passed this onto me") still counts.
  3. It mentions prices, rates, a media pack, a quote, a proposal, advertising, sponsorship... (a keyword check, free).
  4. The AI reads it and decides whether it really is asking for prices or a proposal, and picks out the magazine,
     what they want, any budget or timing, whether it's an agency, and the client's details. No AI configured:
     only emails with two or more of the words above are queued, marked as unchecked.
One card per email thread, only for the person whose inbox it came from.

The reply is drafted from the Brain's own data - never figures from the AI:
  - prices from the rate card, for the products they asked about (or the magazine's main ones);
  - the next issues, their themes and booking deadlines from the editorial plan;
  - the media pack link from the brand facts.
The AI may write the opening sentence or two in the context of their email, but it's thrown away if it adds any
figure. The salesperson edits the draft, then Send replies in the same thread from their own Outlook; or "Make a full
proposal" opens the proposal builder with the client (added to the CRM if new), the products and the examples ready.
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
from app.automations.sender_patterns import contains_unsubscribe_text, is_automated_sender
from app.automations.state import get_state, set_state
from app.db.session import SessionLocal
from app.models import Company, Contact, Email, Note, ReviewQueueItem, SalesRate, SalesRep, SalesTitle, User

logger = logging.getLogger("app.automations.proposal_requests")

KIND = "proposal_request"

TYPES = {"agency_brief": "Agency brief", "pr_pitch": "PR pitch", "general": "General enquiry", "referral": "Referral",
         "follow_up": "After a call or event", "existing_client": "Existing client"}

_STRONG = re.compile(r"\b(rates?|rate ?card|media (pack|kit|info\w*)|pric(e|es|ing)|quote|quotation|proposal|advertis\w*|sponsor\w*|"
                     r"advertorial|sponsored content|costs?|costings?|packages?|opportunit(y|ies)|brief|budget)\b", re.I)
_FORWARDED = re.compile(r"(-{2,}\s*forwarded message|^from:\s.+$|passed (this|it) on|forwarding (this|on))", re.I | re.M)

# What they asked for -> which rate card sections to quote
WANTS = [
    (re.compile(r"sponsor\w* content|advertorial|interview|q ?& ?a|profile|feature|article|editorial|spotlight", re.I), ("sponsored",)),
    (re.compile(r"\badvert\w*|display|full page|half page|quarter|print|page\b|cover", re.I), ("print",)),
    (re.compile(r"newsletter|e-?mail|e-?shot|html|digital|online|website|web|banner|leaderboard|mpu|podcast", re.I), ("newsletter", "website")),
    (re.compile(r"event|award|forum|dinner|lunch|table|sponsorship|conference", re.I), ("events", "awards")),
]

_PROMPT = (
    "You read one email that arrived in a magazine salesperson's inbox at BMI Publishing (business travel and travel-trade "
    "magazines, their websites, newsletters, events and awards). Decide whether the sender is asking for advertising or "
    "sponsorship prices, rates, a media pack, a quote or a proposal - including an agency brief, a PR agency pitching a "
    "client for coverage (that becomes paid sponsored content), or a colleague passing on such an enquiry. A newsletter, "
    "an invoice, a supplier selling to BMI, a press release with no question, or internal chat is NOT a request.\n"
    "Return JSON: {\"is_request\": bool, \"confidence\": 0..1, \"request_type\": one of "
    "agency_brief|pr_pitch|general|referral|follow_up|existing_client, \"magazine\": the magazine or event they mean "
    "(choose from the list given, or null), \"wants\": what they're after in a few words, \"budget\": as written or null, "
    "\"timing\": as written or null, \"agency\": bool (they book for a client), \"client_company\": the company the "
    "booking would be for, \"contact_name\": the person to reply to, \"contact_email\": their address (for a passed-on "
    "email, the original sender's), \"sector\": one of airline|hotel|tech|tmc|tourism|rail|travel_services|other|null, "
    "\"summary\": one plain sentence}. Never invent a value - use null."
)

_OPENING_PROMPT = (
    "Write the first one or two sentences of a friendly, professional reply from a magazine salesperson to the email "
    "below. Thank them and refer to what they asked about in their own terms. British English. No prices, numbers, "
    "dates or promises - those follow separately. No greeting line and no sign-off. Plain text only."
)


# ---- helpers ------------------------------------------------------------------------------------------

def _owner(db: Session, mailbox: str) -> User | None:
    return db.scalars(select(User).where(func.lower(User.email) == mailbox.lower())).first()


def _rep_brand(db: Session, user: User | None):
    from app.sales.brands import BRANDS
    rep = db.scalars(select(SalesRep).where(SalesRep.user_id == user.id)).first() if user else None
    return next((b for b in BRANDS if rep and rep.code in b.editors), None)


def _title_for(db: Session, magazine: str | None, user: User | None) -> SalesTitle | None:
    titles = list(db.scalars(select(SalesTitle).where(SalesTitle.active.is_(True))))
    if magazine:
        m = magazine.lower()
        for t in titles:
            short = re.sub(r"\s*\(.*?\)", "", t.name).lower()
            abbrev = (re.search(r"\((\w+)\)", t.name) or [None, ""])[1].lower()
            if short in m or m in short or (abbrev and abbrev == m.strip()):
                return t
    b = _rep_brand(db, user)
    if b:
        return next((t for t in titles if t.slug == b.title_slugs[0]), None)
    return None


def short_name(title: SalesTitle) -> str:
    """"The Business Travel Magazine (TBTM)" -> "The Business Travel Magazine"."""
    return re.sub(r"\s*\(.*?\)", "", title.name)


def keyword_hits(text: str) -> int:
    return len({m.group(0).lower() for m in _STRONG.finditer(text or "")})


def _is_internal(addr: str | None, domains: set[str]) -> bool:
    return bool(addr and addr.split("@")[-1].lower() in domains)


def candidate(msg: ParsedMessage, mailbox: str, domains: set[str]) -> bool:
    """The free checks, before any AI."""
    sender = (msg.from_address or "").lower()
    if not sender or sender == mailbox.lower() or is_automated_sender(sender):
        return False
    if looks_like_bounce(msg) or looks_like_ooo(msg) or msg.headers.get("list-unsubscribe") or contains_unsubscribe_text(msg.body_text or ""):
        return False
    text = f"{msg.subject}\n{msg.body_text}"
    if _is_internal(sender, domains) and not _FORWARDED.search(msg.body_text or ""):
        return False   # internal chat, unless a colleague is passing an enquiry on
    return keyword_hits(text) >= 1


def classify(db: Session, msg: ParsedMessage) -> dict | None:
    from app.automations.llm import extract_json, is_configured

    titles = [t.name for t in db.scalars(select(SalesTitle).where(SalesTitle.active.is_(True)))]
    if not is_configured():
        hits = keyword_hits(f"{msg.subject}\n{msg.body_text}")
        if hits < 2:
            return None
        return {"is_request": True, "confidence": 0.4, "request_type": "general", "magazine": None, "wants": None, "budget": None,
                "timing": None, "agency": False, "client_company": None, "contact_name": msg.from_name, "contact_email": msg.from_address,
                "sector": None, "summary": f"Mentions {hits} things like prices or a media pack - not checked by the Brain.", "unchecked": True}
    user = (f"Magazines and events: {'; '.join(titles)}\n\nFrom: {msg.from_name or ''} <{msg.from_address}>\nSubject: {msg.subject}\n\n"
            f"{(msg.body_text or '')[:6000]}")
    out = extract_json(_PROMPT, user, max_tokens=500, purpose="proposal_requests.classify")
    if not isinstance(out, dict) or not out.get("is_request"):
        return None
    if out.get("request_type") not in TYPES:
        out["request_type"] = "general"
    return out


def pick_rates(db: Session, title: SalesTitle | None, wants: str | None, limit: int = 8) -> list[SalesRate]:
    from app.proposals.blocks import brand_rates
    from app.sales.brands import brand_for_title_slug

    b = brand_for_title_slug(title.slug) if title else None
    rates = [r for r in brand_rates(db, b) if r.price_gbp is not None or r.price_type == "poa"] if b else []
    sections: list[str] = []
    for rx, secs in WANTS:
        if wants and rx.search(wants):
            sections += [s for s in secs if s not in sections]
    sections = sections or ["print", "sponsored"]
    # A few from each thing they asked about, in the order they asked, so every one is covered.
    each = max(2, limit // len(sections))
    picked: list[SalesRate] = []
    for sec in sections:
        picked += [r for r in rates if r.section == sec][:each]
    return picked[:limit]


def _first_name(name: str | None) -> str:
    return (name or "").strip().split(" ")[0] if name and "@" not in name else "there"


def compose(db: Session, info: dict, title: SalesTitle | None, owner: User | None, msg_text: str, rates: list[SalesRate],
            subject: str, extra: str = "") -> tuple[str, bool]:
    """(draft, ai_used) - plain text with **bold** and "- " bullets, the format the Review Queue edits and sends.
    What goes in, in what order and in whose voice comes from the owner's writing profile (app/proposals/style.py);
    every figure comes from the rate card, editorial plan and brand facts."""
    from app.automations.llm import draft_text, is_configured
    from app.proposals import examples as ex
    from app.proposals import style
    from app.proposals.blocks import brand_of, money, price_text
    from app.proposals.drafting import numbers_in
    from app.sales.editorial import fmt_day, issue_label
    from app.services.mail_merge import shared_context

    prof = style.effective(db, owner.id if owner else None)
    kind = info.get("request_type") or "general"
    sit = style.situation(prof, kind)
    include = sit["include"]
    client = info.get("client_company")
    for_client = f" on behalf of {client}" if client and info.get("agency") else ""
    opening = (sit.get("opening") or style.DEFAULT_PROFILE["situations"]["general"]["opening"]).replace("{for_client}", for_client)
    ai = False
    if is_configured():
        guide = f"Their style: {prof['tone']} {prof['summary']}" + (f" They never: {'; '.join(prof['never'])}." if prof["never"] else "")
        got = draft_text(_OPENING_PROMPT + " " + guide, f"{extra}\n\nTHEIR EMAIL:\n{msg_text[:4000]}" if extra else f"THEIR EMAIL:\n{msg_text[:4000]}",
                         max_tokens=160, purpose="proposal_requests.opening")
        if got and not numbers_in(got) and len(got) < 600:
            opening, ai = got.strip(), True
    b = brand_of(db, title.id) if title else None
    facts = shared_context(db, b.key) if b else {}
    plain_subject = re.sub(r"^((re|fw|fwd):\s*)+", "", subject or "", flags=re.I)
    greeting = prof["greeting"].replace("{first_name}", _first_name(info.get("contact_name")))
    parts = [f"Subject: RE: {plain_subject}".strip(), "", greeting, "", opening]
    for item in include:
        if item == "prices" and rates:
            direct = not info.get("agency") and prof["prices"].get("direct_discount_pct")
            heading = f"{short_name(title)} prices" if title else "Prices"
            parts += ["", f"**{heading} (before VAT{', our introductory rates' if direct else ''})**"]
            for r in rates:
                price = price_text(r)
                if direct and r.price_gbp is not None and r.price_type != "poa":
                    price = price.replace(money(float(r.price_gbp)), money(style.direct_price(prof, float(r.price_gbp))))
                parts.append(f"- {r.product}{f' ({r.specs})' if r.specs else ''}: {price}")
        elif item == "issues" and title:
            from sqlalchemy import or_
            from app.models import SalesEdition
            today = date.today()
            eds = list(db.scalars(select(SalesEdition).where(SalesEdition.title_id == title.id, SalesEdition.kind.in_(("issue", "guide")),
                                                             SalesEdition.edition_date.isnot(None),
                                                             or_(SalesEdition.ad_deadline >= today, SalesEdition.ad_deadline.is_(None) & (SalesEdition.edition_date >= today)))
                                  .order_by(SalesEdition.edition_date).limit(3)))
            if eds:
                parts += ["", f"**{style.HEADINGS['issues']}**"]
                for e in eds:
                    bits = [f"out {fmt_day(e.edition_date)}" if e.edition_date else None, e.theme, f"book by {fmt_day(e.ad_deadline)}" if e.ad_deadline else None]
                    parts.append(f"- {issue_label(e)}: " + ", ".join(x for x in bits if x))
        elif item == "stats" and b:
            from app.services.mail_merge import BRAND_FIELDS
            rows = [f"- {label}: {facts[k]}" for k, (label, _x) in BRAND_FIELDS.items()
                    if k not in ("brand", "media_pack", "video", "latest_issue") and facts.get(k)]
            if rows:
                parts += ["", f"**{style.HEADINGS['stats']}**", *rows]
        elif item == "examples" and b:
            ex.ensure_seed(db, b.key)
            picks = ex.suggest(db, b.key, info.get("sector"), limit=5)
            if picks:
                parts += ["", f"**{style.HEADINGS['examples']}**", *[f"- {x.label}: {x.url}" for x in picks]]
        elif item == "events" and b:
            from app.models import SalesEdition
            tids = [t.id for t in db.scalars(select(SalesTitle).where(SalesTitle.slug.in_(b.title_slugs)))]
            evs = list(db.scalars(select(SalesEdition).where(SalesEdition.title_id.in_(tids), SalesEdition.kind.in_(("event", "awards")),
                                                             SalesEdition.edition_date >= date.today()).order_by(SalesEdition.edition_date).limit(4)))
            if evs:
                parts += ["", f"**{style.HEADINGS['events']}**", *[f"- {e.name}, {fmt_day(e.edition_date)}" for e in evs]]
        elif item == "free_options":
            parts += ["", f"**{style.HEADINGS['free_options']}**",
                      "- Send us your news (new partnerships, people joining) for the weekly newsletter - it's free.",
                      "- Comment in our features: if one in the features list fits, let me know and I'll put you in touch with the writer."]
        elif item == "media_pack" and facts.get("media_pack"):
            parts += ["", f"Everything is in our media pack: {facts['media_pack']}"]
    closing = sit.get("closing") if "call_offer" in include else ""
    if closing:
        parts += ["", closing]
    parts += ["", style.sign_off(prof, owner)]
    return "\n".join(parts).strip(), ai


# ---- the scan -----------------------------------------------------------------------------------------

def _details(db: Session, info: dict, msg: ParsedMessage, title: SalesTitle | None, contact: Contact | None, company: Company | None) -> list[dict]:
    who = " ".join(x for x in (info.get("contact_name") or msg.from_name, f"<{info.get('contact_email') or msg.from_address}>") if x)
    d = [{"label": "From", "value": who, **({"href": f"/contacts/{contact.id}"} if contact else {})},
         {"label": "Company", "value": company.name if company else (info.get("client_company") or "Not in the CRM yet - a new prospect"),
          **({"href": f"/companies/{company.id}"} if company else {})},
         {"label": "Subject", "value": msg.subject or "(no subject)"},
         {"label": "Type of request", "value": TYPES.get(info.get("request_type"), "General enquiry") + (" (through an agency)" if info.get("agency") else "")}]
    if title:
        d.append({"label": "Magazine", "value": title.name})
    for key, label in (("wants", "What they want"), ("budget", "Budget"), ("timing", "Timing")):
        if info.get(key):
            d.append({"label": label, "value": str(info[key])})
    if info.get("summary"):
        d.append({"label": "In short", "value": info["summary"]})
    if info.get("unchecked"):
        d.append({"label": "Worth knowing", "value": "The Brain isn't switched on, so this was picked up from the words it uses. Check it really is a request."})
    return d


def queue(db: Session, mailbox: str, owner: User | None, msg: ParsedMessage, info: dict) -> ReviewQueueItem:
    reply_to = (info.get("contact_email") or msg.from_address or "").strip()
    contact = find_contact_by_email(db, reply_to) if reply_to else None
    company = db.get(Company, contact.company_id) if contact and contact.company_id else None
    if not company and info.get("client_company"):
        company = db.scalars(select(Company).where(func.lower(Company.name) == info["client_company"].strip().lower())).first()
    title = _title_for(db, info.get("magazine"), owner)
    rates = pick_rates(db, title, info.get("wants"))
    draft, ai = compose(db, info, title, owner, msg.body_text or "", rates, msg.subject)
    received = msg.received_at
    item = ReviewQueueItem(
        id=uuid.uuid4(), kind=KIND, source_db=title.crm_source_db if title else None, status="pending",
        entity_type="contact" if contact else ("company" if company else None),
        entity_id=contact.id if contact else (company.id if company else None),
        payload={
            "summary": f"{info.get('client_company') or (company.name if company else None) or info.get('contact_name') or reply_to} "
                       f"is asking about {info.get('wants') or 'prices'}" + (f" - {short_name(title)}" if title else ""),
            "details": _details(db, info, msg, title, contact, company),
            "original_text": draft, "original_label": "Drafted reply",
            "source_context": f"From: {msg.from_name or ''} <{msg.from_address}>\nSubject: {msg.subject}\n\n{(msg.body_text or '')[:4000]}",
            "suggested_to": reply_to,
            "related_entities": ([{"type": "contact", "id": str(contact.id), "label": contact.full_name or reply_to}] if contact else [])
                                + ([{"type": "company", "id": str(company.id), "label": company.name}] if company else []),
            "mailbox": mailbox, "message_id": msg.message_id, "conversation_id": msg.conversation_id,
            "owner_user_id": str(owner.id) if owner else None,
            "title_id": str(title.id) if title else None, "rate_ids": [str(r.id) for r in rates],
            "request": {k: info.get(k) for k in ("request_type", "wants", "budget", "timing", "agency", "client_company",
                                                  "contact_name", "contact_email", "sector", "summary")},
            "ai_drafted": ai, "confidence": info.get("confidence"),
            "facets": {"magazine": short_name(title) if title else "Not sure",
                       "type": TYPES.get(info.get("request_type"), "General enquiry"),
                       "client": "In the CRM" if (contact or company) else "New prospect"},
            "sort_date": received.date().isoformat() if received else date.today().isoformat(),
        },
    )
    db.add(item)
    return item


def scan() -> None:
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        from app.graph_client import GraphRequestError, list_messages_since

        boxes = runtime_settings.get_csv(db, "proposal_request_mailboxes")
        if not boxes:
            logger.info("proposal requests: no inboxes listed - nothing to read")
            return
        domains = {d.strip().lower() for d in runtime_settings.get_csv(db, "email_summary_internal_domains")}
        cap = runtime_settings.get_int(db, "proposal_request_llm_max_per_run")
        used = 0
        seen = {r[0] for r in db.execute(select(ReviewQueueItem.payload["conversation_id"].astext).where(ReviewQueueItem.kind == KIND)) if r[0]}
        seen_msgs = {r[0] for r in db.execute(select(ReviewQueueItem.payload["message_id"].astext).where(ReviewQueueItem.kind == KIND)) if r[0]}
        for box in boxes:
            owner = _owner(db, box)
            key = f"proposal_requests:{box.lower()}"
            st = get_state(db, key)
            since = datetime.fromisoformat(st["last_processed_at"]) if st.get("last_processed_at") else \
                now - timedelta(minutes=runtime_settings.get_int(db, "proposal_request_lookback_minutes"))
            try:
                raw = list_messages_since(box, since.strftime("%Y-%m-%dT%H:%M:%SZ"))
            except GraphRequestError as exc:
                logger.error("proposal requests: inbox %s couldn't be read (HTTP %s)", box, exc.status_code)
                continue
            skip = set(st.get("last_message_ids", []))
            msgs = sorted((parse_message(m) for m in raw if m.get("id") not in skip), key=lambda m: m.received_at)
            done_upto, queued = None, 0
            for msg in msgs:
                if msg.message_id in seen_msgs or (msg.conversation_id and msg.conversation_id in seen) or not candidate(msg, box, domains):
                    done_upto = msg
                    continue
                if used >= cap:
                    break
                used += 1
                info = classify(db, msg)
                done_upto = msg
                if not info:
                    continue
                queue(db, box, owner, msg, info)
                if msg.conversation_id:
                    seen.add(msg.conversation_id)
                queued += 1
            if done_upto:
                set_state(db, key, {"last_processed_at": done_upto.received_at.isoformat(), "last_message_ids": [done_upto.message_id]})
            db.commit()
            logger.info("proposal requests: %s - %d read, %d queued", box, len(msgs), queued)
    finally:
        db.close()


# ---- acting on a card ---------------------------------------------------------------------------------

def _crm_records(db: Session, item: ReviewQueueItem) -> tuple[Contact | None, Company | None]:
    """The client in the CRM, adding them if they're new (only when someone acts on the card)."""
    p = item.payload
    req = p.get("request") or {}
    email = (p.get("suggested_to") or req.get("contact_email") or "").strip()
    contact = find_contact_by_email(db, email) if email else None
    company = db.get(Company, contact.company_id) if contact and contact.company_id else None
    title = db.get(SalesTitle, uuid.UUID(p["title_id"])) if p.get("title_id") else None
    source_db = (title.crm_source_db if title and title.crm_source_db else None) or MANUAL_SOURCE_DB
    name = (req.get("client_company") or "").strip()
    if not company and name:
        company = db.scalars(select(Company).where(func.lower(Company.name) == name.lower())).first()
        if not company:
            company = Company(id=uuid.uuid4(), source_db=source_db, source_act_id=str(uuid.uuid4()), name=name)
            db.add(company)
            db.flush()
    if not contact and email:
        full = (req.get("contact_name") or "").strip() or None
        parts = (full or "").split(maxsplit=1)
        contact = Contact(id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()), first_name=parts[0] if parts else None,
                          last_name=parts[1] if len(parts) > 1 else None, full_name=full or email, company_id=company.id if company else None,
                          custom_fields={})
        db.add(contact)
        db.flush()
        db.add(Email(id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()), contact_id=contact.id,
                     type_label="Business", address=email, is_primary=True))
    if contact and company and not contact.company_id:
        contact.company_id = company.id
    if not company and contact:
        company = Company(id=uuid.uuid4(), source_db=source_db, source_act_id=str(uuid.uuid4()), name=contact.full_name or email)
        db.add(company)
        db.flush()
        contact.company_id = company.id
    return contact, company


def _note(db: Session, entity_type: str, entity_id, body: str, user_id) -> None:
    db.add(Note(id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()), entity_type=entity_type, entity_id=entity_id,
                note_type="Proposal request", body=body, act_created_at=datetime.now(timezone.utc),
                created_by_user_id=uuid.UUID(user_id) if user_id else None))


def _send(db: Session, item: ReviewQueueItem, input_data: dict) -> None:
    from app.automations.sales_orders import _split_draft
    from app.models.messaging import MailAccount
    from app.services import outlook
    from app.services.mail_merge import to_html

    p = item.payload
    draft = (input_data.get("note") or "").strip() or p.get("original_text") or ""
    to = (input_data.get("to") or p.get("suggested_to") or "").strip()
    if not re.fullmatch(r"[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+", to):
        raise ValueError("Enter the email address to send this to.")
    actor = input_data.get("_actor_user_id")
    acct = db.scalar(select(MailAccount).where(MailAccount.user_id == uuid.UUID(actor))) if actor else None
    if not acct:
        raise ValueError("Connect your Outlook first (Settings › Email), or use “I'll reply myself” and send it from Outlook.")
    subject, body = _split_draft(draft)
    html = to_html(body)
    try:
        same_box = acct.email.lower() == (p.get("mailbox") or "").lower() and p.get("message_id")
        sent = False
        if same_box:
            try:
                outlook.reply_to(db, acct, p["message_id"], html_body=html, to=[to])
                sent = True
            except RuntimeError:
                sent = False   # the email was moved or deleted - send it as a new email instead
        if not sent:
            outlook.send_mail(db, acct, to=[to], subject=subject or "Thank you for your email", html_body=html)
    except outlook.OutlookAuthError as exc:
        raise ValueError(f"{exc} Reconnect Outlook in Settings, then try again.") from exc
    except outlook.RateLimited as exc:
        raise ValueError("Outlook is asking us to slow down - try again in a minute.") from exc
    except RuntimeError as exc:
        raise ValueError("Outlook didn't accept the email, so nothing was sent. Please try again.") from exc
    from app.proposals import style
    style.record_edit(db, uuid.UUID(actor), kind="reply", situation=(p.get("request") or {}).get("request_type"),
                      drafted=p.get("original_text"), sent=draft)
    contact, company = _crm_records(db, item)
    target = ("contact", contact.id) if contact else ("company", company.id) if company else (None, None)
    if target[0]:
        _note(db, target[0], target[1], f"Replied to a proposal request ({p.get('facets', {}).get('type', 'enquiry')}), sent to {to}.\n\n{body}", actor)


def make_proposal(db: Session, item: ReviewQueueItem, input_data: dict) -> uuid.UUID:
    """A full proposal from the request: the client (added if new), the magazine, the products quoted, sent as an email,
    with coming issues and the right examples ready to edit."""
    from app.api.routes.proposals import LineIn, ProposalCreate, create_proposal
    from app.models import Proposal

    p = item.payload
    actor = input_data.get("_actor_user_id")
    user = db.get(User, uuid.UUID(actor)) if actor else None
    if not user:
        raise ValueError("Sign in again, then try once more.")
    contact, company = _crm_records(db, item)
    if not company:
        raise ValueError("There's no client name or email on this request, so a proposal can't be started. Use Send reply instead.")
    title_id = uuid.UUID(p["title_id"]) if p.get("title_id") else None
    # One product for each thing they asked about (the first quoted), so the total means something; the rest are a click away.
    quoted = [r for r in (db.get(SalesRate, uuid.UUID(i)) for i in p.get("rate_ids") or []) if r and r.price_gbp is not None]
    firsts = list({r.section: r for r in reversed(quoted)}.values())[::-1][:4]
    lines = [LineIn(product=r.product, rate_id=r.id, source="rate_card", title_id=r.title_id) for r in firsts]
    try:
        out = create_proposal(ProposalCreate(company_id=company.id, contact_id=contact.id if contact else None, title_id=title_id, lines=lines,
                                             use_ai=True), db=db, user=user)
    except Exception as exc:   # an HTTPException from the builder carries a plain reason
        raise ValueError(getattr(exc, "detail", None) or "The proposal couldn't be started. Try again from Proposals.") from exc
    prop = db.get(Proposal, out.id)
    if not any(s.get("block") for s in prop.sections or []):
        from app.api.routes.proposals import _apply_style
        _apply_style(db, prop, user, standard=True)   # from a request: the standard blocks even without a profile
    sector = (p.get("request") or {}).get("sector")
    # The writer's own blocks are already in (their profile); point the examples at the client's sector.
    if sector:
        prop.sections = [{**s, "block": {**s["block"], "config": {**(s["block"].get("config") or {}), "sector": sector}}}
                         if (s.get("block") or {}).get("kind") == "examples" else s for s in prop.sections or []]
    prop.request_item_id = item.id
    item.payload = {**p, "proposal_id": str(prop.id), "open_href": f"/sales/proposals/{prop.id}",
                    "details": [{"label": "Proposal draft", "value": prop.campaign_name, "href": f"/sales/proposals/{prop.id}"}, *p["details"]]}
    return prop.id


def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "send":
        _send(db, item, input_data)
    elif action_id == "proposal":
        make_proposal(db, item, input_data)
    elif action_id == "replied":
        pass
    elif action_id == "not_request":
        pass
    else:
        raise ValueError(f"Unknown action {action_id!r} for {KIND}")


def _redraft(db: Session, item: ReviewQueueItem, extra: str) -> str:
    p = item.payload
    owner = db.get(User, uuid.UUID(p["owner_user_id"])) if p.get("owner_user_id") else None
    title = db.get(SalesTitle, uuid.UUID(p["title_id"])) if p.get("title_id") else None
    rates = [r for r in (db.get(SalesRate, uuid.UUID(i)) for i in p.get("rate_ids") or []) if r]
    body = (p.get("source_context") or "").split("\n\n", 1)[-1]
    subject = next((d["value"] for d in p.get("details", []) if d.get("label") == "Subject"), "")
    draft, _ = compose(db, p.get("request") or {}, title, owner, body, rates, subject, extra=extra)
    return draft


register(ReviewKind(
    kind=KIND,
    label="Proposal requests",
    description="Emails asking for prices, a media pack or a proposal, with a reply already drafted from the rate card and editorial plan.",
    actions=[
        ReviewAction(id="send", label="Send reply from my Outlook", style="primary", outcome="approved",
                     extra_fields=[ExtraField(key="to", label="Send to", placeholder="name@company.com", required=False)]),
        ReviewAction(id="proposal", label="Make a full proposal", style="secondary", outcome="approved"),
        ReviewAction(id="replied", label="I'll reply myself", style="secondary", outcome="approved"),
        ReviewAction(id="not_request", label="Not a proposal request", style="secondary", outcome="rejected"),
    ],
    handler=_handle,
    redraft=_redraft,
    audience="sales",
    facets=(("magazine", "Magazine"), ("type", "Type of request"), ("client", "Client")),
    date_sort_label="date received",
))

register_job(ScheduledJob(
    id="proposal_request_scan",
    label="Proposal requests",
    description="Reads the listed inboxes for emails asking for prices or a proposal, and drafts a reply for each.",
    cron="*/10 * * * *",
    func=scan,
    enabled_flag="automations_proposal_requests_enabled",
))


def _check_example_links() -> None:
    from app.models import ProposalExample
    from app.proposals.examples import check_links

    db = SessionLocal()
    try:
        rows = list(db.scalars(select(ProposalExample).where(ProposalExample.archived.is_(False))))
        broken = check_links(db, rows)
        db.commit()
        logger.info("example links: %d checked, %d broken", len(rows), broken)
    finally:
        db.close()


register_job(ScheduledJob(
    id="proposal_example_link_check",
    label="Proposal example links",
    description="Checks that the links in the proposal examples library still open.",
    cron="30 6 * * 1",
    func=_check_example_links,
    enabled_flag="automations_proposal_example_check_enabled",
))
