"""Regression coverage for the OOO review-queue flooding complaint from
the Sept 23 demo ("the review queue was almost filled entirely by these
out-of-office emails"): a contact whose auto-reply fires on every new
thread during a two-week absence used to get one ooo_ambiguous item per
message. Fixed by _handle_candidate_ooo skipping a contact that already
has a pending item - see bounce_handling.py."""
import uuid
from datetime import datetime, timezone

from app.automations.bounce_handling import _handle_candidate_ooo
from app.automations.mail_parsing import ParsedMessage
from app.models import Contact, ReviewQueueItem


def _make_contact(db_session, **overrides) -> Contact:
    defaults = dict(
        id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()),
        first_name="Gary", last_name="Holiday",
    )
    defaults.update(overrides)
    contact = Contact(**defaults)
    db_session.add(contact)
    db_session.flush()
    return contact


def _ooo_message(from_address: str, message_id: str) -> ParsedMessage:
    return ParsedMessage(
        message_id=message_id,
        internet_message_id=None,
        from_address=from_address,
        from_name="Gary Holiday",
        subject="Out of office",
        received_at=datetime.now(timezone.utc),
        body_text="I am out of the office until further notice.",
    )


def test_second_ooo_message_from_an_already_pending_contact_is_skipped(db_session):
    contact = _make_contact(db_session)
    from app.models import Email
    db_session.add(Email(
        id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()),
        contact_id=contact.id, address="gary@example.com", is_primary=True,
    ))
    db_session.flush()

    # Simulate what a real first queued item does: mark the contact
    # pending, exactly as _handle_candidate_ooo does internally right
    # after a successful queue (see pending_ooo_contacts.add(original.id)).
    pending_ooo_contacts: set[uuid.UUID] = {contact.id}

    # A second, different message (different message_id - a fresh
    # auto-reply, not a re-processed duplicate) from the same contact
    # while still pending must be skipped before ever reaching the LLM
    # classification step - this is the actual flooding fix.
    msg2 = _ooo_message("gary@example.com", "msg-2")
    queued = _handle_candidate_ooo(db_session, msg2, pending_ooo_contacts)
    assert queued is False

    # No review item was written for the skipped second message.
    items = db_session.query(ReviewQueueItem).filter(ReviewQueueItem.kind == "ooo_ambiguous").all()
    assert items == []
