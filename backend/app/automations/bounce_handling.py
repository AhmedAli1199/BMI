"""Review kinds for CS-001 (bounce classification) and CS-002 (out-of-office
replacement mining) - see docs/build-spec.txt for the full automation spec.

scan_mailbox_for_bounces_and_ooo() at the bottom is the real producer: it
reads each configured mailbox via Microsoft Graph (app-only, see
graph_client.py), classifies each new message with cheap heuristics first
(mail_parsing.py) and an OpenAI call only when heuristics alone aren't
enough to decide, then writes one of the three review kinds below.
Nothing here ever unsubscribes a contact or sends anything on its own -
every message that looks bounce/OOO-shaped becomes a queued suggestion,
same "draft, never dispatch" contract as every other automation.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import MANUAL_SOURCE_DB
from app.automations.contact_match import find_contact_by_email
from app.automations.llm import extract_json
from app.automations.mail_parsing import ParsedMessage, looks_like_bounce, looks_like_ooo, parse_message
from app.automations import runtime_settings
from app.automations.registry import ExtraField, ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.automations.state import get_state, set_state
from app.db.session import SessionLocal
from app.graph_client import GraphRequestError, list_messages_since
from app.models import Contact, Email, Note, ReviewQueueItem

logger = logging.getLogger("app.automations.bounce_handling")


def _add_note(db: Session, contact: Contact, note_type: str, body: str) -> None:
    db.add(
        Note(
            id=uuid.uuid4(),
            source_db=MANUAL_SOURCE_DB,
            source_act_id=str(uuid.uuid4()),
            entity_type="contact",
            entity_id=contact.id,
            note_type=note_type,
            body=body,
            act_created_at=datetime.now(timezone.utc),
        )
    )


def _get_contact_or_raise(db: Session, contact_id) -> Contact:
    contact = db.get(Contact, contact_id) if contact_id else None
    if not contact:
        raise ValueError("That contact no longer exists - it may have been deleted or merged since this was queued.")
    return contact


def _handle_bounce_uncertain(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    """A reply looked like it might be a bounce, but confidence was too low
    to action automatically. `item.entity_id` is the contact the automation
    guessed at, if any."""
    if action_id == "confirm_hard_bounce":
        contact = _get_contact_or_raise(db, item.entity_id)
        contact.is_unsubscribed = True
        note = input_data.get("note", "").strip()
        _add_note(
            db, contact, "Bounce",
            f"Hard bounce confirmed via review queue."
            f"{f' Reviewer note: {note}' if note else ''}"
            f"\n\nOriginal message:\n{item.payload.get('original_text', '(not captured)')}",
        )
    elif action_id == "not_a_bounce":
        pass  # No CRM write - the reviewer is telling us our guess was wrong.
    else:
        raise ValueError(f"Unknown action {action_id!r} for bounce_uncertain")


def _handle_bounce_unmatched(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    """A hard bounce came in but we couldn't confidently match it to an
    existing contact - the failed email address is in the payload, not
    entity_id (there's no entity yet)."""
    if action_id == "match_contact":
        contact_id = input_data.get("contact_id")
        if not contact_id:
            raise ValueError("Pick which contact this bounce actually belongs to.")
        contact = _get_contact_or_raise(db, contact_id)
        contact.is_unsubscribed = True
        failed_address = item.payload.get("details", [{}])[0].get("value", "unknown address")
        _add_note(
            db, contact, "Bounce",
            f"Hard bounce for {failed_address} matched to this contact via review queue "
            f"(automatic match wasn't confident enough).",
        )
        item.entity_type, item.entity_id = "contact", contact.id
    elif action_id == "ignore":
        pass
    else:
        raise ValueError(f"Unknown action {action_id!r} for bounce_unmatched")


def _handle_ooo_ambiguous(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    """An out-of-office/auto-reply where we couldn't confidently tell a
    temporary absence from a genuine handover. item.entity_id is the
    ORIGINAL contact who's away; payload["suggested_contact"] (if any) is
    our best guess at who they named as a replacement."""
    original = _get_contact_or_raise(db, item.entity_id)

    if action_id == "confirm_replacement":
        contact_id = input_data.get("contact_id") or (item.payload.get("suggested_contact") or {}).get("id")
        if not contact_id:
            raise ValueError("Pick who the replacement actually is.")
        replacement = _get_contact_or_raise(db, contact_id)
        _add_note(db, original, "Handover", f"Redirected to {replacement.full_name or replacement.first_name} per out-of-office reply.")
        _add_note(db, replacement, "Handover", f"Named as {original.full_name or original.first_name}'s replacement per their out-of-office reply.")
    elif action_id == "create_new_contact":
        name = input_data.get("name", "").strip()
        email = input_data.get("email", "").strip()
        if not name:
            raise ValueError("The new contact needs at least a name.")
        parts = name.split(maxsplit=1)
        new_contact = Contact(
            id=uuid.uuid4(),
            source_db=MANUAL_SOURCE_DB,
            source_act_id=str(uuid.uuid4()),
            first_name=parts[0],
            last_name=parts[1] if len(parts) > 1 else None,
            full_name=name,
            company_id=original.company_id,
            custom_fields={},
        )
        db.add(new_contact)
        db.flush()
        if email:
            db.add(Email(id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()),
                          contact_id=new_contact.id, type_label="Business", address=email, is_primary=True))
        _add_note(db, original, "Handover", f"Replacement {name} created from out-of-office reply.")
        _add_note(db, new_contact, "Handover", f"Created as {original.full_name or original.first_name}'s replacement per their out-of-office reply.")
    elif action_id == "temporary_ignore":
        pass
    else:
        raise ValueError(f"Unknown action {action_id!r} for ooo_ambiguous")


register(ReviewKind(
    kind="bounce_uncertain",
    label="Uncertain bounce",
    description="An email reply that looked like it might be a bounce, but confidence was too low to act on automatically.",
    actions=[
        ReviewAction(id="confirm_hard_bounce", label="Confirm & unsubscribe", style="primary", outcome="approved", requires_note=False),
        ReviewAction(id="not_a_bounce", label="Not a bounce, ignore", style="secondary", outcome="rejected"),
    ],
    handler=_handle_bounce_uncertain,
))

register(ReviewKind(
    kind="bounce_unmatched",
    label="Bounce, no contact match",
    description="A hard bounce came in but we couldn't confidently match it to an existing contact.",
    actions=[
        ReviewAction(id="match_contact", label="Match to a contact", style="primary", outcome="approved", requires_contact_picker=True),
        ReviewAction(id="ignore", label="Ignore", style="secondary", outcome="rejected"),
    ],
    handler=_handle_bounce_unmatched,
))

register(ReviewKind(
    kind="ooo_ambiguous",
    label="Out-of-office needs review",
    description="An out-of-office or auto-reply where we couldn't confidently tell a temporary absence from a genuine handover.",
    actions=[
        ReviewAction(id="confirm_replacement", label="Confirm replacement", style="primary", outcome="approved", requires_contact_picker=True),
        ReviewAction(
            id="create_new_contact", label="Create as new contact", style="primary", outcome="approved",
            extra_fields=[
                ExtraField(key="name", label="Full name", placeholder="Jane Smith"),
                ExtraField(key="email", label="Email", placeholder="jane@company.com", required=False),
            ],
        ),
        ReviewAction(id="temporary_ignore", label="Just temporary, ignore", style="secondary", outcome="rejected"),
    ],
    handler=_handle_ooo_ambiguous,
))


def _scan_mailboxes(db: Session) -> list[str]:
    return runtime_settings.get_csv(db, "graph_scan_mailboxes")


_BOUNCE_SEVERITY_PROMPT = (
    "You classify automated email bounce/delivery-failure notifications. Given the subject and body "
    "of one such message, decide whether the failure is PERMANENT (\"hard\" - address doesn't exist, "
    "domain not found, mailbox disabled/closed - safe to stop emailing this address) or TEMPORARY "
    "(\"soft\" - mailbox full, server busy, greylisting, rate limited - worth retrying later, not a "
    "reason to unsubscribe anyone). Return JSON of the exact shape: "
    '{"severity": "hard" or "soft", "confidence": a number from 0.0 to 1.0}.'
)

_OOO_EXTRACTION_PROMPT = (
    "You read out-of-office / automatic-reply emails. Extract who, if anyone, the sender named as a "
    "replacement or alternative point of contact while they're away. Use null for anything not "
    "mentioned - never invent a name or address. Return JSON of the exact shape: "
    '{"replacement_name": string or null, "replacement_email": string or null}.'
)


def _classify_bounce_severity(msg: ParsedMessage) -> tuple[str, float]:
    result = extract_json(_BOUNCE_SEVERITY_PROMPT, f"Subject: {msg.subject}\n\nBody:\n{msg.body_text}")
    if result and result.get("severity") in ("hard", "soft"):
        try:
            return result["severity"], max(0.0, min(1.0, float(result.get("confidence", 0.5))))
        except (TypeError, ValueError):
            pass
    # No AI configured, or the call failed/returned something unusable - an
    # NDR-shaped subject already matched to get here, so default to "hard"
    # but at a confidence too low to look any more certain than a guess,
    # since severity still decides only wording here, not any auto-action.
    return "hard", 0.4


def _extract_ooo_replacement(msg: ParsedMessage) -> tuple[str | None, str | None]:
    result = extract_json(_OOO_EXTRACTION_PROMPT, f"Subject: {msg.subject}\n\nBody:\n{msg.body_text}")
    if not result:
        return None, None
    name = (result.get("replacement_name") or "").strip() or None
    email = (result.get("replacement_email") or "").strip() or None
    return name, email


def _handle_candidate_bounce(db: Session, msg: ParsedMessage) -> bool:
    """Queues a review item for a message that looks like a delivery-failure
    notification. Always queues - even a maximally-confident hard bounce
    still needs a human to click "confirm & unsubscribe" (see
    _handle_bounce_uncertain above); nothing here writes to Contact
    directly. Returns True if something was queued."""
    failed_address = msg.failed_recipients[0] if msg.failed_recipients else msg.from_address
    contact = find_contact_by_email(db, failed_address)
    severity, confidence = _classify_bounce_severity(msg)

    if contact:
        db.add(ReviewQueueItem(
            id=uuid.uuid4(), kind="bounce_uncertain",
            entity_type="contact", entity_id=contact.id,
            payload={
                "summary": f"{'Hard' if severity == 'hard' else 'Soft'} bounce for "
                           f"{contact.full_name or failed_address or '(unknown address)'}",
                "details": [
                    {"key": "address", "label": "Failed address", "value": failed_address or "-"},
                    {"key": "subject", "label": "Original subject", "value": msg.subject},
                    {"key": "severity", "label": "Classified as", "value": severity},
                ],
                "related_entities": [
                    {"type": "contact", "id": str(contact.id), "label": contact.full_name or failed_address or "contact"}
                ],
                "original_text": msg.body_text,
                "message_id": msg.message_id,
                "confidence": confidence,
            },
        ))
    else:
        db.add(ReviewQueueItem(
            id=uuid.uuid4(), kind="bounce_unmatched",
            entity_type=None, entity_id=None,
            payload={
                "summary": f"Bounce for {failed_address or '(unknown address)'} - no contact match",
                "details": [
                    {"key": "address", "label": "Failed address", "value": failed_address or "-"},
                    {"key": "subject", "label": "Original subject", "value": msg.subject},
                    {"key": "severity", "label": "Classified as", "value": severity},
                ],
                "original_text": msg.body_text,
                "message_id": msg.message_id,
                "confidence": confidence,
            },
        ))
    return True


def _handle_candidate_ooo(db: Session, msg: ParsedMessage) -> bool:
    """Queues a review item for a message that looks like an out-of-office
    / auto-reply, but only when the sender is someone already in the CRM -
    an auto-reply from an address we have no contact for isn't something a
    reviewer can act on. Returns True if something was queued."""
    original = find_contact_by_email(db, msg.from_address)
    if not original:
        return False

    replacement_name, replacement_email = _extract_ooo_replacement(msg)
    replacement_contact = find_contact_by_email(db, replacement_email)
    suggested_contact = (
        {"id": str(replacement_contact.id), "label": replacement_contact.full_name or replacement_email}
        if replacement_contact else None
    )

    db.add(ReviewQueueItem(
        id=uuid.uuid4(), kind="ooo_ambiguous",
        entity_type="contact", entity_id=original.id,
        payload={
            "summary": (
                f"{original.full_name or original.first_name or 'A contact'} is out of office"
                + (f" - possible replacement: {replacement_name}" if replacement_name else "")
            ),
            "details": [
                {"key": "subject", "label": "Subject", "value": msg.subject},
                {"key": "replacement_name", "label": "Named replacement", "value": replacement_name or "-"},
                {"key": "replacement_email", "label": "Replacement email", "value": replacement_email or "-"},
            ],
            "related_entities": [
                {"type": "contact", "id": str(original.id), "label": original.full_name or msg.from_address or "contact"}
            ],
            "suggested_contact": suggested_contact,
            "original_text": msg.body_text,
            "message_id": msg.message_id,
            "confidence": 0.65 if replacement_contact else 0.4,
        },
    ))
    return True


def scan_mailbox_for_bounces_and_ooo() -> None:
    """CS-001 + CS-002 producer: reads every mailbox in GRAPH_SCAN_MAILBOXES
    via Microsoft Graph, classifies each new message, and writes a
    `bounce_uncertain` / `bounce_unmatched` / `ooo_ambiguous` row for
    anything that looks actionable. A genuine human reply, or anything that
    doesn't look like a bounce or an auto-reply, is left alone entirely -
    this scan only ever adds a suggestion, never reads for its own sake.

    Incremental per mailbox: remembers the newest message it already
    processed (app.automations.state, keyed "bounce_scan:{mailbox}") so a
    15-minute scan only asks Graph for what's new since last time, not the
    whole inbox. One mailbox failing (bad permissions, Graph outage) is
    logged and skipped - it never aborts the other mailboxes' scans.
    """
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        mailboxes = _scan_mailboxes(db)
        if not mailboxes:
            logger.info("bounce_ooo scan: no mailboxes configured (GRAPH_SCAN_MAILBOXES / Automations Settings) - nothing to scan.")
            return

        existing_message_ids = set(
            db.scalars(
                select(ReviewQueueItem.payload["message_id"].astext).where(
                    ReviewQueueItem.kind.in_(["bounce_uncertain", "bounce_unmatched", "ooo_ambiguous"]),
                    ReviewQueueItem.status == "pending",
                )
            ).all()
        )

        total_queued = 0
        for mailbox in mailboxes:
            cursor_key = f"bounce_scan:{mailbox}"
            state = get_state(db, cursor_key)
            last_processed_at = state.get("last_processed_at")
            skip_ids = set(state.get("last_message_ids", []))
            since_dt = (
                datetime.fromisoformat(last_processed_at)
                if last_processed_at
                else now - timedelta(minutes=runtime_settings.get_int(db, "bounce_scan_initial_lookback_minutes"))
            )
            since_iso = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            try:
                raw_messages = list_messages_since(mailbox, since_iso)
            except GraphRequestError as exc:
                logger.error("bounce_ooo scan: mailbox %s failed (HTTP %s): %s", mailbox, exc.status_code, exc)
                continue

            parsed = [parse_message(m) for m in raw_messages if m.get("id") not in skip_ids]
            queued_this_mailbox = 0

            for msg in parsed:
                if msg.message_id in existing_message_ids:
                    continue
                if looks_like_bounce(msg):
                    queued = _handle_candidate_bounce(db, msg)
                elif looks_like_ooo(msg):
                    queued = _handle_candidate_ooo(db, msg)
                else:
                    queued = False
                if queued:
                    existing_message_ids.add(msg.message_id)
                    queued_this_mailbox += 1

            if parsed:
                max_ts = max(m.received_at for m in parsed)
                ids_at_max = [m.message_id for m in parsed if m.received_at == max_ts]
                set_state(db, cursor_key, {"last_processed_at": max_ts.isoformat(), "last_message_ids": ids_at_max})

            logger.info(
                "bounce_ooo scan: mailbox %s - %d message(s) read, %d queued",
                mailbox, len(parsed), queued_this_mailbox,
            )
            total_queued += queued_this_mailbox

        db.commit()
        logger.info(
            "bounce_ooo scan finished: %d total item(s) queued across %d mailbox(es)",
            total_queued, len(mailboxes),
        )
    finally:
        db.close()


register_job(ScheduledJob(
    id="cs001_cs002_bounce_ooo_scan",
    label="Bounce & OOO mailbox scan",
    description="Scans the shared mailbox for bounces and out-of-office replies (CS-001, CS-002).",
    cron="*/15 * * * *",  # every 15 minutes, once real - cheap to run often since it's incremental
    func=scan_mailbox_for_bounces_and_ooo,
    enabled_flag="automations_bounce_scan_enabled",
    cursor_prefix="bounce_scan:",
))
