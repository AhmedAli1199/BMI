"""A permanent-departure auto-reply ("I have now departed the company &
retired...") must route to departure_unconfirmed (CS-003's review kind),
not ooo_ambiguous - a departure needs a successor confirmed and records
reassigned, not a handover note with a "due back" date. Regression for
the bug where every departure notice landed as an out-of-office card
because scan_for_departures (CS-003's own detection) was never built and
_classify_ooo had no concept of "left permanently" vs "away for now"."""
import uuid
from datetime import datetime, timezone

import app.automations.bounce_handling as bounce_handling
from app.automations.bounce_handling import _handle_candidate_ooo
from app.automations.mail_parsing import ParsedMessage
from app.models import Contact, Email, ReviewQueueItem


def _make_contact(db_session, **overrides) -> Contact:
    defaults = dict(
        id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()),
        first_name="Paul", last_name="Dowdy",
    )
    defaults.update(overrides)
    contact = Contact(**defaults)
    db_session.add(contact)
    db_session.flush()
    return contact


def _departure_message(from_address: str) -> ParsedMessage:
    return ParsedMessage(
        message_id="msg-departure-1",
        internet_message_id=None,
        from_address=from_address,
        from_name="Paul Dowdy",
        subject="Automatic reply: [EXTERNAL] The AIR-mazing Awards",
        received_at=datetime.now(timezone.utc),
        body_text=(
            "I have now departed Chubb & retired, so for any queries please contact "
            "Bhavisha Hartley at bhavisha.hartley@chubb.com.\n\nMany thanks Paul\n\n"
            "For any urgent issues please send to: emeatravelqueries@chubb.com where "
            "this will be picked up by the Purchasing Team.\n\nRegards\nPaul"
        ),
    )


def test_explicit_departure_language_routes_to_departure_unconfirmed(db_session, monkeypatch):
    contact = _make_contact(db_session)
    db_session.add(Email(
        id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()),
        contact_id=contact.id, address="paul.dowdy@chubb.com", is_primary=True,
    ))
    db_session.flush()

    monkeypatch.setattr(
        bounce_handling, "_classify_ooo",
        lambda msg: {
            "is_genuine_absence": True,
            "is_departure": True,
            "confidence": 0.95,
            "return_date": None,
            "replacements": [{"name": "Bhavisha Hartley", "email": "bhavisha.hartley@chubb.com", "role": None}],
        },
    )

    queued = _handle_candidate_ooo(db_session, _departure_message("paul.dowdy@chubb.com"), set())
    assert queued is True

    ooo_items = db_session.query(ReviewQueueItem).filter(ReviewQueueItem.kind == "ooo_ambiguous").all()
    assert ooo_items == []

    departure_items = db_session.query(ReviewQueueItem).filter(ReviewQueueItem.kind == "departure_unconfirmed").all()
    assert len(departure_items) == 1
    item = departure_items[0]
    assert item.entity_id == contact.id
    assert "departed" in item.payload["summary"].lower()
    assert item.payload["candidate"] is None  # Bhavisha isn't in the CRM as a contact - no match to auto-fill


def test_temporary_absence_still_routes_to_ooo_ambiguous(db_session, monkeypatch):
    contact = _make_contact(db_session, first_name="Gary", last_name="Holiday")
    db_session.add(Email(
        id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()),
        contact_id=contact.id, address="gary@example.com", is_primary=True,
    ))
    db_session.flush()

    monkeypatch.setattr(
        bounce_handling, "_classify_ooo",
        lambda msg: {
            "is_genuine_absence": True,
            "is_departure": False,
            "confidence": 0.8,
            "return_date": "2026-10-05",
            "replacements": [],
        },
    )

    msg = ParsedMessage(
        message_id="msg-holiday-1", internet_message_id=None,
        from_address="gary@example.com", from_name="Gary Holiday",
        subject="Out of office", received_at=datetime.now(timezone.utc),
        body_text="I am on annual leave until 2026-10-05.",
    )
    queued = _handle_candidate_ooo(db_session, msg, set())
    assert queued is True

    assert db_session.query(ReviewQueueItem).filter(ReviewQueueItem.kind == "departure_unconfirmed").all() == []
    ooo_items = db_session.query(ReviewQueueItem).filter(ReviewQueueItem.kind == "ooo_ambiguous").all()
    assert len(ooo_items) == 1
