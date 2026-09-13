"""Review kinds for CS-001 (bounce classification) and CS-002 (out-of-office
replacement mining) - see docs/build-spec.txt for the full automation spec.

The mail-scanning job that actually reads mailboxes and populates these
review items doesn't exist yet (that's the next piece of work - Microsoft
Graph wiring + a Gemini classification call). What's here is the half that
*is* real end to end: once a review item of one of these kinds exists (for
now, seeded by hand for testing), acting on it makes a genuine CRM write
through the same Contact/Note/Email models and logic every other part of
the app already uses.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import MANUAL_SOURCE_DB
from app.automations.registry import ExtraField, ReviewAction, ReviewKind, register
from app.models import Contact, Email, Note, ReviewQueueItem


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
