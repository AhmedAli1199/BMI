import base64
import json
import os

import httpx

from notetaker import outbox, states
from notetaker.bots.attendee import AttendeeBot, sign
from notetaker.db import session_scope
from notetaker.models import Meeting, OutboxMessage
from notetaker.worker import tick

MEET = "https://meet.google.com/abc-defg-hij"


def auth(c):
    return {"Authorization": f"Bearer {c['api_key']}"}


def test_full_meeting_flow(api, client_key):
    r = api.post("/v1/meetings", json={"meeting_url": MEET, "external_id": "evt-1", "metadata": {"contact": "c1"}}, headers=auth(client_key))
    assert r.status_code == 201, r.text
    m = r.json()
    assert m["status"] == "scheduled" and m["platform"] == "google_meet"
    # the same calendar event again doesn't send a second bot
    again = api.post("/v1/meetings", json={"meeting_url": MEET, "external_id": "evt-1"}, headers=auth(client_key))
    assert again.status_code == 200 and again.json()["id"] == m["id"]

    with session_scope() as db:
        bot_id = db.get(Meeting, m["id"]).bot_id
    for s, key in [(states.JOINING, "k1"), (states.RECORDING, "k2"), (states.RECORDING, "k2"), (states.PROCESSING, "k3")]:
        assert api.post("/hooks/fake", json={"bot_id": bot_id, "status": s, "key": key}).status_code == 200

    sent = []
    def handler(req: httpx.Request):
        sent.append(req)
        return httpx.Response(200)
    import notetaker.outbox as ob
    orig = ob.httpx.Client
    ob.httpx.Client = lambda **kw: orig(transport=httpx.MockTransport(handler))
    try:
        tick()
    finally:
        ob.httpx.Client = orig

    got = api.get(f"/v1/meetings/{m['id']}", headers=auth(client_key)).json()
    assert got["status"] == "completed"
    assert got["notes"]["next_step"] == "Send the proposal"
    assert got["transcript"][0]["speaker"] == "Sarah Jones"
    assert [e["status"] for e in got["timeline"]] == ["scheduled", "joining", "recording", "processing", "completed"]

    events = [json.loads(r.content)["event"] for r in sent]
    assert events.count("meeting.completed") == 1 and events[0] == "meeting.status_changed"
    done = next(r for r in sent if json.loads(r.content)["event"] == "meeting.completed")
    body = done.content
    assert done.headers["X-Notetaker-Signature"] == outbox.signature(client_key["webhook_secret"], done.headers["X-Notetaker-Timestamp"], body)
    assert json.loads(body)["data"]["metadata"] == {"contact": "c1"}


def test_finished_meeting_never_goes_backwards(api, client_key):
    m = api.post("/v1/meetings", json={"meeting_url": MEET}, headers=auth(client_key)).json()
    with session_scope() as db:
        bot_id = db.get(Meeting, m["id"]).bot_id
    api.post("/hooks/fake", json={"bot_id": bot_id, "status": states.NOT_ADMITTED, "detail": "Nobody let it in"})
    api.post("/hooks/fake", json={"bot_id": bot_id, "status": states.RECORDING})
    got = api.get(f"/v1/meetings/{m['id']}", headers=auth(client_key)).json()
    assert got["status"] == "not_admitted" and got["status_detail"] == "Nobody let it in"


def test_rejects_bad_links_zoom_and_keys(api, client_key):
    bad = api.post("/v1/meetings", json={"meeting_url": "https://example.com/x"}, headers=auth(client_key))
    assert bad.status_code == 422 and "Google Meet" in bad.json()["detail"]
    zoom = api.post("/v1/meetings", json={"meeting_url": "https://us02web.zoom.us/j/123"}, headers=auth(client_key))
    assert zoom.status_code == 422 and "Zoom" in zoom.json()["detail"]
    assert api.get("/v1/meetings", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_concurrency_limit(api, client_key):
    ids = [api.post("/v1/meetings", json={"meeting_url": MEET}, headers=auth(client_key)).json() for _ in range(2)]
    with session_scope() as db:
        for x in ids:
            db.get(Meeting, x["id"]).status = states.RECORDING
    r = api.post("/v1/meetings", json={"meeting_url": MEET}, headers=auth(client_key))
    assert r.status_code == 422 and "already in 2 calls" in r.json()["detail"]


def test_clients_only_see_their_own(api, client_key):
    other = api.post("/admin/clients", json={"name": "Other"}, headers={"X-Admin-Token": "admin-t"}).json()
    m = api.post("/v1/meetings", json={"meeting_url": MEET}, headers=auth(client_key)).json()
    assert api.get(f"/v1/meetings/{m['id']}", headers=auth(other)).status_code == 404
    assert api.get("/v1/meetings", headers=auth(other)).json() == []


def test_webhook_retries_then_gives_up(api, client_key):
    api.post("/v1/meetings", json={"meeting_url": MEET}, headers=auth(client_key))
    with session_scope() as db:
        http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
        outbox.deliver_due(db, http=http)
        msg = db.query(OutboxMessage).one()
        assert msg.status == "pending" and msg.attempts == 1 and msg.last_error == "HTTP 500"


def test_internal_transcribe_needs_token(api):
    files = {"audio": ("a.mp3", b"123", "audio/mpeg")}
    assert api.post("/internal/transcribe", files=files).status_code == 401
    r = api.post("/internal/transcribe", files=files, headers={"X-Internal-Token": "int-t"})
    assert r.json()["status"] == "done" and r.json()["result"]["transcription"]["full_transcript"]


def test_attendee_webhook_parsing():
    secret = base64.b64encode(os.urandom(24)).decode()   # made up for each run, never a real key
    bot = AttendeeBot(base_url="http://x", api_key="k", webhook_secret=secret)
    payload = {"idempotency_key": "i1", "bot_id": "bot_1", "trigger": "bot.state_change",
               "data": {"new_state": "ended", "old_state": "post_processing", "event_type": "post_processing_completed", "event_sub_type": None}}
    u = bot.parse_webhook(json.dumps(payload).encode(), {"x-webhook-signature": sign(payload, secret)})
    assert u.status == states.PROCESSING and u.ready
    denied = {**payload, "data": {"new_state": "fatal_error", "event_type": "could_not_join_meeting", "event_sub_type": "request_to_join_denied"}}
    u2 = bot.parse_webhook(json.dumps(denied).encode(), {"x-webhook-signature": sign(denied, secret)})
    assert u2.status == states.NOT_ADMITTED and "turned the notetaker away" in u2.detail
    try:
        bot.parse_webhook(json.dumps(payload).encode(), {"x-webhook-signature": "wrong"})
        raise AssertionError("should reject")
    except PermissionError:
        pass


def test_attendee_create_and_transcript():
    seen = {}
    def handler(req: httpx.Request):
        if req.method == "POST" and req.url.path == "/api/v1/bots":
            seen["body"] = json.loads(req.content)
            return httpx.Response(201, json={"id": "bot_9"})
        if req.url.path.endswith("/transcript"):
            return httpx.Response(200, json=[
                {"speaker_name": "B", "timestamp_ms": 5000, "duration_ms": 1000, "transcription": {"transcript": "second"}},
                {"speaker_name": "A", "timestamp_ms": 1000, "duration_ms": 1000, "transcription": {"transcript": "first"}},
                {"speaker_name": "A", "timestamp_ms": 9000, "duration_ms": 0, "transcription": {"transcript": "  "}}])
        if req.url.path.endswith("/participants"):
            return httpx.Response(200, json=[{"name": "A"}, {"name": "B"}])
        return httpx.Response(404)
    from notetaker.bots.base import BotRequest
    bot = AttendeeBot(base_url="http://att", api_key="k", webhook_secret="", http=httpx.Client(transport=httpx.MockTransport(handler)))
    assert bot.create(BotRequest(meeting_id="m1", meeting_url=MEET, bot_name="BMI Notetaker", chat_message="Hi")) == "bot_9"
    assert seen["body"]["bot_name"] == "BMI Notetaker" and seen["body"]["bot_chat_message"] == {"message": "Hi"}
    assert seen["body"]["webhooks"][0]["url"].endswith("/hooks/attendee")
    res = bot.fetch_result("bot_9")
    assert [u.text for u in res.transcript] == ["first", "second"] and res.participants == ["A", "B"]
