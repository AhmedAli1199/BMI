"""Connect Zoom: Zoom lets the notetaker into a call only on behalf of a signed-in person in it, so each person
connects their Zoom once; Zoom meetings on the shared calendar go on behalf of the BMI organiser (or whoever from
BMI going has connected)."""
import uuid
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest

from app.core.config import settings
from app.models import ZoomConnection
from app.services import calendar_sync as cs
from app.services import notetaker, outlook, zoom
from tests.conftest import identity_headers, make_user
from tests.test_calendar_sync import NOW, ev, meetings, people  # noqa: F401 - the shared fixture

ZOOM = "https://us02web.zoom.us/j/81234567890?pwd=abc"


@pytest.fixture()
def zoom_on(monkeypatch):
    monkeypatch.setattr(settings, "notetaker_url", "http://nt")
    monkeypatch.setattr(settings, "notetaker_api_key", "k")
    monkeypatch.setattr(settings, "app_base_url", "https://bmi.rabtaai.com")
    monkeypatch.setattr(notetaker, "zoom_info", lambda fresh=False: {"available": True, "client_id": "Ot_syquQQk2zwZYfhRC3Nw"})
    calls = []
    monkeypatch.setattr(notetaker, "zoom_connect", lambda code, redirect_uri, external_user: calls.append((code, redirect_uri, external_user))
                        or {"zoom_user_id": f"zu_{external_user[:6]}", "state": "connected"})
    monkeypatch.setattr(notetaker, "zoom_disconnect", lambda zid: calls.append(("off", zid)))
    return calls


def test_connect_zoom_sign_in_and_way_back(client, db_session, zoom_on):
    sally = make_user(db_session, role="sales", name="Sally Parker")
    h = identity_headers(sally)
    r = client.get("/api/zoom/start", headers=h)
    assert r.status_code == 200, r.text
    url = urlparse(r.json()["url"])
    q = parse_qs(url.query)
    assert url.netloc == "zoom.us" and q["client_id"] == ["Ot_syquQQk2zwZYfhRC3Nw"]
    assert q["redirect_uri"] == ["https://bmi.rabtaai.com/api/zoom/callback"]   # must match the Zoom app exactly

    r = client.post("/api/zoom/callback", json={"code": "abc", "state": q["state"][0]})
    assert r.status_code == 200 and r.json()["return_to"] == "/calls/meetings"
    assert zoom_on[-1] == ("abc", "https://bmi.rabtaai.com/api/zoom/callback", str(sally.id))
    conn = db_session.query(ZoomConnection).filter_by(user_id=sally.id).one()
    assert conn.status == "connected"

    # a calendar sign-in link can't be reused for Zoom
    other = outlook.make_state(sally.id, "/calls/meetings", purpose="calendar")
    r = client.post("/api/zoom/callback", json={"code": "abc", "state": other})
    assert r.status_code == 400 and "isn't valid any more" in r.json()["detail"]

    assert client.delete("/api/zoom/connection", headers=h).status_code == 204
    assert db_session.query(ZoomConnection).filter_by(user_id=sally.id).count() == 0 and zoom_on[-1][0] == "off"


def test_zoom_own_add_app_now_connects_whoever_is_signed_in(client, db_session, zoom_on):
    ahmed = make_user(db_session, role="admin", name="Ahmed")
    r = client.post("/api/zoom/callback", json={"code": "from-zoom", "state": None}, headers=identity_headers(ahmed))
    assert r.status_code == 200
    assert db_session.query(ZoomConnection).filter_by(user_id=ahmed.id).one()
    r = client.post("/api/zoom/callback", json={"code": "from-zoom", "state": None})   # nobody signed in
    assert r.status_code == 400 and "Sign in to BMI Brain first" in r.json()["detail"]


def test_not_set_up_says_so(client, db_session, monkeypatch):
    monkeypatch.setattr(notetaker, "zoom_info", lambda fresh=False: {"available": False, "client_id": None})
    sally = make_user(db_session, role="sales", name="Sally Parker")
    r = client.get("/api/zoom/start", headers=identity_headers(sally))
    assert r.status_code == 400 and "Zoom isn't set up on the notetaker yet" in r.json()["detail"]


def test_zoom_meetings_go_on_behalf_of_the_organiser(db_session, people, zoom_on, monkeypatch):  # noqa: F811
    matt, sam, cm, cg = people
    start = NOW + timedelta(minutes=10)
    cs.sync_connection(db_session, cm, NOW, [ev("ms-1", start, link=ZOOM, me="organizer")])
    cs.sync_connection(db_session, cg, NOW, [ev("g-1", start, link=ZOOM)])
    m = meetings(db_session)[0]
    d = cs.should_record(db_session, m)
    assert not d.record and d.reason.startswith("Nobody from BMI in it has connected Zoom")

    db_session.add(ZoomConnection(id=uuid.uuid4(), user_id=sam.id, zoom_user_id="zu_sam"))
    db_session.flush()
    assert cs.should_record(db_session, m).record and cs.zoom_person(db_session, m).zoom_user_id == "zu_sam"
    db_session.add(ZoomConnection(id=uuid.uuid4(), user_id=matt.id, zoom_user_id="zu_matt"))
    db_session.flush()
    assert cs.zoom_person(db_session, m).zoom_user_id == "zu_matt"   # the organiser first

    sent = []
    monkeypatch.setattr(notetaker, "send_bot", lambda **kw: sent.append(kw) or {"id": "nt_1", "status": "scheduled", "platform": "zoom"})
    cs.plan(db_session, NOW + timedelta(minutes=7))
    assert sent and sent[0]["zoom_user_id"] == "zu_matt"

    db_session.query(ZoomConnection).filter_by(user_id=matt.id).one().status = "error"   # Matt removed the app in Zoom
    db_session.flush()
    assert cs.zoom_person(db_session, m).zoom_user_id == "zu_sam"


def test_zoom_view_for_the_meetings_page(db_session, zoom_on):
    sally = make_user(db_session, role="sales", name="Sally Parker")
    assert zoom.view(db_session, sally.id) == {"available": True, "connected": False, "status": None, "last_error": None, "connected_at": None}


def test_zoom_removed_in_zoom_shows_reconnect(client, db_session, monkeypatch):
    from app.models import Notification
    from tests.test_calls import _signed
    monkeypatch.setattr(settings, "notetaker_webhook_secret", "s3cret")
    sally = make_user(db_session, role="sales", name="Sally Parker")
    db_session.add(ZoomConnection(id=uuid.uuid4(), user_id=sally.id, zoom_user_id="zu_sally"))
    db_session.flush()
    raw, h = _signed({"id": "m1", "event": "zoom.disconnected", "data": {"zoom_user_id": "zu_sally", "reason": "removed"}}, "s3cret")
    assert client.post("/api/calls/webhook", content=raw, headers=h).status_code == 200
    conn = db_session.query(ZoomConnection).filter_by(user_id=sally.id).one()
    assert conn.status == "error" and "Reconnect" in conn.last_error
    assert db_session.query(Notification).filter_by(user_id=sally.id, title="Your Zoom was disconnected").count() == 1
