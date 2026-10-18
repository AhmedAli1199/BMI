"""Call notes: send the notetaker, receive its signed webhook, review the notes, save them to history."""
import hashlib
import hmac
import json
import time
import uuid

from tests.conftest import identity_headers, make_user

from app.core.config import settings
from app.models import CallRecording, Company, Contact, HistoryEntry, ReviewQueueItem
from app.models.messaging import Reminder
from app.services import notetaker


def _signed(body: dict, secret: str):
    raw = json.dumps(body).encode()
    ts = str(int(time.time()))
    sig = "sha256=" + hmac.new(secret.encode(), ts.encode() + b"." + raw, hashlib.sha256).hexdigest()
    return raw, {"X-Notetaker-Timestamp": ts, "X-Notetaker-Signature": sig, "Content-Type": "application/json"}


def test_send_receive_and_save(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "notetaker_url", "http://nt")
    monkeypatch.setattr(settings, "notetaker_api_key", "k")
    monkeypatch.setattr(settings, "notetaker_webhook_secret", "s3cret")
    sent = {}
    def fake_send(**kw):
        sent.update(kw)
        return {"id": "nt_1", "platform": "google_meet", "status": "scheduled", "status_label": "Scheduled"}
    monkeypatch.setattr(notetaker, "send_bot", fake_send)

    me, other = make_user(db_session), make_user(db_session)
    co = Company(id=uuid.uuid4(), name="Caribbean Tourism", source_db="onboard", source_act_id=str(uuid.uuid4()))
    db_session.add(co)
    db_session.flush()
    ct = Contact(id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()), full_name="Sarah Jones", company_id=co.id)
    db_session.add(ct)
    db_session.flush()

    r = client.post("/api/calls", json={"meeting_url": "https://meet.google.com/abc-defg-hij", "title": "Spring campaign", "contact_id": str(ct.id)},
                    headers=identity_headers(me))
    assert r.status_code == 201, r.text
    call = r.json()
    assert call["company"]["name"] == "Caribbean Tourism" and sent["external_id"] == call["id"]
    # someone else's call is invisible to another salesperson
    assert client.get(f"/api/calls/{call['id']}", headers=identity_headers(other)).status_code == 404

    notes = {"title": "Spring campaign", "summary": "Sarah wants a spread and the newsletter.", "next_step": "Send the proposal",
             "key_points": [], "decisions": [], "money_mentioned": ["£5,000 for both"], "dates_mentioned": [], "sentiment": "positive",
             "action_items": [{"task": "Send the proposal", "owner": "Matt", "due": "today"}]}
    body = {"id": "d1", "event": "meeting.completed", "data": {"id": "nt_1", "status": "completed", "status_label": "Notes ready",
            "metadata": {"bmi_call_id": call["id"]}, "participants": ["Sarah Jones", "Matt"], "notes": notes,
            "transcript": [{"speaker": "Sarah Jones", "start_ms": 0, "end_ms": 1000, "text": "Hello"}]}}
    raw, h = _signed(body, "s3cret")
    assert client.post("/api/calls/webhook", content=raw, headers=h).status_code == 200
    raw2, h2 = _signed(body, "wrong")
    assert client.post("/api/calls/webhook", content=raw2, headers=h2).status_code == 401
    client.post("/api/calls/webhook", content=raw, headers=h)   # a repeat delivery doesn't make a second card

    items = db_session.query(ReviewQueueItem).filter_by(kind="call_notes").all()
    assert len(items) == 1
    hrefs = {d["label"]: d.get("href") for d in items[0].payload["details"]}
    assert hrefs["Contact"] == f"/contacts/{ct.id}" and hrefs["Company"] == f"/companies/{co.id}" and hrefs["Call"] == f"/calls/{call['id']}"
    assert items[0].payload["facets"]["interest"] == "Interested"

    got = client.get(f"/api/calls/{call['id']}", headers=identity_headers(me)).json()
    assert got["status"] == "completed" and got["transcript"][0]["text"] == "Hello"

    r = client.post(f"/api/review-queue/{items[0].id}/actions/save", json={}, headers=identity_headers(me))
    assert r.status_code == 200, r.text
    h = db_session.query(HistoryEntry).filter_by(entity_id=ct.id, history_type="Meeting Held").one()
    assert "Send the proposal" in h.details and "£5,000" in h.details
    assert db_session.query(Reminder).filter_by(contact_id=ct.id).count() == 1
    assert db_session.get(CallRecording, uuid.UUID(call["id"])).saved_to_history_at is not None


def test_action_item_due_dates_are_read_from_the_words_used():
    from datetime import date
    from app.automations.call_notes import due_from_text
    wed = date(2026, 10, 14)
    cases = {"by Friday": date(2026, 10, 16), "Friday": date(2026, 10, 16), "next Wednesday": date(2026, 10, 21),
             "next week": date(2026, 10, 19), "tomorrow": date(2026, 10, 15), "today": wed, "by 14 Nov": date(2026, 11, 14),
             "14th of November 2026": date(2026, 11, 14), "Nov 3rd": date(2026, 11, 3), "by 14/11": date(2026, 11, 14),
             "2026-12-01": date(2026, 12, 1), "in two weeks": date(2026, 10, 28), "in 3 working days": date(2026, 10, 19),
             "end of the week": date(2026, 10, 16), "end of the month": date(2026, 10, 31), "next month": date(2026, 11, 1),
             "by November": date(2026, 11, 1), "mid-January": date(2027, 1, 15), "by 5 Jan": date(2027, 1, 5)}
    assert {k: due_from_text(k, wed) for k in cases} == cases
    assert due_from_text("soon", wed) is None and due_from_text(None, wed) is None


def test_reminders_follow_the_agreed_day_and_saving_closes_the_card(client, db_session):
    from datetime import date, datetime, timezone
    from app.automations import call_notes
    me = make_user(db_session)
    ct = Contact(id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()), full_name="Sarah Jones")
    db_session.add(ct)
    call = CallRecording(id=uuid.uuid4(), user_id=me.id, meeting_url="https://meet.google.com/abc-defg-hij", title="Spring campaign",
                         status="completed", status_label="Notes ready", ended_at=datetime(2026, 10, 14, 15, 0, tzinfo=timezone.utc),
                         notes={"summary": "Sarah wants a spread.", "sentiment": "positive",
                                "action_items": [{"task": "Send the proposal", "due": "by Friday"}, {"task": "Call back"}]})
    db_session.add(call)
    db_session.flush()
    call_notes.queue_for_review(db_session, call)
    db_session.flush()
    card = db_session.query(ReviewQueueItem).filter_by(kind="call_notes").one()
    assert card.entity_id is None and card.payload["facets"]["linked"] == "Not linked to a contact"
    # the contact is linked on the call's page after the card was made: the card shows them
    r = client.patch(f"/api/calls/{call.id}", json={"contact_id": str(ct.id)}, headers=identity_headers(me))
    assert r.status_code == 200, r.text
    db_session.refresh(card)
    assert card.entity_type == "contact" and card.entity_id == ct.id and card.payload["facets"]["linked"] == "Linked to a contact"
    assert {d["label"]: d.get("href") for d in card.payload["details"]}["Contact"] == f"/contacts/{ct.id}"
    # Save to history on the call's page closes the card
    r = client.post(f"/api/calls/{call.id}/save-to-history", headers=identity_headers(me))
    assert r.status_code == 200, r.text
    db_session.refresh(card)
    assert card.status == "approved" and card.resolved_action == "save" and card.reviewed_by_user_id == me.id
    due = {x.note.split(" ")[0]: x.due_at for x in db_session.query(Reminder).filter_by(contact_id=ct.id)}
    assert due["Send"] == call_notes.reminder_due(call, "by Friday")
    assert due["Call"] == call_notes.reminder_due(call, None)
    # 9am UK time on the Friday after the call; never in the past; no day given: the next working day
    assert call_notes.reminder_due(call, "by Friday", today=date(2026, 10, 14)) == datetime(2026, 10, 16, 8, 0, tzinfo=timezone.utc)
    assert call_notes.reminder_due(call, "by Friday", today=date(2026, 10, 20)) == datetime(2026, 10, 20, 8, 0, tzinfo=timezone.utc)
    assert call_notes.reminder_due(call, None, today=date(2026, 10, 16)) == datetime(2026, 10, 19, 8, 0, tzinfo=timezone.utc)


def test_not_configured_is_a_plain_message(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "notetaker_url", "")
    me = make_user(db_session)
    r = client.post("/api/calls", json={"meeting_url": "https://meet.google.com/abc-defg-hij"}, headers=identity_headers(me))
    assert r.status_code == 409 and "isn't set up" in r.json()["detail"]
