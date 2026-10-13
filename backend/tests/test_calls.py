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


def test_not_configured_is_a_plain_message(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "notetaker_url", "")
    me = make_user(db_session)
    r = client.post("/api/calls", json={"meeting_url": "https://meet.google.com/abc-defg-hij"}, headers=identity_headers(me))
    assert r.status_code == 409 and "isn't set up" in r.json()["detail"]
