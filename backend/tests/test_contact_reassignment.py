"""Manual note/history reassignment when a contact leaves a company -
"when a contact leaves a particular company, we can easily move notes in
ACT from that person to a new person - we need this ability" (BMI's Act
pain-points doc). See app/services/contact_transfer.py."""
import uuid

from app.models import Contact, HistoryEntry, Note
from datetime import datetime, timezone


def _create_contact(client, **overrides):
    payload = {"first_name": "Old", "last_name": "Contact"}
    payload.update(overrides)
    resp = client.post("/api/contacts", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_reassign_moves_notes_and_history(client, db_session):
    source = _create_contact(client, first_name="Departing", last_name="Person")
    destination = _create_contact(client, first_name="New", last_name="Person")

    db_session.add(Note(
        id=uuid.uuid4(), source_db="manual", source_act_id=str(uuid.uuid4()),
        entity_type="contact", entity_id=uuid.UUID(source["id"]),
        note_type="Note", body="Discussed renewal pricing.", act_created_at=datetime.now(timezone.utc),
    ))
    db_session.add(HistoryEntry(
        id=uuid.uuid4(), source_db="manual", source_act_id=str(uuid.uuid4()),
        entity_type="contact", entity_id=uuid.UUID(source["id"]),
        history_type="Call", subject="Renewal call", occurred_at=datetime.now(timezone.utc),
    ))
    db_session.flush()

    resp = client.post(f"/api/contacts/{source['id']}/reassign/{destination['id']}")
    assert resp.status_code == 204

    source_detail = client.get(f"/api/contacts/{source['id']}").json()
    destination_detail = client.get(f"/api/contacts/{destination['id']}").json()

    # The original note/history moved off the departed contact...
    assert not any(n["body"] == "Discussed renewal pricing." for n in source_detail["notes"])
    assert not any(h["subject"] == "Renewal call" for h in source_detail["history"])
    # ...and now live on the successor.
    assert any(n["body"] == "Discussed renewal pricing." for n in destination_detail["notes"])
    assert any(h["subject"] == "Renewal call" for h in destination_detail["history"])

    # Both records get an explanatory note about the handover.
    assert any("moved to New Person" in n["body"] for n in source_detail["notes"])
    assert any("Received notes and history from Departing Person" in n["body"] for n in destination_detail["notes"])


def test_reassign_to_self_rejected(client, db_session):
    contact = _create_contact(client)
    resp = client.post(f"/api/contacts/{contact['id']}/reassign/{contact['id']}")
    assert resp.status_code == 400


def test_reassign_unknown_source_404s(client, db_session):
    destination = _create_contact(client)
    resp = client.post(f"/api/contacts/{uuid.uuid4()}/reassign/{destination['id']}")
    assert resp.status_code == 404


def test_reassign_unknown_destination_400s(client, db_session):
    source = _create_contact(client)
    resp = client.post(f"/api/contacts/{source['id']}/reassign/{uuid.uuid4()}")
    assert resp.status_code == 400
