from datetime import datetime, timedelta, timezone

from notetaker.db import session_scope
from notetaker.models import Meeting

MEET = "https://meet.google.com/abc-defg-hij"
ADMIN = {"X-Admin-Token": "admin-t"}


def mk_app(api, name, **extra):
    r = api.post("/admin/apps", json={"name": name, **extra}, headers=ADMIN)
    assert r.status_code == 201, r.text
    return r.json()


def book(api, app, start, minutes=60):
    return api.post("/v1/meetings", headers={"Authorization": f"Bearer {app['api_key']}"},
                    json={"meeting_url": MEET, "join_at": start.isoformat(), "end_at": (start + timedelta(minutes=minutes)).isoformat()})


def test_bookings_are_checked_in_advance(api):
    a, b = mk_app(api, "BMI", gemini_api_key="k1"), mk_app(api, "Hiring", gemini_api_key="k2")
    two = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=1)
    assert book(api, a, two).status_code == 201
    assert book(api, b, two).status_code == 201
    r = book(api, a, two + timedelta(minutes=30))
    assert r.status_code == 422 and "already booked for 2 calls at" in r.json()["detail"]
    # back to back is fine: the 2pm calls end at 3pm
    assert book(api, a, two + timedelta(hours=1)).status_code == 201
    cap = api.get("/v1/capacity", headers={"Authorization": f"Bearer {b['api_key']}"},
                  params={"start": two.isoformat(), "end": (two + timedelta(minutes=30)).isoformat()}).json()
    assert cap["free"] == 0 and cap["overall_limit"] == 2


def test_each_app_has_its_own_limit(api):
    a = mk_app(api, "Busy app", max_concurrent=1, gemini_api_key="k1")
    t = datetime.now(timezone.utc) + timedelta(days=2)
    assert book(api, a, t).status_code == 201
    r = book(api, a, t + timedelta(minutes=10))
    assert r.status_code == 422 and "its limit" in r.json()["detail"]
    other = mk_app(api, "Quiet app", gemini_api_key="k2")
    assert book(api, other, t + timedelta(minutes=10)).status_code == 201   # the other app still gets the second bot


def test_no_key_means_transcript_only(api):
    from notetaker.worker import tick
    app = mk_app(api, "No key yet")
    m = api.post("/v1/meetings", headers={"Authorization": f"Bearer {app['api_key']}"}, json={"meeting_url": MEET}).json()
    with session_scope() as db:
        bot_id = db.get(Meeting, m["id"]).bot_id
    api.post("/hooks/fake", json={"bot_id": bot_id, "status": "recording"})
    api.post("/hooks/fake", json={"bot_id": bot_id, "status": "processing"})
    tick()
    got = api.get(f"/v1/meetings/{m['id']}", headers={"Authorization": f"Bearer {app['api_key']}"}).json()
    assert got["status"] == "completed" and got["notes"] is None and got["transcript"]
    assert "Gemini key" in got["status_detail"]


def test_keys_are_checked_stored_encrypted_and_tracked(api):
    from notetaker.worker import tick
    assert api.post("/admin/apps", json={"name": "Bad", "gemini_api_key": "bad-key"}, headers=ADMIN).status_code == 422
    app = mk_app(api, "Good", gemini_api_key="good-key-1234")
    assert app["app"]["gemini_key_hint"] == "…1234"
    with session_scope() as db:
        from notetaker.models import Client
        c = db.get(Client, app["app"]["id"])
        assert "good-key-1234" not in (c.gemini_key_enc or "")
    m = api.post("/v1/meetings", headers={"Authorization": f"Bearer {app['api_key']}"}, json={"meeting_url": MEET}).json()
    with session_scope() as db:
        bot_id = db.get(Meeting, m["id"]).bot_id
    api.post("/hooks/fake", json={"bot_id": bot_id, "status": "processing"})
    tick()
    apps = {x["name"]: x for x in api.get("/admin/apps", headers=ADMIN).json()}
    assert apps["Good"]["usage_month"]["calls"] == 1 and apps["Good"]["usage_month"]["ai_input_tokens"] == 1200
    # removing the key
    apps["Good"]["gemini_api_key"] = ""
    r = api.patch(f"/admin/apps/{app['app']['id']}", json=apps["Good"], headers=ADMIN).json()
    assert r["has_gemini_key"] is False
