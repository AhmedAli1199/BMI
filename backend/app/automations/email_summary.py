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

from app.automations import runtime_settings
from app.automations.contact_match import find_contact_by_email
from app.automations.llm import extract_json
from app.automations.mail_parsing import ParsedMessage, looks_like_bounce, looks_like_ooo, parse_message
from app.automations.scheduler import ScheduledJob, register_job
from app.automations.state import get_state, set_state
from app.db.session import SessionLocal
from app.graph_client import GraphRequestError, list_messages_since
from app.models import Contact, Email, EmailSignal

logger = logging.getLogger("app.automations.email_summary")

_SIGNAL_EXTRACTION_PROMPT = (
    "You read one real email exchange between a salesperson and a client/prospect. Extract any of the "
    "following that this message (in light of the conversation summary so far) actually establishes - "
    "never invent one that isn't clearly there:\n"
    "- budget_window: ONLY a genuinely pending, not-yet-decided spend the CLIENT hasn't committed to yet - "
    "a real figure or amount must be mentioned (e.g. \"has a budget of £4,000\", \"an extra £6k for Q4\"), "
    "AND it must read as an open decision, not a fact already settled. A month/quarter/deadline date "
    "mentioned on its own - a webinar date, a press/print deadline, an event date - is NOT a budget_window "
    "unless money or spend is explicitly tied to it. Critically, a price/rate/fee the SALESPERSON quoted OR "
    "a cost the client already confirmed/paid (an advertising rate card, an awards entry fee schedule, an "
    "invoice amount, a rate already agreed) is NOT a budget_window either - that's a quote or a closed fact, "
    "not something to follow up on. Only extract this when the client still has a real spend decision ahead "
    "of them. When in doubt, don't extract it.\n"
    "- renewal_date: a contract or ad-placement renewal date with an actual client/customer - NEVER an "
    "internal BMI staffing, appointment, promotion, or payroll matter (those aren't renewals, skip them "
    "entirely even if a date is mentioned).\n"
    "- promised_callback: a specific date the salesperson said they'd follow up\n"
    "- personal_touchpoint: a light, positive-or-neutral personal occasion mentioned in passing (leave, a "
    "holiday, a birthday, an anniversary) worth a friendly note later. NEVER extract a bereavement, death, "
    "serious illness, or other sensitive/difficult personal matter as a personal_touchpoint - those need a "
    "human's own judgement, not an automated note, so leave them out entirely.\n\n"
    "due_date rule (applies to all four types): only set due_date when the message states an exact, "
    "specific calendar date or day (\"25 October\", \"next Friday\", \"the 12th\"). If it only mentions a "
    "vague period - \"next year\", \"Q4\", \"early 2028\", \"sometime in the autumn\", \"in a few weeks\" - "
    "due_date MUST be null. NEVER invent a specific day (e.g. defaulting to the 1st of the month) to fill "
    "in a date that wasn't actually given - a null due_date is correct and expected far more often than a "
    "guessed one.\n\n"
    "Return JSON of the exact shape: {\"signals\": [{\"type\": one of the four above, "
    "\"due_date\": \"YYYY-MM-DD\" or null, \"summary\": \"one sentence\"}], "
    "\"thread_summary\": \"one or two sentences on where this conversation stands\"}. "
    "Return {\"signals\": [], \"thread_summary\": \"...\"} if nothing above is actually established."
)

# Belt-and-suspenders safety net for the personal_touchpoint prompt
# instruction above - never rely on the LLM alone to keep a sensitive
# matter out of an automated note. Any personal_touchpoint whose summary
# hits one of these is dropped rather than stored, regardless of what the
# model returned.
_SENSITIVE_TOUCHPOINT_KEYWORDS = (
    "bereavement", "passed away", "passing", "death", "died", "funeral", "condolence",
    "terminal", "cancer", "serious illness", "hospice", "miscarriage",
)


def _is_sensitive_touchpoint(summary: str) -> bool:
    lowered = summary.lower()
    return any(keyword in lowered for keyword in _SENSITIVE_TOUCHPOINT_KEYWORDS)


def _scan_mailboxes(db: Session) -> list[str]:
    return runtime_settings.get_csv(db, "graph_email_summary_mailboxes")


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


def _domain(address: str | None) -> str:
    if not address or "@" not in address:
        return ""
    return address.rsplit("@", 1)[-1].strip().lower()


def _is_internal_thread(db: Session, msg: ParsedMessage, contact: Contact) -> bool:
    """True when both the mailbox's counterpart on this thread and the
    matched contact sit on a BMI-owned domain - i.e. this is staff writing
    to staff, not a client conversation, even though the recipient matched
    a real Contact row (a record manager who also has a legacy/duplicate
    contact record from the Act! import - see David Wilcox, caught in
    review: an internal appointment/salary email got extracted as a
    "renewal_date" because his own contact record matched)."""
    internal_domains = {d.strip().lower() for d in runtime_settings.get_csv(db, "email_summary_internal_domains") if d.strip()}
    if not internal_domains:
        return False
    contact_email = db.query(Email.address).filter(Email.contact_id == contact.id).filter(Email.address.isnot(None)).first()
    contact_domain = _domain(contact_email[0] if contact_email else None)
    other_party_domains = {_domain(msg.from_address), *[_domain(a) for a in msg.to_addresses]}
    return contact_domain in internal_domains and bool(other_party_domains & internal_domains)


def _looks_like_real_conversation(db: Session, msg: ParsedMessage) -> bool:
    if msg.recipient_count > runtime_settings.get_int(db, "email_summary_max_recipients"):
        return False
    if looks_like_bounce(msg) or looks_like_ooo(msg):
        return False
    list_unsubscribe = msg.headers.get("list-unsubscribe", "")
    if list_unsubscribe:
        return False
    if len(msg.body_text.strip()) < runtime_settings.get_int(db, "email_summary_min_body_chars"):
        return False
    return True


_SOURCE_SNIPPET_MAX_CHARS = 1200


def _upsert_signals(
    db: Session, contact_id, thread_id: str, message_id: str, extracted: dict, *, sent_at: datetime, message_body: str,
) -> int:
    """Insert-or-update by (source_thread_id, signal_type) - a thread's Nth
    message about the same renewal date refines the existing row, it never
    creates a duplicate. Returns how many rows were written.

    The LLM can (and does) return more than one signal of the same type in
    a single response - e.g. two separate budget_window mentions in one
    message. Since the DB constraint is one row per (thread, type), those
    have to be merged in Python before either hits the session: a DB
    lookup alone isn't enough, because the *second* one in the same call
    would still see no existing row (nothing's flushed yet) and try to
    INSERT a second row for the same key, which is exactly what produced
    the UniqueViolation this docstring is now warning about. `existing_by_type`
    is fetched once up front and mutated in place for the rest of this call
    so every same-type signal after the first updates the one row instead.

    `sent_at` is the source message's own received date - a belt-and-
    suspenders check on top of the prompt now being told that date
    explicitly: no promise, renewal, or budget window can legitimately be
    dated before the email that mentions it was even sent, so a due_date
    that lands earlier is almost certainly a wrong-year hallucination
    (observed twice on real data) and is dropped down to null rather than
    stored wrong - a missing due_date is safe, a false-overdue one isn't,
    since SALES-012 will trigger off it.

    `message_body` is capped to _SOURCE_SNIPPET_MAX_CHARS and stored as
    source_snippet - a bounded excerpt of the ONE message that produced
    this signal, not the whole thread, so a reviewer can see the real
    context behind the AI's one-line summary. A deliberate, scoped
    exception to this module's original "never store a message body"
    design - see EmailSignal.source_snippet's own docstring."""
    snippet = message_body.strip()[:_SOURCE_SNIPPET_MAX_CHARS] or None
    existing_by_type: dict[str, EmailSignal] = {
        row.signal_type: row
        for row in db.query(EmailSignal).filter_by(source_thread_id=thread_id).all()
    }

    written = 0
    for signal in extracted.get("signals") or []:
        signal_type = signal.get("type")
        if signal_type not in ("budget_window", "renewal_date", "promised_callback", "personal_touchpoint"):
            continue
        summary = (signal.get("summary") or "").strip()
        if not summary:
            continue
        if signal_type == "personal_touchpoint" and _is_sensitive_touchpoint(summary):
            logger.info("email_summary: dropped a sensitive personal_touchpoint (thread %s) - needs a human, not an automated note", thread_id)
            continue
        due_date = None
        raw_date = signal.get("due_date")
        if raw_date:
            try:
                due_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
            except ValueError:
                pass
            if due_date and due_date < sent_at.date():
                logger.warning(
                    "email_summary: dropping due_date %s for a %s signal (thread %s) - it's before the message's "
                    "own send date %s, almost certainly a wrong-year hallucination",
                    due_date, signal_type, thread_id, sent_at.date(),
                )
                due_date = None

        existing = existing_by_type.get(signal_type)
        if existing:
            existing.summary = summary
            existing.due_date = due_date
            existing.source_message_id = message_id
            existing.source_snippet = snippet
            existing.status = "open"  # a fresh mention re-opens a signal a rep may have already actioned/dismissed
        else:
            new_row = EmailSignal(
                id=uuid.uuid4(), contact_id=contact_id, signal_type=signal_type,
                due_date=due_date, summary=summary,
                source_thread_id=thread_id, source_message_id=message_id, source_snippet=snippet,
                confidence=0.6,
            )
            db.add(new_row)
            existing_by_type[signal_type] = new_row
        written += 1
    return written


def scan_email_exchanges() -> None:
    """SALES-010-lite producer: reads each configured salesperson mailbox,
    filters down to real contact-matched 1:1 conversations (see module
    docstring), and extracts structured signals one LLM call per updated
    thread. Same incremental-cursor and per-mailbox-failure-isolation
    pattern as the bounce/OOO scan.
    """
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        mailboxes = _scan_mailboxes(db)
        if not mailboxes:
            logger.info("email_summary scan: no mailboxes configured (GRAPH_EMAIL_SUMMARY_MAILBOXES / Automations Settings) - nothing to scan.")
            return

        total_signals = 0
        for mailbox in mailboxes:
            cursor_key = f"email_summary_scan:{mailbox}"
            state = get_state(db, cursor_key)
            last_processed_at = state.get("last_processed_at")
            skip_ids = set(state.get("last_message_ids", []))
            since_dt = (
                datetime.fromisoformat(last_processed_at)
                if last_processed_at
                else now - timedelta(minutes=runtime_settings.get_int(db, "email_summary_initial_lookback_minutes"))
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
                if not _looks_like_real_conversation(db, msg):
                    continue
                contact = _thread_contact(db, msg)
                if not contact:
                    continue
                if (contact.custom_fields or {}).get("_ai_email_summary_excluded"):
                    continue
                if _is_internal_thread(db, msg, contact):
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
                # The model's training cutoff is not "now" - without being
                # told the message's actual date, it has no reliable way to
                # resolve "tomorrow"/"next week"/a bare day-of-week into a
                # real calendar date, and defaults to guessing a year from
                # its own training data (observed: 2023, on a message sent
                # in 2026). Anchoring explicitly on the message's own
                # received_at date fixes this at the source, on top of the
                # due-date sanity check in _upsert_signals below.
                sent_date = latest_msg.received_at.date().isoformat()
                user_prompt = (
                    f"This message was sent on {sent_date} - resolve any relative date (\"tomorrow\", \"next week\", "
                    f"a bare day-of-week) and infer the correct year from that date, never from any other assumption.\n\n"
                    f"Conversation so far:\n{context}\n\n"
                    f"New message - Subject: {latest_msg.subject}\n\n{latest_msg.body_text}"
                )
                # Default max_tokens (400) was tuned against OpenAI's
                # typically terser output - Gemini's response for the same
                # prompt ran long enough to get cut off mid-string,
                # producing invalid JSON (observed in production: a
                # JSONDecodeError, "Unterminated string"). This prompt asks
                # for up to 4 signals plus a thread_summary, so it needs
                # real headroom.
                extracted = extract_json(_SIGNAL_EXTRACTION_PROMPT, user_prompt, max_tokens=1200, purpose="email_summary.signal_extraction")
                if not extracted:
                    continue
                queued_this_mailbox += _upsert_signals(
                    db, contact.id, thread_id, latest_msg.message_id, extracted,
                    sent_at=latest_msg.received_at, message_body=latest_msg.body_text,
                )

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
    cursor_prefix="email_summary_scan:",
))
