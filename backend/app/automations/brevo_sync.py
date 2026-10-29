"""Brevo, where the newsletters go out from (app/services/brevo.py for the calls).

Unsubscribes, both ways ("Brevo > Keep unsubscribes in step with Brevo"):
  - From BMI Brain to Brevo: when someone is unsubscribed on a Subscription changes card, they're unsubscribed in
    Brevo too - from every Brevo email when they asked to stop everything, otherwise taken off that title's newsletter
    list ("Brevo list for each magazine"). The card says what happened in Brevo, and if Brevo couldn't be updated.
  - From Brevo to BMI Brain: every hour, people who unsubscribed from Brevo's own emails since the last look are marked
    unsubscribed on every record with their address, and people who left a title's list are taken off that title's
    newsletter group. An unsubscribe has to be honoured, so this happens by itself, recorded in the field history and
    noted on the contact.

SALES-004 coverage forwarding ("Brevo > Spot clients in the newsletters"):
  Every few hours, newsletters Brevo has sent since the last look are read for the names of BMI's clients (companies
  with a booking in the last two years). Each salesperson gets one card per newsletter for their clients in it, with a
  short "you're in our newsletter" note drafted, opened as a mail merge to check and send.
"""
from __future__ import annotations

import html
import logging
import re
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.automations.group_allowlist import NEWSLETTER_GROUP
from app.automations.registry import ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.automations.state import get_state, set_state
from app.db.session import SessionLocal
from app.models import Company, Contact, Email, Group, GroupMembership, Note, ReviewQueueItem, SalesOrder, SalesRep, User

logger = logging.getLogger("app.automations.brevo_sync")

COVERAGE_KIND = "newsletter_coverage"
UNSUB_STATE = "brevo_unsubscribes"
COVERAGE_STATE = "brevo_coverage"
LIST_LIMIT = 15
MIN_NAME = 5
_SUFFIX = re.compile(r"\b(ltd|limited|plc|llc|inc|group|uk|gmbh|sa|bv|co)\.?$", re.I)
TITLE_NAME = {"sellingtravel": "Selling Travel", "prospects": "The Business Travel Magazine", "onboard": "Onboard Hospitality"}


def title_lists(db: Session) -> dict[str, int]:
    """{database: Brevo list id} from "Brevo list for each magazine" ("sellingtravel:12, prospects:7")."""
    out = {}
    for pair in runtime_settings.get_csv(db, "brevo_title_lists"):
        db_key, _, list_id = pair.partition(":")
        if db_key.strip() and list_id.strip().isdigit():
            out[db_key.strip().lower()] = int(list_id.strip())
    return out


def _addresses(db: Session, contact_ids) -> list[str]:
    return sorted({a.lower() for (a,) in db.execute(select(Email.address).where(Email.contact_id.in_(list(contact_ids)))) if a})


# ---- BMI Brain to Brevo ---------------------------------------------------------------------------------------------

def push_unsubscribe(db: Session, contacts: list[Contact], *, everything: bool, source_db: str | None) -> str:
    """Makes an unsubscribe done in BMI Brain in Brevo too. Returns one plain line for the card saying what happened."""
    from app.services import brevo
    if not runtime_settings.get_bool(db, "automations_brevo_unsubscribes_enabled") or not brevo.configured():
        return "Unsubscribe them in Brevo by hand too: Brevo isn't connected to BMI Brain yet."
    emails = _addresses(db, [c.id for c in contacts])
    if not emails:
        return "No email address on their record, so nothing to change in Brevo."
    list_id = None if everything else title_lists(db).get((source_db or "").lower())
    if not everything and not list_id:
        return f"Unsubscribe them from the {TITLE_NAME.get(source_db or '', 'title')} list in Brevo by hand: no Brevo list is set for it (Automations > Settings > Brevo)."
    try:
        found = [brevo.update_contact(e, blacklist=everything, remove_from=None if everything else [list_id]) for e in emails]
    except brevo.BrevoError as exc:
        return f"{exc} Unsubscribe them in Brevo by hand."
    if not any(found):
        return "They're not in Brevo, so nothing to change there."
    return "Unsubscribed from every Brevo email too." if everything else "Taken off the title's Brevo list too."


# ---- Brevo to BMI Brain ---------------------------------------------------------------------------------------------

def apply_from_brevo(db: Session, people: list[dict], lists: dict[str, int]) -> tuple[int, int]:
    """(records marked unsubscribed, taken off a newsletter group) from Brevo's changed contacts."""
    from app.services.field_audit import record_field_changes
    by_list = {v: k for k, v in lists.items()}
    marked = removed = 0
    for p in people:
        email = (p.get("email") or "").strip().lower()
        if not email:
            continue
        records = list(db.scalars(select(Contact).join(Email, Email.contact_id == Contact.id).where(func.lower(Email.address) == email)))
        if p.get("emailBlacklisted"):
            for c in records:
                if c.is_unsubscribed:
                    continue
                record_field_changes(db, entity_type="contact", entity_id=c.id, before={"is_unsubscribed": False},
                                     updates={"is_unsubscribed": True}, changed_by_user_id=None)
                c.is_unsubscribed = True
                db.add(Note(id=uuid.uuid4(), source_db=c.source_db, source_act_id=str(uuid.uuid4()), entity_type="contact", entity_id=c.id,
                            note_type="Subscription", body="Unsubscribed from BMI's emails in Brevo, so marked unsubscribed here too.",
                            act_created_at=datetime.now(timezone.utc)))
                marked += 1
        for list_id in p.get("listUnsubscribed") or []:
            db_key = by_list.get(int(list_id))
            group_name = NEWSLETTER_GROUP.get(db_key or "")
            if not group_name:
                continue
            group = db.scalars(select(Group).where(Group.source_db == db_key, func.lower(Group.name) == group_name.lower())).first()
            for c in records:
                if group and c.source_db == db_key and db.execute(delete(GroupMembership).where(
                        GroupMembership.group_id == group.id, GroupMembership.contact_id == c.id)).rowcount:
                    db.add(Note(id=uuid.uuid4(), source_db=c.source_db, source_act_id=str(uuid.uuid4()), entity_type="contact", entity_id=c.id,
                                note_type="Subscription", body=f"Left the {TITLE_NAME.get(db_key, db_key)} newsletter list in Brevo, so taken off the {group.name} group.",
                                act_created_at=datetime.now(timezone.utc)))
                    removed += 1
    return marked, removed


def sync_unsubscribes() -> None:
    from app.services import brevo
    if not brevo.configured():
        logger.info("brevo: no key on the server - nothing to read")
        return
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        st = get_state(db, UNSUB_STATE)
        since = datetime.fromisoformat(st["since"]) if st.get("since") else now - timedelta(days=runtime_settings.get_int(db, "brevo_first_look_back_days"))
        try:
            people, carry_on = brevo.contacts_changed_since(since, offset=int(st.get("offset") or 0))
        except brevo.BrevoError as exc:
            logger.warning("brevo: unsubscribes not read (%s)", exc)
            return
        marked, removed = apply_from_brevo(db, people, title_lists(db))
        # a very long first read carries on next time from where it stopped; otherwise the next read starts from now
        set_state(db, UNSUB_STATE, {"since": since.isoformat(), "offset": carry_on} if carry_on else {"since": (now - timedelta(minutes=5)).isoformat()})
        db.commit()
        logger.info("brevo: %d changed contacts read, %d marked unsubscribed, %d taken off a newsletter group", len(people), marked, removed)
    finally:
        db.close()


# ---- SALES-004: clients in the newsletters -------------------------------------------------------------------------------

def _text(html_content: str) -> str:
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html_content or "", flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()


def _core(name: str) -> str:
    """"Gate Gourmet Ltd" -> "Gate Gourmet" - the part a newsletter would print."""
    n = name.strip()
    for _ in range(2):
        n = _SUFFIX.sub("", n).strip(" ,.-")
    return n


def clients_in(db: Session, text: str) -> list[Company]:
    """Clients (a booking in the last two years) whose name appears in the newsletter, as whole words."""
    since = date.today() - timedelta(days=730)
    ids = {r[0] for r in db.execute(select(SalesOrder.company_id).where(SalesOrder.company_id.isnot(None), SalesOrder.status != "cancelled",
                                                                       SalesOrder.booked_on >= since))}
    low = f" {text.lower()} "
    out = []
    for co in db.scalars(select(Company).where(Company.id.in_(ids))) if ids else []:
        core = _core(co.name)
        if len(core) < MIN_NAME or core.lower() in {"selling travel", "onboard hospitality", "business travel"}:
            continue
        if re.search(r"(?<![\w&])" + re.escape(core.lower()) + r"(?![\w&])", low):
            out.append(co)
    return out


def _owner(db: Session, co: Company) -> User | None:
    if co.owner_user_id:
        u = db.get(User, co.owner_user_id)
        if u:
            return u
    rep_id = db.scalar(select(SalesOrder.rep_id).where(SalesOrder.company_id == co.id, SalesOrder.rep_id.isnot(None))
                       .order_by(SalesOrder.booked_on.desc().nullslast()))
    rep = db.get(SalesRep, rep_id) if rep_id else None
    return db.get(User, rep.user_id) if rep and rep.user_id else None


def _person(db: Session, co: Company) -> Contact | None:
    from app.models import SalesDeal
    deal_contact = db.scalar(select(SalesDeal.contact_id).where(SalesDeal.company_id == co.id, SalesDeal.contact_id.isnot(None))
                             .order_by(SalesDeal.created_at.desc()))
    c = db.get(Contact, deal_contact) if deal_contact else None
    if c and not c.is_unsubscribed:
        return c
    people = db.execute(select(Contact).join(Email, Email.contact_id == Contact.id)
                        .where(Contact.company_id == co.id, Contact.is_unsubscribed.is_(False), Contact.has_bounced.is_(False))
                        .order_by(Email.is_primary.desc())).scalars().all()
    return next((p for p in people if re.search(r"market|brand|trade|partner|commercial", p.job_title or "", re.I)), people[0] if people else None)


def coverage_cards(db: Session, campaign: dict) -> list[ReviewQueueItem]:
    """One card per salesperson for their clients in one newsletter."""
    name = campaign.get("subject") or campaign.get("name") or "our newsletter"
    link = campaign.get("shareLink") or ""
    found = clients_in(db, _text(campaign.get("htmlContent") or ""))
    by_owner: dict = defaultdict(list)
    for co in found:
        owner = _owner(db, co)
        by_owner[owner.id if owner else None].append(co)
    subject = f"You're in our newsletter: {name}"
    body = ("Dear {{salutation|colleague}},\n\nJust to let you know, {{company}} features in our latest newsletter, "
            f"\"{name}\"" + (f", which you can see here:\n{link}" if link else ".") +
            "\n\nPlease feel free to share it with your team and on social media.\n\nKind regards,\n{{my_name}}")
    sent = (campaign.get("sentDate") or "")[:10] or date.today().isoformat()
    cards = []
    for owner_id, companies in by_owner.items():
        owner = db.get(User, owner_id) if owner_id else None
        people = [(co, _person(db, co)) for co in companies]
        reach = [(co, p) for co, p in people if p]
        details = [{"label": "Newsletter", "value": name, **({"href": link} if link else {})}, {"label": "Sent", "value": sent}]
        details += [{"label": co.name, "value": p.full_name or "Contact", "href": f"/companies/{co.id}"} for co, p in reach[:LIST_LIMIT]]
        if len(reach) > LIST_LIMIT:
            details.append({"label": "And", "value": f"{len(reach) - LIST_LIMIT} more - all listed in the mail merge"})
        nobody = [co.name for co, p in people if not p]
        if nobody:
            details.append({"label": "No one to email at", "value": ", ".join(sorted(nobody))[:500]})
        if not link:
            details.append({"label": "Worth knowing", "value": "Brevo didn't give a link to this newsletter, so the note doesn't include one. Add it if you have it."})
        card = ReviewQueueItem(
            id=uuid.uuid4(), kind=COVERAGE_KIND, source_db=None, status="pending",
            payload={
                "summary": f"{len(companies)} of your client{'s' if len(companies) != 1 else ''} in \"{name}\"",
                "details": details, "original_text": f"Subject: {subject}\n\n{body}", "original_label": "Drafted note",
                "campaign_id": campaign.get("id"), "owner_user_id": str(owner.id) if owner else None,
                "merge": {"contact_ids": [str(p.id) for _, p in reach], "subject": subject, "body": body, "label": f"Newsletter: {name}"[:300]},
                "hidden_actions": [] if reach else ["open_merge"],
                "related_entities": [{"type": "company", "id": str(co.id), "label": co.name} for co in companies[:LIST_LIMIT]],
                "facets": {"salesperson": (owner.name or owner.email) if owner else "No one", "reach": "Someone to email" if reach else "No one to email"},
                "sort_date": sent,
            })
        db.add(card)
        cards.append(card)
    return cards


def scan_coverage() -> None:
    from app.services import brevo
    if not brevo.configured():
        logger.info("brevo: no key on the server - no newsletters to read")
        return
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        st = get_state(db, COVERAGE_STATE)
        since = datetime.fromisoformat(st["since"]) if st.get("since") else now - timedelta(days=2)
        seen = set(st.get("seen") or [])
        try:
            campaigns = brevo.sent_campaigns(since, now)
        except brevo.BrevoError as exc:
            logger.warning("brevo: newsletters not read (%s)", exc)
            return
        made = 0
        for c in campaigns:
            if c.get("id") in seen:
                continue
            seen.add(c.get("id"))
            made += len(coverage_cards(db, c))
        set_state(db, COVERAGE_STATE, {"since": (now - timedelta(minutes=10)).isoformat(), "seen": sorted(seen, key=str)[-500:]})
        db.commit()
        logger.info("brevo: %d newsletters read, %d cards", len(campaigns), made)
    finally:
        db.close()


def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "open_merge":
        item.payload = {**item.payload, "open_href": f"/mail-merge?review={item.id}"}
    elif action_id != "not_needed":
        raise ValueError("That button isn't available on this card.")


register(ReviewKind(
    kind=COVERAGE_KIND,
    label="Clients in the newsletter",
    description="Your clients named in a newsletter Brevo has just sent, with a short note drafted to tell them, sent as a mail merge.",
    actions=[
        ReviewAction(id="open_merge", label="Open as a mail merge", style="primary", outcome="approved"),
        ReviewAction(id="not_needed", label="No need this time", style="secondary", outcome="dismissed", reopenable=True),
    ],
    handler=_handle,
    audience="sales",
    facets=(("salesperson", "Salesperson"), ("reach", "Contact")),
    date_sort_label="date sent",
))

register_job(ScheduledJob(
    id="brevo_unsubscribe_sync",
    label="Brevo unsubscribes",
    description="Every hour, marks people who unsubscribed in Brevo as unsubscribed here too.",
    cron="5 * * * *",
    func=sync_unsubscribes,
    enabled_flag="automations_brevo_unsubscribes_enabled",
))

register_job(ScheduledJob(
    id="brevo_coverage_scan",
    label="Clients in the newsletter",
    description="Reads the newsletters Brevo has sent for the names of BMI's clients, and drafts a note to tell them.",
    cron="50 */3 * * *",
    func=scan_coverage,
    enabled_flag="automations_brevo_coverage_enabled",
))
