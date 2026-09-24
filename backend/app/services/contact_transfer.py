"""Moving a contact's notes/history to another contact - "when a contact
leaves a particular company, we can easily move notes in ACT from that
person to a new person - we need this ability" (BMI's own Act pain-points
doc).

Deliberately a plain, standalone function rather than something buried
inside a route handler or an automation's review-action handler: it's
called directly from the manual "Reassign to" action on a contact's page
(app/api/routes/contacts.py), and is exactly the piece CS-003's
departure-detection automation (app/automations/departure.py) would call
too if its detection side is ever built - the rep-initiated case and the
someday-automated case should always move records the same way, not grow
two different implementations that quietly drift apart.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.api.schemas import MANUAL_SOURCE_DB
from app.models import Contact, HistoryEntry, Note


def reassign_contact_records(
    db: Session, *, source: Contact, destination: Contact, reason: str = "manually confirmed"
) -> None:
    """Moves every Note/HistoryEntry from `source` to `destination` (a
    bulk UPDATE, not a copy - the record genuinely now belongs to the new
    contact), and leaves a short explanatory note on both sides so anyone
    reading either record later understands why the history moved.
    Caller commits."""
    source_label = source.full_name or source.first_name or "the previous contact"
    destination_label = destination.full_name or destination.first_name or "the new contact"

    db.execute(
        Note.__table__.update()
        .where(Note.entity_type == "contact", Note.entity_id == source.id)
        .values(entity_id=destination.id)
    )
    db.execute(
        HistoryEntry.__table__.update()
        .where(HistoryEntry.entity_type == "contact", HistoryEntry.entity_id == source.id)
        .values(entity_id=destination.id)
    )

    now = datetime.now(timezone.utc)
    db.add(Note(
        id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()),
        entity_type="contact", entity_id=source.id, note_type="Departure",
        body=f"Notes and history moved to {destination_label} ({reason}).",
        act_created_at=now,
    ))
    db.add(Note(
        id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()),
        entity_type="contact", entity_id=destination.id, note_type="Departure",
        body=f"Received notes and history from {source_label} ({reason}).",
        act_created_at=now,
    ))
