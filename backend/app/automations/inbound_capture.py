"""SALES-011 (Inbound Contact Capture) - see docs/build-spec.txt for the
full spec. Scans a shared enquiry mailbox for messages from senders who
don't match any existing contact, and queues a review item suggesting how
to add them: a guessed company (by email domain - see company_match.py),
a newsletter opt-in toggle, and up to three "suggested groups" drawn only
from a hand-curated allowlist (see group_allowlist.py) of real segment
groups, never the full noisy group table.

A mailbox configured with source_db "*" (rather than a real database
name) is treated as a genuinely shared/general inbox that isn't tied to
one brand - company/group suggestions are meaningless without knowing
which database to search, so those are skipped at scan time and the
reviewer picks the actual database themselves when confirming (see
_handle_create_contact) instead of the automation guessing wrong.

Same "draft, never dispatch" contract as every other automation here:
nothing is written to the CRM until a reviewer picks an action. In
particular the suggested company is only ever a pre-filled guess - the
reviewer confirms, overrides, or creates a new company themselves; group
suggestions are computed from whichever company the reviewer actually
settles on, not the automation's guess (see _handle_create_contact).

Deliberately narrow scope, same shape as email_summary.py's five gates:

  1. No contact match for the sender - already in the CRM isn't "inbound".
  2. Recipient count capped - a group thread isn't a new 1:1 enquiry.
  3. Not bounce/OOO-shaped (a bounce or auto-reply isn't a new lead).
  4. Body length floor - a one-line non-answer has nothing to capture.
  5. Sender isn't on a BMI-owned domain - internal mail isn't an inbound lead.
  6. One pending item per sender at a time - a second message from the same
     unmatched address before the first is reviewed doesn't queue again.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas import MANUAL_SOURCE_DB
from app.automations import runtime_settings
from app.automations.company_match import domain_of, suggest_company
from app.automations.contact_match import find_contact_by_email
from app.automations.group_allowlist import ALLOWLISTED_GROUPS, NEWSLETTER_GROUP, suggest_groups
from app.automations.mail_parsing import ParsedMessage, looks_like_bounce, looks_like_ooo, parse_message
from app.automations.registry import ExtraField, ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.automations.state import get_state, set_state
from app.db.session import SessionLocal
from app.graph_client import GraphRequestError, list_messages_since
from app.models import Company, Contact, Email, Group, GroupMembership, Note, ReviewQueueItem
from app.models.base import SOURCE_DBS

logger = logging.getLogger("app.automations.inbound_capture")


def _parse_mailbox_config(db: Session) -> list[tuple[str, str]]:
    """"mailbox:source_db" pairs from settings - source_db is one of
    SOURCE_DBS, or "*" for a genuinely shared/general inbox that isn't
    tied to one brand (see _handle_create_contact: the reviewer picks the
    actual database when confirming, since a company/group suggestion is
    meaningless without knowing which database to search). Malformed
    entries (no colon, an unrecognized source_db that isn't "*") are
    logged and skipped rather than crashing the whole scan over one typo."""
    pairs: list[tuple[str, str]] = []
    for raw in runtime_settings.get_csv(db, "graph_inbound_capture_mailboxes"):
        if ":" not in raw:
            logger.warning("inbound_capture: ignoring malformed mailbox entry %r (expected mailbox:source_db or mailbox:*)", raw)
            continue
        mailbox, source_db = raw.rsplit(":", 1)
        mailbox, source_db = mailbox.strip(), source_db.strip().lower()
        if not mailbox or not source_db:
            continue
        if source_db != "*" and source_db not in SOURCE_DBS:
            logger.warning("inbound_capture: ignoring mailbox %r - %r isn't a real database or \"*\"", mailbox, source_db)
            continue
        pairs.append((mailbox, source_db))
    return pairs


def _find_group(db: Session, source_db: str, name: str) -> Group | None:
    return db.query(Group).filter(Group.source_db == source_db, func.lower(Group.name) == name.strip().lower()).first() if name else None


def _find_or_create_company(db: Session, source_db: str, name: str) -> Company:
    existing = db.query(Company).filter(Company.source_db == source_db, func.lower(Company.name) == name.strip().lower()).first()
    if existing:
        return existing
    company = Company(id=uuid.uuid4(), source_db=source_db, source_act_id=str(uuid.uuid4()), name=name.strip())
    db.add(company)
    db.flush()
    return company


def _handle_create_contact(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "ignore":
        return
    if action_id != "create_contact":
        raise ValueError(f"Unknown action {action_id!r} for inbound_contact_unmatched")

    name = (input_data.get("name") or "").strip()
    if not name:
        raise ValueError("The new contact needs at least a name.")
    source_db = item.payload.get("source_db")
    sender_email = item.payload.get("sender_email")
    if source_db == "*":
        # A shared/general inbox isn't tied to one brand - the mailbox
        # config couldn't tell us which database this belongs to, so the
        # scan queued this without a company/group guess and the reviewer
        # picks it now, same "never guess what we can't know" rule as
        # everywhere else here.
        chosen = (input_data.get("source_db") or "").strip().lower()
        if chosen not in SOURCE_DBS:
            raise ValueError(f"This came in on a shared inbox - pick which database it belongs to ({', '.join(SOURCE_DBS)}).")
        source_db = chosen
    elif not source_db:
        raise ValueError("This item is missing its source database - it may be stale.")

    company_name = (input_data.get("company_name") or "").strip()
    company = _find_or_create_company(db, source_db, company_name) if company_name else None

    parts = name.split(maxsplit=1)
    contact = Contact(
        id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()),
        first_name=parts[0], last_name=parts[1] if len(parts) > 1 else None, full_name=name,
        company_id=company.id if company else None, custom_fields={},
    )
    db.add(contact)
    db.flush()

    if sender_email:
        db.add(Email(id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()),
                      contact_id=contact.id, type_label="Business", address=sender_email, is_primary=True))

    # Whatever the reviewer typed (pre-filled from suggestions computed
    # against the company they actually confirmed/created) is only ever
    # applied if it resolves to a real, allowlisted group - a typo or a
    # non-allowlisted name is silently skipped, never created as a new group.
    requested_names = {n.strip().lower() for n in (input_data.get("groups") or "").split(",") if n.strip()}
    for group_name in requested_names:
        if group_name not in ALLOWLISTED_GROUPS.get(source_db, set()):
            continue
        group = _find_group(db, source_db, group_name)
        if group:
            db.add(GroupMembership(id=uuid.uuid4(), group_id=group.id, contact_id=contact.id))

    if (input_data.get("newsletter") or "").lower() == "true":
        newsletter_name = NEWSLETTER_GROUP.get(source_db)
        newsletter_group = _find_group(db, source_db, newsletter_name) if newsletter_name else None
        if newsletter_group:
            db.add(GroupMembership(id=uuid.uuid4(), group_id=newsletter_group.id, contact_id=contact.id))

    db.add(Note(
        id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()),
        entity_type="contact", entity_id=contact.id, note_type="Inbound enquiry",
        body=f"Captured from an inbound email to a monitored mailbox.\n\nOriginal message:\n{item.payload.get('original_text', '(not captured)')}",
        act_created_at=datetime.now(timezone.utc),
    ))
    item.entity_type, item.entity_id = "contact", contact.id


register(ReviewKind(
    kind="inbound_contact_unmatched",
    label="New inbound contact",
    description="An email arrived from a sender with no existing contact match - review and capture them as a new contact.",
    actions=[
        ReviewAction(
            id="create_contact", label="Create contact", style="primary", outcome="approved",
            extra_fields=[
                ExtraField(key="name", label="Full name", placeholder="Jane Smith"),
                ExtraField(
                    key="source_db", label="Database (only needed for a shared inbox)",
                    placeholder=f"{' / '.join(SOURCE_DBS)}", required=False,
                ),
                ExtraField(key="company_name", label="Company", placeholder="(suggested company, or type a different one)", required=False),
                ExtraField(key="groups", label="Groups to add (comma-separated)", placeholder="e.g. Leeds, Technology", required=False),
                ExtraField(key="newsletter", label="Subscribe to newsletter", field_type="bool", required=False),
            ],
        ),
        ReviewAction(id="ignore", label="Not a lead, ignore", style="secondary", outcome="rejected"),
    ],
    handler=_handle_create_contact,
))


def _looks_like_new_enquiry(db: Session, msg: ParsedMessage, internal_domains: set[str]) -> bool:
    if msg.recipient_count > runtime_settings.get_int(db, "inbound_capture_max_recipients"):
        return False
    if looks_like_bounce(msg) or looks_like_ooo(msg):
        return False
    if msg.headers.get("list-unsubscribe", ""):
        return False
    if len(msg.body_text.strip()) < runtime_settings.get_int(db, "inbound_capture_min_body_chars"):
        return False
    if domain_of(msg.from_address) in internal_domains:
        return False
    return True


def scan_inbound_contacts() -> None:
    """SALES-011 producer: reads each configured enquiry mailbox, and for
    every new message from a sender with no existing contact match, queues
    one `inbound_contact_unmatched` review item with a best-effort company
    guess and curated group suggestions attached. Same incremental-cursor,
    per-mailbox-failure-isolation pattern as the other mailbox scans.
    """
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        mailbox_pairs = _parse_mailbox_config(db)
        if not mailbox_pairs:
            logger.info("inbound_capture scan: no mailboxes configured (GRAPH_INBOUND_CAPTURE_MAILBOXES / Automations Settings) - nothing to scan.")
            return

        internal_domains = {d.strip().lower() for d in runtime_settings.get_csv(db, "email_summary_internal_domains") if d.strip()}
        pending_senders = {
            (row.payload or {}).get("sender_email", "").lower()
            for row in db.scalars(
                select(ReviewQueueItem).where(ReviewQueueItem.kind == "inbound_contact_unmatched", ReviewQueueItem.status == "pending")
            ).all()
        }

        total_queued = 0
        for mailbox, source_db in mailbox_pairs:
            # Keyed by (mailbox, source_db), not mailbox alone - someone
            # with access to more than one database (per BMI's real access
            # sheet: several people appear once per database they can see)
            # needs the SAME mailbox scanned once per database, each with
            # its own independent "since last run" position. Keying by
            # mailbox alone would mean the second entry for that address
            # reads the cursor the first entry just advanced past, so it
            # would never see anything new again after its very first run.
            cursor_key = f"inbound_capture_scan:{mailbox}:{source_db}"
            state = get_state(db, cursor_key)
            last_processed_at = state.get("last_processed_at")
            skip_ids = set(state.get("last_message_ids", []))
            since_dt = (
                datetime.fromisoformat(last_processed_at)
                if last_processed_at
                else now - timedelta(minutes=runtime_settings.get_int(db, "inbound_capture_initial_lookback_minutes"))
            )
            since_iso = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            try:
                raw_messages = list_messages_since(mailbox, since_iso)
            except GraphRequestError as exc:
                logger.error("inbound_capture scan: mailbox %s failed (HTTP %s): %s", mailbox, exc.status_code, exc)
                continue

            parsed = [parse_message(m) for m in raw_messages if m.get("id") not in skip_ids]
            queued_this_mailbox = 0

            for msg in parsed:
                sender = (msg.from_address or "").lower()
                if not sender or sender in pending_senders:
                    continue
                if not _looks_like_new_enquiry(db, msg, internal_domains):
                    continue
                if find_contact_by_email(db, msg.from_address):
                    continue

                is_shared_inbox = source_db == "*"
                company = None if is_shared_inbox else suggest_company(db, source_db, msg.from_address)
                suggested_groups = suggest_groups(db, source_db, company.id) if company else []
                newsletter_name = None if is_shared_inbox else NEWSLETTER_GROUP.get(source_db)

                details = [
                    {"key": "sender_email", "label": "From", "value": msg.from_address or "-"},
                    {"key": "subject", "label": "Subject", "value": msg.subject},
                ]
                if is_shared_inbox:
                    details.append({
                        "key": "database", "label": "Database",
                        "value": f"Unknown - shared inbox, pick one when confirming ({', '.join(SOURCE_DBS)})",
                    })
                else:
                    details.extend([
                        {"key": "suggested_company", "label": "Suggested company", "value": company.name if company else "(none - no domain match)"},
                        {"key": "suggested_groups", "label": "Suggested groups", "value": ", ".join(g.name for g in suggested_groups) or "(none)"},
                        {"key": "newsletter_group", "label": "Newsletter group for this database", "value": newsletter_name or "(none configured)"},
                    ])

                db.add(ReviewQueueItem(
                    id=uuid.uuid4(), kind="inbound_contact_unmatched",
                    entity_type=None, entity_id=None,
                    payload={
                        "summary": f"New inbound contact: {msg.from_address or '(unknown sender)'}"
                                   + (f" - looks like {company.name}" if company else ""),
                        "details": details,
                        "original_text": msg.body_text,
                        "sender_email": msg.from_address,
                        "source_db": source_db,
                        "message_id": msg.message_id,
                        "confidence": 0.6 if company else 0.35,
                    },
                ))
                pending_senders.add(sender)
                queued_this_mailbox += 1

            if parsed:
                max_ts = max(m.received_at for m in parsed)
                ids_at_max = [m.message_id for m in parsed if m.received_at == max_ts]
                set_state(db, cursor_key, {"last_processed_at": max_ts.isoformat(), "last_message_ids": ids_at_max})

            logger.info(
                "inbound_capture scan: mailbox %s (%s) - %d message(s) read, %d queued",
                mailbox, source_db, len(parsed), queued_this_mailbox,
            )
            total_queued += queued_this_mailbox

        db.commit()
        logger.info("inbound_capture scan finished: %d total item(s) queued across %d mailbox(es)", total_queued, len(mailbox_pairs))
    finally:
        db.close()


register_job(ScheduledJob(
    id="sales011_inbound_capture_scan",
    label="Inbound contact capture scan",
    description="Scans enquiry mailboxes for messages from unmatched senders and suggests capturing them as new contacts (SALES-011).",
    cron="*/30 * * * *",
    func=scan_inbound_contacts,
    enabled_flag="automations_inbound_capture_scan_enabled",
    cursor_prefix="inbound_capture_scan:",
))
