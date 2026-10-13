import json

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from notetaker import engine as eng
from notetaker.db import init_db
from notetaker.styles import instructions

MEET = "https://meet.google.com/abc-defg-hij"


def test_console_needs_sign_in_and_cookie_works(api):
    assert api.get("/admin/overview").status_code == 401
    assert api.post("/console/login", json={"password": "wrong"}).status_code == 401
    assert api.post("/console/login", json={"password": "admin-t"}).status_code == 200
    o = api.get("/admin/overview").json()          # the cookie now signs us in
    assert {c["name"] for c in o["checks"]} >= {"Meeting bot", "Every app has its own Gemini key", "Public address", "Background worker"}
    assert any(s["value"] == "sales" for s in o["styles"])
    api.post("/console/logout")
    api.cookies.clear()
    assert api.get("/admin/overview").status_code == 401


def test_app_lifecycle(api):
    api.post("/console/login", json={"password": "admin-t"})
    r = api.post("/admin/apps", json={"name": "Hiring tool", "webhook_url": "https://hire.example.com/hook", "notes_style": "interview"})
    assert r.status_code == 201, r.text
    created = r.json()
    key = created["api_key"]
    assert key.startswith("nt_") and "NOTETAKER_API_KEY=" + key in created["env"] and created["app"]["key_hint"] == key[:7]
    app_id = created["app"]["id"]
    h = {"Authorization": f"Bearer {key}"}
    assert api.get("/v1/meetings", headers=h).status_code == 200

    new = api.post(f"/admin/apps/{app_id}/rotate-key").json()["api_key"]
    assert api.get("/v1/meetings", headers=h).status_code == 401          # the old key stopped working
    h = {"Authorization": f"Bearer {new}"}
    assert api.get("/v1/meetings", headers=h).status_code == 200

    app = api.get("/admin/apps").json()[0]
    api.patch(f"/admin/apps/{app_id}", json={**app, "is_active": False})
    assert api.get("/v1/meetings", headers=h).status_code == 403          # switched off

    assert api.post(f"/admin/apps/{app_id}/test-webhook").status_code == 200
    d = api.get(f"/admin/apps/{app_id}/deliveries").json()
    assert d[0]["event"] == "test.ping"
    assert api.post(f"/admin/deliveries/{d[0]['id']}/resend").status_code == 200
    assert api.delete(f"/admin/apps/{app_id}").status_code == 204
    assert api.get("/admin/apps").json() == []


def test_try_a_call_from_the_console(api):
    api.post("/console/login", json={"password": "admin-t"})
    app_id = api.post("/admin/apps", json={"name": "BMI"}).json()["app"]["id"]
    m = api.post("/admin/meetings", json={"app_id": app_id, "meeting_url": MEET, "title": "Test"}).json()
    assert m["status"] == "scheduled"
    detail = api.get(f"/admin/meetings/{m['id']}").json()
    assert detail["app"] == "BMI" and detail["timeline"][0]["label"] == "Scheduled"
    assert api.delete(f"/admin/meetings/{m['id']}").status_code == 200
    assert api.get(f"/admin/meetings/{m['id']}").json()["status"] == "cancelled"


def test_notes_styles():
    assert "candidate" in instructions("interview", None)
    assert instructions("sales", "Mention the issue.").endswith("Mention the issue.")
    assert instructions("nonsense", None) == instructions("general", None)


def test_credentials_come_from_the_bootstrap_file(tmp_path, monkeypatch):
    from notetaker.config import settings
    f = tmp_path / "attendee.json"
    f.write_text(json.dumps({"api_key": "k1", "webhook_secret": "s1", "admin_email": "a@x", "admin_password": "p"}))
    from dataclasses import replace
    monkeypatch.setattr(eng, "settings", replace(settings, attendee_credentials_file=str(f), attendee_api_key="", attendee_webhook_secret=""))
    assert eng.api_key() == "k1" and eng.webhook_secret() == "s1" and eng.admin_login()["password"] == "p"


def test_existing_install_gets_new_columns():
    e = create_engine("sqlite://", poolclass=StaticPool)
    with e.begin() as c:
        c.execute(text("CREATE TABLE clients (id VARCHAR(32) PRIMARY KEY, name VARCHAR(200), api_key_hash VARCHAR(64), webhook_url TEXT,"
                       " webhook_secret VARCHAR(128), bot_name VARCHAR(100), chat_message TEXT, summary_instructions TEXT,"
                       " retention_days INTEGER, created_at TIMESTAMP)"))
    init_db(e)
    init_db(e)   # safe twice
    from sqlalchemy import inspect
    assert {"notes_style", "key_hint", "is_active", "last_used_at"} <= {c["name"] for c in inspect(e).get_columns("clients")}
