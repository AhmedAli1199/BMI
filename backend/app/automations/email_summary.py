"""SALES-010-lite (Email Exchange Summarising), scoped down from the
original spec to the part that's actually useful and safe to build first:
turning real, contact-matched 1:1 correspondence into the structured
signals (budget windows, renewal dates, promised call-backs, personal
touchpoints) that SALES-012/013 need but have never had - see BACKLOG.md/
session notes for why the follow-up queue has been empty without this.

Deliberately narrow scope - every one of these runs before anything ever
reaches the LLM, cheapest/most-eliminating first:

  1. Contact match required (either party) - no match, no read at all.
  2. Recipient count capped (EMAIL_SUMMARY_MAX_RECIPIENTS) - a group
     thread isn't a 1:1 sales conversation.
  3. Not bounce/OOO-shaped (reuses mail_parsing.py's own heuristics as an
     *exclusion* filter here) and no List-Unsubscribe header - a
     newsletter or an auto-reply isn't a conversation.
  4. Body length floor (EMAIL_SUMMARY_MIN_BODY_CHARS) - a bare "Thanks!"
     has nothing to extract.
  5. Contact-level opt-out (custom_fields._ai_email_summary_excluded).

What survives all five gets grouped by Graph's conversationId - one LLM
call per *thread* with a new message, not per message, fed only the new
message's text plus that thread's own prior extracted signals (never the
raw prior emails) - see _extract_signals()'s prompt. Never touches
attachments, never reads more than what's needed to decide.

Nothing here queues a review-queue item - that would flood the queue for
the mere act of reading a thread. The human-approval gate stays at
SALES-012/013: turning a stored signal into an actual outbound draft.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.automations.contact_match import find_contact_by_email
from app.automations.llm import extract_json
from app.automations.mail_parsing import ParsedMessage, looks_like_bounce, looks_like_ooo, parse_message
from app.automations.scheduler import ScheduledJob, register_job
from app.automations.state import get_state, set_state
from app.core.config import settings
from app.db.session import SessionLocal
from app.graph_client import GraphRequestError, list_messages_since
from app.models import Contact, EmailSignal

logger = logging.getLogger("app.automations.email_summary")

_SIGNAL_EXTRACTION_PROMPT = (
    "You read one real email exchange between a salesperson and a client/prospect. Extract any of the "
    "following that this message (in light of the conversation summary so far) actually establishes - "
    "never invent one that isn't clearly there:\n"
    "- budget_window: a month/quarter mentioned for a future spend decision\n"
    "- renewal_date: a contract or ad-placement renewal date\n"
    "- promised_callback: a specific date the salesperson said they'd follow up\n"
    "- personal_touchpoint: an occasion mentioned in passing (leave, a holiday, an anniversary) worth "
    "a personal note later\n\n"
    "Return JSON of the exact shape: {\"signals\": [{\"type\": one of the four above, "
    "\"due_date\": \"YYYY-MM-DD\" or null, \"summary\": \"one sentence\"}], "
    "\"thread_summary\": \"one or two sentences on where this conversation stands\"}. "
    "Return {\"signals\": [], \"thread_summary\": \"...\"} if nothing above is actually established."
)


def _scan_mailboxes() -> list[str]:
    raw = settings.graph_email_summary_mailboxes.strip()
    return [m.strip() for m in raw.split(",") if m.strip()]


def _thread_contact(db: Session, msg: ParsedMessage) -> Contact | None:
    """The mailbox being scanned belongs to a salesperson, so the "other
    party" on a real conversation could be either side: the sender (an
    inbound reply from the client) or a recipient (an outbound message the
    salesperson sent). Checked in that order since it's slightly cheaper
    and inbound replies are the common case."""
    contact = find_contact_by_email(db, msg.from_address)
    if contact:
        return contact
    for address in msg.to_addresses:
        contact = find_contact_by_email(db, address)
        if contact:
            return contact
    return None


def _looks_like_real_conversation(msg: ParsedMessage) -> bool:
    if msg.recipient_count > settings.email_summary_max_recipients:
        return False
    if looks_like_bounce(msg) or looks_like_ooo(msg):
        return False
    list_unsubscribe = msg.headers.get("list-unsubscribe", "")
    if list_unsubscribe:
        return False
    if len(msg.body_text.strip()) < settings.email_summary_min_body_chars:
        return False
    return True


def _upsert_signals(db: Session, contact_id, thread_id: str, message_id: str, extracted: dict) -> int:
    """Insert-or-update by (source_thread_id, signal_type) - a thread's Nth
    message about the same renewal date refines the existing row, it never
    creates a duplicate. Returns how many rows were written."""
    written = 0
    for signal in extracted.get("signals") or []:
        signal_type = signal.get("type")
        if signal_type not in ("budget_window", "renewal_date", "promised_callback", "personal_touchpoint"):
            continue
        summary = (signal.get("summary") or "").strip()
        if not summary:
            continue
        due_date = None
        raw_date = signal.get("due_date")
        if raw_date:
            try:
                due_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
            except ValueError:
                pass

        existing = db.query(EmailSignal).filter_by(source_thread_id=thread_id, signal_type=signal_type).first()
        if existing:
            existing.summary = summary
            existing.due_date = due_date
            existing.source_message_id = message_id
            existing.status = "open"  # a fresh mention re-opens a signal a rep may have already actioned/dismissed
        else:
            db.add(EmailSignal(
                id=uuid.uuid4(), contact_id=contact_id, signal_type=signal_type,
                due_date=due_date, summary=summary,
                source_thread_id=thread_id, source_message_id=message_id,
                confidence=0.6,
            ))
        written += 1
    return written


def scan_email_exchanges() -> None:
    """SALES-010-lite producer: reads each configured salesperson mailbox,
    filters down to real contact-matched 1:1 conversations (see module
    docstring), and extracts structured signals one LLM call per updated
    thread. Same incremental-cursor and per-mailbox-failure-isolation
    pattern as the bounce/OOO scan.
    """
    mailboxes = _scan_mailboxes()
    if not mailboxes:
        logger.info("email_summary scan: GRAPH_EMAIL_SUMMARY_MAILBOXES not configured - nothing to scan.")
        return

    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        total_signals = 0
        for mailbox in mailboxes:
            cursor_key = f"email_summary_scan:{mailbox}"
            state = get_state(db, cursor_key)
            last_processed_at = state.get("last_processed_at")
            skip_ids = set(state.get("last_message_ids", []))
            since_dt = (
                datetime.fromisoformat(last_processed_at)
                if last_processed_at
                else now - timedelta(minutes=settings.email_summary_initial_lookback_minutes)
            )
            since_iso = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            try:
                raw_messages = list_messages_since(mailbox, since_iso)
            except GraphRequestError as exc:
                logger.error("email_summary scan: mailbox %s failed (HTTP %s): %s", mailbox, exc.status_code, exc)
                continue

            parsed = [parse_message(m) for m in raw_messages if m.get("id") not in skip_ids]

            # Filter to real, contact-matched conversations, then group
            # survivors by thread so an updated thread only ever costs one
            # LLM call this run, however many new messages it got.
            threads: dict[str, list[tuple[ParsedMessage, Contact]]] = {}
            for msg in parsed:
                if not _looks_like_real_conversation(msg):
                    continue
                contact = _thread_contact(db, msg)
                if not contact:
                    continue
                if (contact.custom_fields or {}).get("_ai_email_summary_excluded"):
                    continue
                thread_id = msg.conversation_id or msg.internet_message_id or msg.message_id
                threads.setdefault(thread_id, []).append((msg, contact))

            queued_this_mailbox = 0
            for thread_id, entries in threads.items():
                # Only the newest message in the thread needs summarizing -
                # older ones in this same batch already establish the
                # context an earlier signal (if any) was built from.
                latest_msg, contact = max(entries, key=lambda e: e[0].received_at)
                prior_summaries = [
                    s.summary for s in
                    db.query(EmailSignal).filter_by(source_thread_id=thread_id).all()
                ]
                context = "\n".join(f"- {s}" for s in prior_summaries) or "(no prior context)"
                user_prompt = (
                    f"Conversation so far:\n{context}\n\n"
                    f"New message - Subject: {latest_msg.subject}\n\n{latest_msg.body_text}"
                )
                extracted = extract_json(_SIGNAL_EXTRACTION_PROMPT, user_prompt)
                if not extracted:
                    continue
                queued_this_mailbox += _upsert_signals(db, contact.id, thread_id, latest_msg.message_id, extracted)

            if parsed:
                max_ts = max(m.received_at for m in parsed)
                ids_at_max = [m.message_id for m in parsed if m.received_at == max_ts]
                set_state(db, cursor_key, {"last_processed_at": max_ts.isoformat(), "last_message_ids": ids_at_max})

            logger.info(
                "email_summary scan: mailbox %s - %d message(s) read, %d real conversation thread(s), %d signal(s) written",
                mailbox, len(parsed), len(threads), queued_this_mailbox,
            )
            total_signals += queued_this_mailbox

        db.commit()
        logger.info(
            "email_summary scan finished: %d total signal(s) written across %d mailbox(es)",
            total_signals, len(mailboxes),
        )
    finally:
        db.close()


register_job(ScheduledJob(
    id="email_summary_scan",
    label="Email exchange summary scan",
    description="Reads real 1:1 sales conversations and extracts budget/renewal/call-back/touchpoint signals (SALES-010-lite).",
    cron="0 */4 * * *",  # every 4 hours - less urgent than bounce, more expensive per run (an LLM call per updated thread)
    func=scan_email_exchanges,
    enabled_flag="automations_email_summary_scan_enabled",
))
