"""Feedback from testers: send it with what was pointed at and screenshots, the shared board, me too,
comments, status (with notifications), the download, and the GitHub issue."""
import base64
import io
import json
import zipfile

import httpx

from app.core.config import settings
from app.feedback import github
from app.models import Feedback, FeedbackImage, Notification
from tests.conftest import identity_headers, make_user

PNG = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 100).decode()


def _send(client, h, **kw):
    body = {"kind": "broken", "message": "The Save button on the booking does nothing", "page_path": "/sales/deals/new",
            "page_title": "New booking", "elements": [{"label": "Button: Save", "selector": "main button:nth-of-type(2)",
                                                       "source": ["components/deals/deal-form.tsx:389"], "heading": "Confirmation"}],
            "context": {"browser": "Chrome 140", "errors": [{"at": "10:01", "kind": "error", "message": "Couldn't save"}]},
            "images": [{"data": PNG, "label": "Area screenshot", "width": 10, "height": 10}], **kw}
    return client.post("/api/feedback", json=body, headers=h)


def test_send_and_see_it_on_the_board(client, db_session):
    admin = make_user(db_session, role="admin", name="Ahmed")
    sally = make_user(db_session, role="sales", name="Sally Parker")
    tom = make_user(db_session, role="sales", name="Tom")
    db_session.flush()
    sh, th, ah = identity_headers(sally), identity_headers(tom), identity_headers(admin)

    assert client.post("/api/feedback", json={"kind": "broken", "page_path": "/x"}, headers=sh).status_code == 422   # nothing said
    r = _send(client, sh)
    assert r.status_code == 200, r.text
    f = r.json()
    assert f["number"] >= 1 and f["mine"] and len(f["images"]) == 1 and f["elements"][0]["source"] == ["components/deals/deal-form.tsx:389"]
    assert f["context"]["errors"][0]["message"] == "Couldn't save"           # the sender sees what was recorded
    assert db_session.query(Notification).filter_by(user_id=admin.id, kind="feedback").count() == 1

    board = client.get("/api/feedback", headers=th).json()
    assert board["total"] == 1 and board["items"][0]["user_name"] == "Sally Parker" and board["counts"]["new"] == 1
    assert client.get(f"/api/feedback/{f['id']}", headers=th).json()["context"] == {}   # others don't see browser details
    img = client.get(f"/api/feedback/images/{f['images'][0]['id']}", headers=th)
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"

    # someone else about to report the same thing is shown it first
    sim = client.get("/api/feedback/similar", params={"path": "/sales/deals/new", "q": "save button broken"}, headers=th).json()
    assert [s["id"] for s in sim] == [f["id"]]
    assert client.get("/api/feedback/similar", params={"path": "/contacts", "q": "export spreadsheet"}, headers=th).json() == []
    pins = client.get("/api/feedback/pins", params={"path": "/sales/deals/new"}, headers=th).json()
    assert pins[0]["elements"][0]["selector"] == "main button:nth-of-type(2)"

    assert client.post(f"/api/feedback/{f['id']}/me-too", headers=sh).status_code == 422   # not your own
    assert client.post(f"/api/feedback/{f['id']}/me-too", headers=th).json()["me_too"] == ["Tom"]
    assert client.get("/api/feedback", params={"sort": "votes"}, headers=th).json()["items"][0]["me_too_mine"] is True
    c = client.post(f"/api/feedback/{f['id']}/comments", json={"text": "Same on the edit page"}, headers=th).json()
    assert c["comments"][0]["name"] == "Tom"
    assert db_session.query(Notification).filter_by(user_id=sally.id, kind="feedback").count() == 1   # told about the comment

    # only managers move it along; the sender and everyone who said "me too" hear about it
    assert client.put(f"/api/feedback/{f['id']}/status", json={"status": "fixed"}, headers=th).status_code == 403
    done = client.put(f"/api/feedback/{f['id']}/status", json={"status": "fixed", "note": "Fixed in today's update"}, headers=ah).json()
    assert done["status_label"] == "Fixed" and done["status_by"] == "Ahmed"
    assert db_session.query(Notification).filter_by(user_id=tom.id, kind="feedback").count() == 1
    assert db_session.query(Notification).filter_by(user_id=sally.id, kind="feedback").count() == 2
    assert client.get("/api/feedback", params={"status": "open"}, headers=th).json()["total"] == 0
    assert client.delete(f"/api/feedback/{f['id']}", headers=sh).status_code == 403   # no longer new


def test_pins_say_which_are_yours_so_there_is_no_me_too_on_them(client, db_session):
    sally = make_user(db_session, role="sales", name="Sally Parker")
    tom = make_user(db_session, role="sales", name="Tom")
    db_session.flush()
    sh, th = identity_headers(sally), identity_headers(tom)
    f = _send(client, sh).json()
    mine = client.get("/api/feedback/pins", params={"path": "/sales/deals/new"}, headers=sh).json()[0]
    assert mine["mine"] is True and mine["me_too_mine"] is False
    theirs = client.get("/api/feedback/pins", params={"path": "/sales/deals/new"}, headers=th).json()[0]
    assert theirs["mine"] is False
    client.post(f"/api/feedback/{f['id']}/me-too", headers=th)
    assert client.get("/api/feedback/pins", params={"path": "/sales/deals/new"}, headers=th).json()[0]["me_too_mine"] is True


def test_count_tiles_follow_the_filters_except_status(client, db_session):
    admin = make_user(db_session, role="admin", name="Ahmed")
    sally = make_user(db_session, role="sales", name="Sally Parker")
    tom = make_user(db_session, role="sales", name="Tom")
    db_session.flush()
    sh, th, ah = identity_headers(sally), identity_headers(tom), identity_headers(admin)
    a = _send(client, sh).json()
    _send(client, sh, kind="idea", message="An idea", images=[], elements=[])
    _send(client, th, message="Tom's problem", images=[], elements=[])
    client.put(f"/api/feedback/{a['id']}/status", json={"status": "wont_do"}, headers=ah)

    everything = client.get("/api/feedback", params={"status": "new"}, headers=sh).json()["counts"]
    assert everything == {"new": 2, "looking": 0, "fixed": 0, "wont_do": 1}       # the status tab doesn't narrow the tiles
    only_mine = client.get("/api/feedback", params={"mine": True}, headers=sh).json()["counts"]
    assert only_mine["new"] == 1 and only_mine["wont_do"] == 1
    ideas = client.get("/api/feedback", params={"kind": "idea"}, headers=sh).json()["counts"]
    assert ideas == {"new": 1, "looking": 0, "fixed": 0, "wont_do": 0}


def test_feedback_notifications_are_emailed_unless_turned_off(client, db_session):
    admin = make_user(db_session, role="admin", name="Ahmed")
    quiet = make_user(db_session, role="admin", name="Quiet Admin")
    quiet.preferences = {"email_notifications": "off"}
    sally = make_user(db_session, role="sales", name="Sally Parker")
    db_session.flush()
    _send(client, identity_headers(sally))
    n = db_session.query(Notification).filter_by(user_id=admin.id, kind="feedback").one()
    assert n.email_status == "pending"                                   # goes out by email as well as the bell
    from app.services.notify import send_pending_emails

    send_pending_emails(db_session)
    q = db_session.query(Notification).filter_by(user_id=quiet.id, kind="feedback").one()
    assert q.email_status == "skipped"                                   # their "Email me notifications" is off


def test_data_managers_are_named_in_the_feedback_permission_messages(client, db_session):
    sally = make_user(db_session, role="sales", name="Sally Parker")
    tom = make_user(db_session, role="sales", name="Tom")
    admin = make_user(db_session, role="admin", name="Ahmed")
    db_session.flush()
    f = _send(client, identity_headers(sally)).json()
    client.put(f"/api/feedback/{f['id']}/status", json={"status": "looking"}, headers=identity_headers(admin))
    r = client.delete(f"/api/feedback/{f['id']}", headers=identity_headers(sally))
    assert r.status_code == 403 and "data managers" in r.json()["detail"]
    r = client.post(f"/api/feedback/{f['id']}/github", headers=identity_headers(tom))
    assert r.status_code == 403 and "data managers" in r.json()["detail"]


def test_download_feedback(client, db_session):
    sally = make_user(db_session, role="sales", name="Sally Parker")
    db_session.flush()
    h = identity_headers(sally)
    _send(client, h)
    _send(client, h, kind="idea", message="Could it remember my last magazine?", images=[], elements=[])
    r = client.get("/api/feedback/export", params={"status": "open"}, headers=h)
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = z.namelist()
    assert "feedback.md" in names and "feedback.json" in names and any(n.startswith("images/") for n in names)
    md = z.read("feedback.md").decode()
    assert "The Save button on the booking does nothing" in md and "deal-form.tsx:389" in md and "remember my last magazine" in md
    data = json.loads(z.read("feedback.json"))
    assert len(data) == 2 and data[0]["context"]["browser"] == "Chrome 140"
    assert len(zipfile.ZipFile(io.BytesIO(client.get("/api/feedback/export", params={"kind": "idea"}, headers=h).content))
               .read("feedback.json")) > 2


def test_github_issue_with_screenshots(client, db_session, monkeypatch):
    sally = make_user(db_session, role="sales", name="Sally Parker")
    db_session.flush()
    f = _send(client, identity_headers(sally)).json()
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append((req.method, req.url.path, json.loads(req.content) if req.content else None))
        p = req.url.path
        if req.method == "GET" and p.endswith("/branches/feedback-screenshots"):
            return httpx.Response(404, json={})
        if req.method == "GET" and p == "/repos/bmi/brain":
            return httpx.Response(200, json={"default_branch": "main"})
        if req.method == "GET" and p.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "abc"}})
        if req.method == "POST" and p.endswith("/git/refs"):
            return httpx.Response(201, json={})
        if req.method == "PUT" and "/contents/" in p:
            return httpx.Response(201, json={})
        if req.method == "POST" and p.endswith("/issues"):
            return httpx.Response(201, json={"number": 7, "html_url": "https://github.com/bmi/brain/issues/7"})
        if req.method == "PATCH":
            return httpx.Response(200, json={})
        return httpx.Response(500, json={})

    monkeypatch.setattr(settings, "github_feedback_repo", "bmi/brain")
    monkeypatch.setattr(settings, "github_feedback_token", "t")
    monkeypatch.setattr(github, "_client", lambda: httpx.Client(base_url=github.API, transport=httpx.MockTransport(handler)))
    row = db_session.get(Feedback, __import__("uuid").UUID(f["id"]))
    github.sync(db_session, row)
    assert row.github_number == 7 and row.github_error is None
    issue = next(c for c in calls if c[0] == "POST" and c[1].endswith("/issues"))[2]
    assert "Save button" in issue["title"] and "deal-form.tsx:389" in issue["body"]
    assert "blob/feedback-screenshots/feedback/" in issue["body"] and issue["labels"] == ["feedback", "bug"]
    assert db_session.query(FeedbackImage).filter_by(feedback_id=row.id).one().github_url
    row.status = "fixed"
    github.sync(db_session, row)
    patch = next(c for c in calls if c[0] == "PATCH")[2]
    assert patch["state"] == "closed" and patch["state_reason"] == "completed"
    assert sum(1 for c in calls if c[0] == "PUT") == 1   # the screenshot isn't uploaded twice


def test_new_feedback_goes_to_discord_with_its_screenshot(client, db_session, monkeypatch):
    from app.feedback import discord
    sent = []

    def handler(req: httpx.Request) -> httpx.Response:
        sent.append(req)
        return httpx.Response(204)

    monkeypatch.setattr(settings, "discord_feedback_webhook_url", "https://discord.com/api/webhooks/1/abc")
    monkeypatch.setattr(discord, "_client", lambda: httpx.Client(transport=httpx.MockTransport(handler)))
    sally = make_user(db_session, role="sales", name="Sally Parker")
    db_session.flush()
    f = _send(client, identity_headers(sally), message="Hey @everyone the Save button does nothing").json()
    row = db_session.get(Feedback, __import__("uuid").UUID(f["id"]))
    assert discord.post(db_session, row)
    req = sent[-1]
    assert str(req.url) == "https://discord.com/api/webhooks/1/abc"
    body = req.content.decode("latin-1")
    assert 'name="files[0]"; filename="screenshot.png"' in body          # the screenshot goes with it
    payload = json.loads(body.split('name="payload_json"')[1].split("\r\n\r\n", 1)[1].split("\r\n--", 1)[0])
    embed = payload["embeds"][0]
    assert payload["allowed_mentions"] == {"parse": []}                    # no pings, whatever they wrote
    assert embed["title"].startswith(f"#{row.number} ") and "Save button" in embed["description"]
    assert embed["url"].endswith(f"/feedback?open={row.id}") and embed["image"]["url"] == "attachment://screenshot.png"
    assert any(fl["name"] == "From" and "Sally Parker (Sales)" in fl["value"] for fl in embed["fields"])


def test_discord_being_down_never_stops_feedback(client, db_session, monkeypatch):
    from app.feedback import discord

    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    sally = make_user(db_session, role="sales", name="Sally Parker")
    db_session.flush()
    monkeypatch.setattr(settings, "discord_feedback_webhook_url", "")
    assert not discord.enabled()                                           # off unless the address is set
    monkeypatch.setattr(settings, "discord_feedback_webhook_url", "https://example.com/not-discord")
    assert not discord.enabled()                                           # only a real Discord webhook address counts
    monkeypatch.setattr(settings, "discord_feedback_webhook_url", "https://discord.com/api/webhooks/1/abc")
    monkeypatch.setattr(discord, "_client", lambda: httpx.Client(transport=httpx.MockTransport(handler)))
    r = _send(client, identity_headers(sally))
    assert r.status_code == 200
    row = db_session.get(Feedback, __import__("uuid").UUID(r.json()["id"]))
    assert discord.post(db_session, row) is False
