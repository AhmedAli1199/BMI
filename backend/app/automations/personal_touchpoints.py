"""SALES-005 (Personal Touchpoint Reminders) - see docs/build-spec.txt.
Reads the `personal_touchpoint` signals SALES-010 (email_summary.py)
already extracts and sensitivity-filters (bereavement/serious illness are
never extracted as a touchpoint in the first place - see that module's
_is_sensitive_touchpoint) and surfaces one for review once its occasion is
due, so a rep can send a short, warm, occasion-appropriate note.

A deliberately separate producer from SALES-012 (signal_triggers.py),
even though the trigger mechanics (due-date-within-a-window, or a delay
after extraction if undated) are structurally the same: these are warmth/
relationship signals, not "something needs chasing" ones, so they get
their own settings, their own tone of draft, and their own queue kind
(personal_touchpoint_due) - never blended into the sales-follow-up queue
under signal_trigger's label.

Same "draft, never dispatch" and "trigger once" contract as every other
automation here: this only ever queues a review item; the underlying
EmailSignal's own status (open -> actioned/dismissed) IS the "skip once,
never nag again" ledger the spec asks for - no separate skip table
needed, since a dismissed/actioned signal is excluded from every future
scan's candidate query by construction.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import MANUAL_SOURCE_DB
from app.automations import runtime_settings
from app.automations.llm import extract_json, is_configured
from app.automations.registry import ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.db.session import SessionLocal
from app.models import Contact, EmailSignal, HistoryEntry, Note, ReviewQueueItem

logger = logging.getLogger("app.automations.personal_touchpoints")

_DRAFT_TOUCHPOINT_PROMPT = (
    "You draft a short, warm, personal note a BMI Publishing salesperson can copy and send to a client/"
    "prospect, marking a personal occasion mentioned in their own earlier correspondence (e.g. returning "
    "from leave, a birthday, an anniversary). Write a real, brief email: a genuine, friendly greeting "
    "referencing the specific occasion, 1-3 sentences, warm but not gushing, no business pitch or sales "
    "ask folded in - this is purely a relationship touchpoint. Never invent detail beyond what's given. "
    "Return JSON of the exact shape: {\"subject\": string, \"body\": string}. \"body\" is the email text "
    "only - no labels, no commentary."
)


def _purpose_line(signal: EmailSignal, contact_label: str) -> str:
    due = f", due {signal.due_date.isoformat()}" if signal.due_date else ""
    return f"Personal touchpoint{due} for {contact_label} - {signal.summary}"


def _format_drafted_note(purpose: str, subject: str, body: str) -> str:
    return f"Why this note: {purpose}\n\nSubject: {subject}\n\n{body}".strip()


def _draft_touchpoint_text(signal: EmailSignal, contact_label: str, extra_instructions: str = "") -> tuple[str, bool]:
    """Returns (formatted_note_body, was_ai_generated) - same contract and
    same queue-time (not click-time) generation as signal_triggers.py's
    _draft_followup_text, so what the reviewer previews is exactly what
    gets written on approval."""
    purpose = _purpose_line(signal, contact_label)

    if is_configured():
        system_prompt = _DRAFT_TOUCHPOINT_PROMPT
        if extra_instructions:
            system_prompt += f"\n\nThe reviewer asked for this specific revision - follow it: {extra_instructions}"
        result = extract_json(
            system_prompt,
            f"Contact: {contact_label}\nOccasion: {signal.summary}",
            purpose="personal_touchpoints.draft",
        )
        subject = (result or {}).get("subject", "").strip()
        body = (result or {}).get("body", "").strip()
        body = "\n".join(
            line for line in body.splitlines()
            if not re.match(r"^\s*(sentence\s*\d|drafting\b)", line, re.IGNORECASE)
        ).strip()
        if subject and body:
            return _format_drafted_note(purpose, subject, body), True

    subject = f"Good to hear from you, {contact_label}"
    body = f"Hi {contact_label},\n\n{signal.summary}. Hope all is well - would be great to catch up soon.\n"
    return _format_drafted_note(purpose, subject, body), False


def _add_note(db: Session, contact: Contact, body: str) -> None:
    db.add(Note(
        id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()),
        entity_type="contact", entity_id=contact.id,
        note_type="Personal touchpoint", body=body, act_created_at=datetime.now(timezone.utc),
    ))


def _get_signal_or_raise(db: Session, signal_id) -> EmailSignal:
    signal = db.get(EmailSignal, signal_id) if signal_id else None
    if not signal:
        raise ValueError("This signal no longer exists - it may have been superseded by a newer message on the same thread.")
    return signal


def _handle_touchpoint(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    signal = _get_signal_or_raise(db, item.payload.get("signal_id"))

    if action_id == "draft_touchpoint":
        contact = db.get(Contact, signal.contact_id)
        if not contact:
            raise ValueError("The contact this signal belongs to no longer exists.")
        draft = (input_data.get("note") or "").strip() or item.payload.get("original_text") or signal.summary
        _add_note(db, contact, draft)
        signal.status = "actioned"
    elif action_id == "skip":
        # Permanent, same as signal_trigger's "Not relevant" - the
        # underlying signal is the skip ledger the spec asks for; once
        # dismissed it's excluded from every future candidate query below.
        signal.status = "dismissed"
    else:
        raise ValueError(f"Unknown action {action_id!r} for personal_touchpoint_due")


def _redraft_touchpoint(db: Session, item: ReviewQueueItem, extra_instructions: str) -> str:
    signal = _get_signal_or_raise(db, item.payload.get("signal_id"))
    contact = db.get(Contact, signal.contact_id)
    contact_label = (contact.full_name or contact.first_name) if contact else None
    draft, _ = _draft_touchpoint_text(signal, contact_label or "the contact", extra_instructions)
    return draft


register(ReviewKind(
    kind="personal_touchpoint_due",
    label="Personal Touchpoint Reminders",
    description="Client return-from-leave dates, anniversaries, and relationship milestones for warm, no-pitch touchpoints.",
    actions=[
        ReviewAction(id="draft_touchpoint", label="Approve & log to CRM", style="primary", outcome="approved"),
        ReviewAction(id="skip", label="Skip this occasion", style="secondary", outcome="rejected"),
    ],
    handler=_handle_touchpoint,
    redraft=_redraft_touchpoint,
    audience="sales",
))


def _already_queued_signal_ids(db: Session) -> set[str]:
    return set(
        db.scalars(
            select(ReviewQueueItem.payload["signal_id"].astext).where(
                ReviewQueueItem.kind == "personal_touchpoint_due",
                ReviewQueueItem.status == "pending",
            )
        ).all()
    )


def _should_trigger(signal: EmailSignal, today: date, lead_days: int, no_date_delay_days: int) -> bool:
    if signal.due_date:
        return signal.due_date - today <= timedelta(days=lead_days)
    created = signal.created_at.date() if signal.created_at else today
    return today - created >= timedelta(days=no_date_delay_days)


def scan_personal_touchpoints() -> None:
    """SALES-005 producer: reads open personal_touchpoint signals, queues
    a review item for any that have crossed their trigger point, capped
    per run. Runs once daily, early morning - matches the spec's "on the
    day a recorded personal date falls due" framing."""
    today = datetime.now(timezone.utc).date()
    db = SessionLocal()
    try:
        lead_days = runtime_settings.get_int(db, "sales005_lead_days")
        no_date_delay_days = runtime_settings.get_int(db, "sales005_no_date_delay_days")
        max_per_run = runtime_settings.get_int(db, "sales005_max_per_run")

        already_queued = _already_queued_signal_ids(db)
        candidates = (
            db.query(EmailSignal)
            .filter(EmailSignal.signal_type == "personal_touchpoint", EmailSignal.status == "open")
            .order_by(EmailSignal.due_date.asc().nulls_last(), EmailSignal.created_at.asc())
            .all()
        )

        queued = 0
        for signal in candidates:
            if queued >= max_per_run:
                break
            if str(signal.id) in already_queued:
                continue
            if not _should_trigger(signal, today, lead_days, no_date_delay_days):
                continue

            contact = db.get(Contact, signal.contact_id)
            if not contact:
                continue  # orphaned signal (contact deleted/merged since extraction)

            contact_label = contact.full_name or contact.first_name or "a contact"
            draft, was_ai = _draft_touchpoint_text(signal, contact_label)
            db.add(ReviewQueueItem(
                id=uuid.uuid4(), kind="personal_touchpoint_due", source_db=contact.source_db,
                entity_type="contact", entity_id=contact.id,
                payload={
                    "summary": f"Personal touchpoint for {contact_label}" + (f" - due {signal.due_date.isoformat()}" if signal.due_date else ""),
                    "details": [
                        {"key": "occasion", "label": "Occasion", "value": signal.summary},
                        {"key": "due_date", "label": "Due date", "value": signal.due_date.isoformat() if signal.due_date else "(none stated)"},
                        {"key": "draft_source", "label": "Draft", "value": "AI-drafted" if was_ai else "Templated (no AI configured)"},
                    ],
                    "original_text": draft,
                    "source_context": signal.source_snippet,
                    "related_entities": [{"type": "contact", "id": str(contact.id), "label": contact_label}],
                    "signal_id": str(signal.id),
                    "confidence": signal.confidence,
                    "due_date": signal.due_date.isoformat() if signal.due_date else None,
                },
            ))
            db.add(HistoryEntry(
                id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()),
                entity_type="contact", entity_id=contact.id,
                history_type="Touchpoint drafted", subject="Personal touchpoint drafted",
                details=signal.summary + (f", due {signal.due_date.isoformat()}" if signal.due_date else ""),
                occurred_at=datetime.now(timezone.utc),
            ))
            queued += 1

        db.commit()
        logger.info("personal_touchpoints scan finished: %d item(s) queued (of %d open candidate(s))", queued, len(candidates))
    finally:
        db.close()


register_job(ScheduledJob(
    id="personal_touchpoints_scan",
    label="Personal touchpoint reminder scan",
    description="Surfaces due personal touchpoints (leave, birthdays, anniversaries) extracted from real correspondence, with a warm no-business draft (SALES-005).",
    cron="0 6 * * *",  # once daily, early morning - matches the spec's "on the day it falls due"
    func=scan_personal_touchpoints,
    enabled_flag="automations_personal_touchpoints_scan_enabled",
))
