"""Follow-up Engine + Morning Queue (SALES-005/012/013 from the automations
catalog) - the first producer job in this codebase that runs end to end:
scans real data, drafts real text (AI when configured, a plain template
when not), and writes a real review_queue row a rep acts on.

Unblocked by the 2026-09-18 Act! activity backfill: every migrated
Activity now carries a real contact_id/company_id (where Act!'s own
association data resolved to exactly one, see activity_link.py) and an
`organized_by_name` - enough to build a genuinely useful queue without
needing the still-parked Act!-accessor-to-our-user mapping (see
BACKLOG.md). A future backfill of that mapping only improves this
automation (real per-rep queues instead of grouping by a text name); it
doesn't block it.

Guardrail, same as every other automation in this codebase: this NEVER
sends anything. It drafts a follow-up and queues it for a human to review,
edit if needed, and send themselves through their own email client. See
registry.py's module docstring for the shared review-queue contract.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import MANUAL_SOURCE_DB
from app.automations import runtime_settings
from app.automations.llm import draft_text, is_configured
from app.automations.registry import ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.db.session import SessionLocal
from app.models import Activity, Company, Contact, HistoryEntry, ReviewQueueItem

# How far back/forward to look for "due" activities, and how many to draft
# per run - configurable via FOLLOWUP_LOOKBACK_DAYS/FOLLOWUP_LOOKAHEAD_DAYS/
# FOLLOWUP_MAX_PER_RUN (see app/core/config.py), deliberately bounded by
# default rather than "every incomplete Act! activity ever" - the migrated
# backlog goes back years (see BACKLOG.md's note on the Calendar & Task
# List's unbounded Open tab), and nobody wants an AI-drafted follow-up for
# a to-do from 2019 by default. Only activities that are due soon or went
# overdue recently are genuinely "due for a follow-up today" - anything
# older is stale backlog to triage separately, not a live queue candidate.
# Widen these (env var + restart, no code change) if your data is mostly
# historical rather than forward-looking, same as right after a migration.


def _entity_label(contact: Contact | None, company: Company | None) -> str:
    if contact:
        return contact.full_name or " ".join(filter(None, [contact.first_name, contact.last_name])) or "this contact"
    if company:
        return company.name or "this company"
    return "this record"


def _add_history(db: Session, *, entity_type: str, entity_id: uuid.UUID, subject: str, body: str) -> None:
    db.add(HistoryEntry(
        id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()),
        entity_type=entity_type, entity_id=entity_id,
        history_type="Email Sent", subject=subject, details=body,
        occurred_at=datetime.now(timezone.utc),
    ))


def _handle_followup(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    activity = db.get(Activity, item.entity_id) if item.entity_id else None
    if not activity:
        raise ValueError("The activity this follow-up was drafted from no longer exists - it may have been deleted.")

    if action_id == "mark_sent":
        entity_type = "contact" if activity.contact_id else "company"
        entity_id = activity.contact_id or activity.company_id
        if not entity_id:
            raise ValueError("This activity is no longer linked to a contact or company.")
        note = input_data.get("note", "").strip()
        body = note or item.payload.get("original_text") or "(no draft text captured)"
        _add_history(
            db, entity_type=entity_type, entity_id=entity_id,
            subject=activity.subject or "Follow-up sent", body=body,
        )
        activity.is_cleared = True

    elif action_id == "snooze":
        activity.start_at = datetime.now(timezone.utc) + timedelta(days=7)

    elif action_id == "dismiss":
        pass  # No write - reviewer is telling us this one doesn't need a follow-up right now.

    else:
        raise ValueError(f"Unknown action {action_id!r} for followup_due")


register(ReviewKind(
    kind="followup_due",
    label="Follow-up due",
    description=(
        "A scheduled call, meeting or to-do is due or just went overdue. Review the draft, send it "
        "yourself from your own inbox, then mark it sent here so it's logged and cleared."
    ),
    actions=[
        ReviewAction(
            id="mark_sent", label="Mark sent", style="primary", outcome="approved",
            requires_note=False,
        ),
        ReviewAction(id="snooze", label="Snooze 1 week", style="secondary", outcome="approved"),
        ReviewAction(id="dismiss", label="Dismiss", style="destructive", outcome="rejected"),
    ],
    handler=_handle_followup,
))


def _draft_followup_text(activity: Activity, contact: Contact | None, company: Company | None) -> tuple[str, bool]:
    """Returns (draft_text, was_ai_generated). Always returns something
    usable - AI when configured, a plain templated line otherwise - never
    blocks the item from being queued just because no key is set."""
    who = _entity_label(contact, company)
    subject = activity.subject or activity.activity_type or "a follow-up"

    if is_configured():
        context = (
            f"Activity type: {activity.activity_type or 'follow-up'}\n"
            f"Subject: {subject}\n"
            f"Due: {activity.start_at.strftime('%d %b %Y')}\n"
            f"Contact/company: {who}\n"
            f"Notes on the activity: {activity.details or '(none)'}\n"
            f"Originally organized by: {activity.organized_by_name or 'unknown'}\n"
        )
        ai_text = draft_text(
            system_prompt=(
                "You are drafting a short, warm, professional follow-up email on behalf of a BMI "
                "Publishing salesperson, based on a CRM activity that's due. Write only the email body "
                "(no subject line, no greeting placeholders like [Name] - use the actual name given). "
                "Keep it under 120 words. Never invent facts, prices, or commitments not present in the "
                "context - if the context is thin, keep the email general rather than fabricating detail."
            ),
            user_prompt=context,
        )
        if ai_text:
            return ai_text, True

    # Fallback - always available, no AI dependency.
    return (
        f"Hi {who},\n\n"
        f"Following up on \"{subject}\" - just wanted to check in and see where things stand.\n\n"
        f"Let me know a good time to connect.\n"
    ), False


def scan_for_due_followups() -> None:
    """Producer job: finds Activities due (or recently overdue) that are
    linked to a real contact/company, drafts a follow-up for each, and
    queues a `followup_due` review item - unless one's already pending for
    that same activity."""
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        window_start = now - timedelta(days=runtime_settings.get_int(db, "followup_lookback_days"))
        window_end = now + timedelta(days=runtime_settings.get_int(db, "followup_lookahead_days"))
        max_per_run = runtime_settings.get_int(db, "followup_max_per_run")

        already_queued = set(
            db.scalars(
                select(ReviewQueueItem.entity_id).where(
                    ReviewQueueItem.kind == "followup_due",
                    ReviewQueueItem.status == "pending",
                )
            ).all()
        )

        candidates = db.scalars(
            select(Activity)
            .where(
                Activity.is_cleared.is_(False),
                Activity.start_at >= window_start,
                Activity.start_at <= window_end,
                Activity.contact_id.isnot(None) | Activity.company_id.isnot(None),
            )
            .order_by(Activity.start_at.asc())
            .limit(max_per_run * 3)  # headroom for the already-queued rows we'll filter out below
        ).all()

        queued_count = 0
        for activity in candidates:
            if queued_count >= max_per_run:
                break
            if activity.id in already_queued:
                continue

            contact = db.get(Contact, activity.contact_id) if activity.contact_id else None
            company = db.get(Company, activity.company_id) if activity.company_id else None
            draft, was_ai = _draft_followup_text(activity, contact, company)
            entity_type = "contact" if contact else "company"
            related_id = str(contact.id) if contact else str(company.id) if company else None

            db.add(ReviewQueueItem(
                id=uuid.uuid4(),
                kind="followup_due",
                entity_type="activity",
                entity_id=activity.id,
                payload={
                    "summary": f"{activity.activity_type or 'Follow-up'} due for {_entity_label(contact, company)}"
                               f" - \"{activity.subject or '(no subject)'}\"",
                    "details": [
                        {"key": "due", "label": "Due", "value": activity.start_at.strftime("%d %b %Y")},
                        {"key": "type", "label": "Type", "value": activity.activity_type or "-"},
                        {"key": "priority", "label": "Priority", "value": activity.priority},
                        {"key": "draft_source", "label": "Draft", "value": "AI-drafted" if was_ai else "Templated (no AI configured)"},
                    ],
                    "original_text": draft,
                    "related_entities": (
                        [{"type": entity_type, "id": related_id, "label": _entity_label(contact, company)}]
                        if related_id else []
                    ),
                    "confidence": 0.7 if was_ai else None,
                },
            ))
            queued_count += 1

        db.commit()
        print(f"followup_due scan: {queued_count} new item(s) queued "
              f"({len(candidates)} candidates in window, {len(already_queued)} already pending)")
    finally:
        db.close()


register_job(ScheduledJob(
    id="followup_engine_scan",
    label="Follow-up due scan",
    description="Finds due/overdue activities linked to a contact or company and drafts a follow-up for review.",
    cron="0 7-18 * * 1-5",  # hourly, business hours, weekdays - a queue that grows all night isn't more useful
    func=scan_for_due_followups,
    enabled_flag="automations_followup_scan_enabled",
))
