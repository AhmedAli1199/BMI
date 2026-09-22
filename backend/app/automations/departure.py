"""Review kind for CS-003 (departure detection & successor finding) - the
highest-stakes automation in this stage, since writing the wrong successor
means the wrong person gets pitched/invoiced/mailed. Every path here
requires a human to confirm before anything is written - there is no
"auto-approve" branch, unlike the bounce/OOO kinds.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.api.schemas import MANUAL_SOURCE_DB
from app.automations.registry import ExtraField, ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.models import Contact, Note, ReviewQueueItem


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


def _related_contact_ids(item: ReviewQueueItem) -> list[uuid.UUID]:
    """Every record the departed person holds - the "6+ records across
    titles" fan-out CS-003 is meant to solve. Populated by the departure
    job into payload["related_entities"]; item.entity_id is always
    included too as a safety net so a hand-seeded item still works."""
    ids = {e["id"] for e in item.payload.get("related_entities", []) if e.get("type") == "contact"}
    if item.entity_id:
        ids.add(str(item.entity_id))
    return [uuid.UUID(i) if not isinstance(i, uuid.UUID) else i for i in ids]


def _apply_successor(db: Session, item: ReviewQueueItem, successor: Contact, source_label: str) -> None:
    for contact_id in _related_contact_ids(item):
        record = db.get(Contact, contact_id)
        if not record:
            continue  # deleted/merged since this was queued - skip, don't fail the whole batch over it
        _add_note(
            db, record, "Departure",
            f"Superseded by {successor.full_name or successor.first_name} ({source_label}), "
            f"confirmed via review queue.",
        )
    _add_note(db, successor, "Departure", f"Confirmed as successor for the departed contact(s) linked to this review item.")


def _handle_departure(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "confirm_successor":
        candidate = item.payload.get("candidate") or {}
        contact_id = candidate.get("contact_id")
        if not contact_id:
            raise ValueError("No researched candidate is attached to this item - use \"Pick someone else\" instead.")
        successor = db.get(Contact, contact_id)
        if not successor:
            raise ValueError("The researched candidate no longer exists in the CRM.")
        _apply_successor(db, item, successor, candidate.get("source", "researched match"))

    elif action_id == "pick_different_successor":
        contact_id = input_data.get("contact_id")
        if not contact_id:
            raise ValueError("Pick who the successor actually is.")
        successor = db.get(Contact, contact_id)
        if not successor:
            raise ValueError("That contact no longer exists.")
        _apply_successor(db, item, successor, "manually confirmed")

    elif action_id == "use_fallback":
        fallback_email = input_data.get("fallback_email", "").strip()
        if not fallback_email:
            raise ValueError("Enter the verified general company address to use as the fallback.")
        for contact_id in _related_contact_ids(item):
            record = db.get(Contact, contact_id)
            if not record:
                continue
            _add_note(
                db, record, "Departure",
                f"No confirmed successor - falling back to general company address ({fallback_email}), "
                f"confirmed via review queue. This is a placeholder, not a verified individual.",
            )

    elif action_id == "dismiss_false_alarm":
        pass  # No CRM write - the reviewer is telling us this wasn't really a departure.

    else:
        raise ValueError(f"Unknown action {action_id!r} for departure_unconfirmed")


register(ReviewKind(
    kind="departure_unconfirmed",
    label="Executive Role Departures",
    description="Contacts detected as having moved on, with proposed same-company successors ready for review.",
    actions=[
        ReviewAction(
            id="confirm_successor", label="Confirm successor", style="primary", outcome="approved",
            confirm_message="This updates the contact record across all active publication titles. Continue?",
        ),
        ReviewAction(id="pick_different_successor", label="Assign different contact", style="secondary", outcome="approved", requires_contact_picker=True),
        ReviewAction(
            id="use_fallback", label="Use general company address", style="secondary", outcome="approved",
            extra_fields=[ExtraField(key="fallback_email", label="General company email", placeholder="info@company.com")],
        ),
        ReviewAction(id="dismiss_false_alarm", label="Dismiss (contact remains)", style="secondary", outcome="rejected", confirm_message="Dismiss this departure signal?"),
    ],
    handler=_handle_departure,
))


def scan_for_departures() -> None:
    """CS-003 producer: scans recent mailbox signals (bounces, OOO text
    mentioning a departure, etc.) plus whatever research step finds a
    likely successor, and writes a `departure_unconfirmed` row.

    Not implemented yet - depends on the same Graph/Gemini wiring as
    scan_mailbox_for_bounces_and_ooo (see bounce_handling.py), plus
    whatever successor-research step (LinkedIn search, company website,
    ...) CS-003 ends up using. Wired into the scheduler now so enabling
    CS-003 later is only: fill this body in, set
    AUTOMATIONS_DEPARTURE_SCAN_ENABLED=true, restart.
    """
    raise NotImplementedError(
        "Departure scanning for CS-003 isn't built yet - "
        "see scan_for_departures's docstring."
    )


register_job(ScheduledJob(
    id="cs003_departure_scan",
    label="Departure & successor scan",
    description="Looks for departure signals and researches a likely successor (CS-003).",
    cron="0 */6 * * *",  # every 6 hours - lower-frequency, higher-stakes signal than the bounce scan
    func=scan_for_departures,
    enabled_flag="automations_departure_scan_enabled",
))
