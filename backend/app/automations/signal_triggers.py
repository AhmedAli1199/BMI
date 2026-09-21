"""SALES-012 (Budget-Window & Renewal Triggers) - see docs/build-spec.txt.
Reads the budget_window/renewal_date rows SALES-010-lite (email_summary.py)
already extracts and surfaces one for review once it's actually worth a
rep's attention - two ways, since the real data has both:

  1. Has a due_date: triggers once that date is within a configurable lead
     window (default 14 days out) - the classic "renewal coming up" case.
  2. No due_date: plenty of the strongest signals (a confirmed budget
     figure, no specific date attached - see the real data sample) would
     otherwise never surface. These trigger once, a configurable number of
     days after the signal was first created (default 3), so it's not an
     instant re-notification of something a rep just read.

Same "draft, never dispatch" contract as every other automation here:
this only ever queues a review item - "Draft follow-up" writes a Note
flagging the contact for outreach, never sends anything. Every signal is
triggered at most once while it has a pending review item open; "Not
relevant" permanently dismisses it (status="dismissed"), "Draft
follow-up" marks it actioned - either way it never re-triggers on its own.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import MANUAL_SOURCE_DB
from app.automations import runtime_settings
from app.automations.registry import ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.db.session import SessionLocal
from app.models import Contact, EmailSignal, Note, ReviewQueueItem

logger = logging.getLogger("app.automations.signal_triggers")

_TRIGGERABLE_TYPES = ("budget_window", "renewal_date")

_SIGNAL_TYPE_LABELS = {"budget_window": "Budget window", "renewal_date": "Renewal date"}


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
        label = _SIGNAL_TYPE_LABELS.get(signal.signal_type, signal.signal_type)
        due = f" (due {signal.due_date.isoformat()})" if signal.due_date else ""
        _add_note(db, contact, f"{label} follow-up{due}: {signal.summary}")
        signal.status = "actioned"
    elif action_id == "dismiss":
        signal.status = "dismissed"
    else:
        raise ValueError(f"Unknown action {action_id!r} for signal_trigger")


register(ReviewKind(
    kind="signal_trigger",
    label="Budget window / renewal due",
    description="A budget window or renewal date extracted from real email correspondence is coming up (or was confirmed with no specific date).",
    actions=[
        ReviewAction(id="draft_followup", label="Draft follow-up", style="primary", outcome="approved"),
        ReviewAction(id="dismiss", label="Not relevant", style="secondary", outcome="rejected"),
    ],
    handler=_handle_signal_trigger,
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
            db.add(ReviewQueueItem(
                id=uuid.uuid4(), kind="signal_trigger",
                entity_type="contact", entity_id=contact.id,
                payload={
                    "summary": f"{label} for {contact_label}" + (f" - due {signal.due_date.isoformat()}" if signal.due_date else ""),
                    "details": [
                        {"key": "signal_type", "label": "Type", "value": label},
                        {"key": "due_date", "label": "Due date", "value": signal.due_date.isoformat() if signal.due_date else "(none stated)"},
                        {"key": "extracted", "label": "From the email thread", "value": signal.summary},
                    ],
                    "related_entities": [{"type": "contact", "id": str(contact.id), "label": contact_label}],
                    "signal_id": str(signal.id),
                    "confidence": signal.confidence,
                },
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
