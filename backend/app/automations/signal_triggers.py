"""SALES-012 (Budget-Window & Renewal Triggers, now also covering
promised_callback - see the _TRIGGERABLE_TYPES comment below) - see
docs/build-spec.txt. Reads the signal rows SALES-010-lite
(email_summary.py) already extracts and surfaces one for review once it's
actually worth a rep's attention - two ways, since the real data has both:

  1. Has a due_date: triggers once that date is within a configurable lead
     window (default 14 days out) - the classic "renewal coming up" case.
  2. No due_date: plenty of the strongest signals (a confirmed budget
     figure, no specific date attached - see the real data sample) would
     otherwise never surface. These trigger once, a configurable number of
     days after the signal was first created (default 3), so it's not an
     instant re-notification of something a rep just read.

Same "draft, never dispatch" contract as every other automation here:
this only ever queues a review item. A real follow-up note (AI-drafted
when configured, a plain template otherwise - see _draft_followup_text)
is generated once at queue time and shown in the review card's expandable
"Original message" section, so the reviewer sees exactly what "Draft
follow-up" will write to the contact's record before deciding, not an
opaque button with no visible outcome. Nothing is ever sent - this writes
an internal Note only. Every signal is triggered at most once while it
has a pending review item open; "Not relevant" permanently dismisses it
(status="dismissed"), "Draft follow-up" marks it actioned - either way it
never re-triggers on its own.
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

logger = logging.getLogger("app.automations.signal_triggers")

# promised_callback included alongside the original budget_window/
# renewal_date pair - SALES-013 (morning_queue.py) needs somewhere these
# surface from, and this trigger logic (due within a lead window, or a
# delay after extraction if undated) already fits it exactly the same way
# - no separate producer needed. personal_touchpoint deliberately stays
# out: it's a warmth/context signal, not something with a "due" point.
_TRIGGERABLE_TYPES = ("budget_window", "renewal_date", "promised_callback")

_SIGNAL_TYPE_LABELS = {
    "budget_window": "Budget window", "renewal_date": "Renewal date", "promised_callback": "Promised callback",
}


_DRAFT_EMAIL_PROMPT = (
    "You draft a short, professional follow-up EMAIL a BMI Publishing salesperson can copy and send "
    "to their client/prospect almost as-is, based on one fact their own earlier email correspondence "
    "already established. Write a real email: a greeting using the contact's first name if given, 2-4 "
    "sentences referencing the established fact and prompting the specific next step, and a brief "
    "sign-off with no signature block (the rep's own email client adds that). Never invent facts, "
    "prices, dates, or commitments beyond what's given - if the context is thin, keep it general rather "
    "than fabricating detail. Return JSON of the exact shape: {\"subject\": string, \"body\": string}. "
    "\"body\" is the email text only - no labels, no commentary, no explaining what you're about to write."
)


def _purpose_line(signal: EmailSignal, contact_label: str) -> str:
    """A short, deterministic (never LLM-generated) explanation of why this
    note exists, written into the Note itself - not just shown in the
    review card. The Note is a permanent CRM record a future reader has no
    other context for, so it needs to be self-explanatory on its own, not
    rely on the review queue UI that queued it having ever existed."""
    label = _SIGNAL_TYPE_LABELS.get(signal.signal_type, signal.signal_type)
    due = f", due {signal.due_date.isoformat()}" if signal.due_date else ""
    extras = ", ".join(
        f"{k}: {v}" for k, v in (("package", signal.package_offered), ("rate", signal.rate_offered)) if v
    )
    return f"{label}{due} for {contact_label} - {signal.summary}" + (f" ({extras})" if extras else "")


def _format_drafted_note(purpose: str, subject: str, body: str) -> str:
    """One self-contained Note body: why this exists, then the actual
    email a rep can copy into their own client - see this module's
    docstring on why a bare internal reminder wasn't good enough."""
    return f"Why this note: {purpose}\n\nSubject: {subject}\n\n{body}".strip()


def _draft_followup_text(signal: EmailSignal, contact_label: str, extra_instructions: str = "") -> tuple[str, bool]:
    """Returns (formatted_note_body, was_ai_generated) - same contract as
    followup_queue.py's _draft_followup_text, and deliberately generated
    once at QUEUE time (not when the reviewer clicks) so what the rep sees
    in the review card before deciding is exactly what gets written to the
    contact's record if they approve it - no surprise gap between preview
    and outcome. `extra_instructions`, when set, comes from the reviewer's
    own "regenerate with instructions" request (see _redraft_signal_trigger
    below) - appended as an explicit, higher-priority instruction, never
    silently blended into the base prompt."""
    label = _SIGNAL_TYPE_LABELS.get(signal.signal_type, signal.signal_type)
    due = f" (due {signal.due_date.isoformat()})" if signal.due_date else ""
    purpose = _purpose_line(signal, contact_label)
    price_context = "".join(
        f"\n{k}: {v}" for k, v in (("Package discussed", signal.package_offered), ("Rate discussed", signal.rate_offered)) if v
    )

    if is_configured():
        system_prompt = _DRAFT_EMAIL_PROMPT
        if price_context:
            system_prompt += "\n\nIf a package/rate is given below, you may reference it, but never alter the figure or invent one."
        if extra_instructions:
            system_prompt += f"\n\nThe reviewer asked for this specific revision - follow it: {extra_instructions}"
        result = extract_json(
            system_prompt,
            f"Signal type: {label}{due}\nContact: {contact_label}\nWhat the email established: {signal.summary}{price_context}",
            purpose="signal_triggers.draft",
        )
        subject = (result or {}).get("subject", "").strip()
        body = (result or {}).get("body", "").strip()
        # Defensive strip - see llm.py's thinking-budget fix and the
        # production bug it addressed: even now, a stray meta-label line
        # can slip into "body" before the real prose. Drop it rather than
        # writing it into the contact's record.
        body = "\n".join(
            line for line in body.splitlines()
            if not re.match(r"^\s*(sentence\s*\d|drafting\b)", line, re.IGNORECASE)
        ).strip()
        if subject and body:
            return _format_drafted_note(purpose, subject, body), True

    subject = f"{label} - {contact_label}"
    body = f"Hi {contact_label},\n\nFollowing up: {signal.summary}\n\nLet me know if that still works.\n"
    return _format_drafted_note(purpose, subject, body), False


def _add_note(db: Session, contact: Contact, body: str) -> None:
    db.add(Note(
        id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()),
        entity_type="contact", entity_id=contact.id,
        note_type="Follow-up needed", body=body, act_created_at=datetime.now(timezone.utc),
    ))


def _get_signal_or_raise(db: Session, signal_id) -> EmailSignal:
    signal = db.get(EmailSignal, signal_id) if signal_id else None
    if not signal:
        raise ValueError("This signal no longer exists - it may have been superseded by a newer message on the same thread.")
    return signal


def _handle_signal_trigger(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    signal = _get_signal_or_raise(db, item.payload.get("signal_id"))

    if action_id == "draft_followup":
        contact = db.get(Contact, signal.contact_id)
        if not contact:
            raise ValueError("The contact this signal belongs to no longer exists.")
        # Prefer whatever the reviewer last saw/edited in the draft dialog
        # (submitted as `note`, same field the generic review form already
        # uses for "override the default text") - falls back to the
        # queue-time draft only if the dialog was skipped entirely (an
        # older client, or an API caller that never opened it).
        draft = (input_data.get("note") or "").strip() or item.payload.get("original_text") or signal.summary
        _add_note(db, contact, draft)
        signal.status = "actioned"
    elif action_id == "dismiss":
        signal.status = "dismissed"
    else:
        raise ValueError(f"Unknown action {action_id!r} for signal_trigger")


def _redraft_signal_trigger(db: Session, item: ReviewQueueItem, extra_instructions: str) -> str:
    """POST /review-queue/{id}/redraft's backing function for this kind -
    re-runs the same drafting prompt with the reviewer's extra
    instructions folded in. Never touches signal.status or the item's
    approval state - see that route's docstring."""
    signal = _get_signal_or_raise(db, item.payload.get("signal_id"))
    contact = db.get(Contact, signal.contact_id)
    contact_label = (contact.full_name or contact.first_name) if contact else None
    draft, _ = _draft_followup_text(signal, contact_label or "the contact", extra_instructions)
    return draft


register(ReviewKind(
    kind="signal_trigger",
    label="Commercial Signals",
    description="Upcoming advertiser budget windows, publication renewal dates, and promised callbacks extracted from email correspondence.",
    actions=[
        ReviewAction(id="draft_followup", label="Review draft & send", style="primary", outcome="approved"),
        ReviewAction(id="dismiss", label="Dismiss signal", style="secondary", outcome="rejected"),
    ],
    handler=_handle_signal_trigger,
    redraft=_redraft_signal_trigger,
))


def _already_queued_signal_ids(db: Session) -> set[str]:
    return set(
        db.scalars(
            select(ReviewQueueItem.payload["signal_id"].astext).where(
                ReviewQueueItem.kind == "signal_trigger",
                ReviewQueueItem.status == "pending",
            )
        ).all()
    )


def _should_trigger(signal: EmailSignal, today: date, lead_days: int, no_date_delay_days: int) -> bool:
    if signal.due_date:
        return signal.due_date - today <= timedelta(days=lead_days)
    created = signal.created_at.date() if signal.created_at else today
    return today - created >= timedelta(days=no_date_delay_days)


def scan_signal_triggers() -> None:
    """SALES-012 producer: reads open budget_window/renewal_date signals,
    queues a review item for any that have crossed their trigger point
    (see module docstring), capped per run. Runs once daily - unlike the
    mailbox scans, nothing here needs minute-level freshness."""
    today = datetime.now(timezone.utc).date()
    db = SessionLocal()
    try:
        lead_days = runtime_settings.get_int(db, "sales012_lead_days")
        no_date_delay_days = runtime_settings.get_int(db, "sales012_no_date_delay_days")
        max_per_run = runtime_settings.get_int(db, "sales012_max_per_run")

        already_queued = _already_queued_signal_ids(db)
        candidates = (
            db.query(EmailSignal)
            .filter(EmailSignal.signal_type.in_(_TRIGGERABLE_TYPES), EmailSignal.status == "open")
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
                continue  # orphaned signal (contact deleted/merged since extraction) - nothing to surface

            label = _SIGNAL_TYPE_LABELS.get(signal.signal_type, signal.signal_type)
            contact_label = contact.full_name or contact.first_name or "a contact"
            draft, was_ai = _draft_followup_text(signal, contact_label)
            db.add(ReviewQueueItem(
                id=uuid.uuid4(), kind="signal_trigger",
                entity_type="contact", entity_id=contact.id,
                payload={
                    "summary": f"{label} for {contact_label}" + (f" - due {signal.due_date.isoformat()}" if signal.due_date else ""),
                    "details": [
                        {"key": "signal_type", "label": "Type", "value": label},
                        {"key": "due_date", "label": "Due date", "value": signal.due_date.isoformat() if signal.due_date else "(none stated)"},
                        {"key": "extracted", "label": "From the email thread", "value": signal.summary},
                        *([{"key": "package_offered", "label": "Package discussed", "value": signal.package_offered}] if signal.package_offered else []),
                        *([{"key": "rate_offered", "label": "Rate discussed", "value": signal.rate_offered}] if signal.rate_offered else []),
                        {"key": "draft_source", "label": "Draft", "value": "AI-drafted" if was_ai else "Templated (no AI configured)"},
                    ],
                    # Rendered by the generic review card as an expandable
                    # "Original message" section - what "Draft follow-up"
                    # actually writes to the contact's record, visible
                    # before the reviewer decides, not just after.
                    "original_text": draft,
                    # Separate expandable section, distinct from
                    # original_text above (that's the drafted action, this
                    # is the real source material it was drawn from) - see
                    # EmailSignal.source_snippet.
                    "source_context": signal.source_snippet,
                    "related_entities": [{"type": "contact", "id": str(contact.id), "label": contact_label}],
                    "signal_id": str(signal.id),
                    "confidence": signal.confidence,
                    # Root-level (not just inside "details", which is
                    # display-only text) so morning_queue.py's ranking can
                    # read a real date/type without parsing display strings.
                    "signal_type": signal.signal_type,
                    "due_date": signal.due_date.isoformat() if signal.due_date else None,
                },
            ))
            # Audit stamp on the contact's own record the moment a trigger
            # fires - separate from (and independent of) the Note written
            # later if/when the reviewer approves the draft, so there's a
            # visible trail even for a trigger that ends up dismissed.
            db.add(HistoryEntry(
                id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()),
                entity_type="contact", entity_id=contact.id,
                history_type="Follow-up queued", subject=f"{label} follow-up queued",
                details=f"{label}" + (f", due {signal.due_date.isoformat()}" if signal.due_date else "") + f" - {signal.summary}",
                occurred_at=datetime.now(timezone.utc),
            ))
            queued += 1

        db.commit()
        logger.info(
            "signal_triggers scan: %d candidate(s) examined, %d queued (lead_days=%d, no_date_delay_days=%d)",
            len(candidates), queued, lead_days, no_date_delay_days,
        )
    finally:
        db.close()


register_job(ScheduledJob(
    id="sales012_signal_triggers_scan",
    label="Budget window / renewal trigger scan",
    description="Surfaces budget_window/renewal_date signals once they're due or have sat undated long enough to be worth a look (SALES-012).",
    cron="0 6 * * *",  # once daily - not time-critical the way a mailbox scan is
    func=scan_signal_triggers,
    enabled_flag="automations_signal_triggers_scan_enabled",
))
