"""Hand-offs to editorial and production once accounts have checked a booking (15 Oct call)."""
import uuid
from datetime import date, timedelta

from tests.conftest import identity_headers, make_user
from tests.test_orders import w  # noqa: F401 - fixture

from app.models import ReviewQueueItem, SalesDeal
from app.sales import handoffs as ho
from app.services import notify


def test_who_each_item_goes_to(w):
    st, usa = w["titles"]["selling-travel"], w["titles"]["visit-usa-planner"]
    assert ho.suggest_team(st, {"description": "Sponsored feature"}) == "editorial"
    assert ho.suggest_team(st, {"description": "Social media campaign"}) == "editorial"
    assert ho.suggest_team(st, {"description": "Full page advert"}) == "production"
    assert ho.suggest_team(st, {"description": "Solus html email"}) == "production"
    assert ho.suggest_team(usa, {"description": "Sponsored feature"}) == "production"      # fillable forms: production
    assert ho.suggest_team(st, {"description": "Sponsored content with banner"}) == "both"


def test_handoffs_go_after_the_accounts_check(w, client, monkeypatch):
    db = w["db"]
    sent = []
    monkeypatch.setattr(notify, "automation_mailbox_ready", lambda db: True)
    monkeypatch.setattr(notify, "send_automation_email", lambda db, to, subject, body, attachments=None: sent.append((to, subject, body)))
    h = w["h"]
    st_id = str(w["titles"]["selling-travel"].id)
    cur = client.get("/api/sales/deals/settings", headers=h).json()
    client.put("/api/sales/deals/settings", json={**cur, "production_emails": "production@bmi.example",
                                                   "handoff_routes": {"titles": {st_id: {"editorial": "editor-st@bmi.example"}}}}, headers=h)
    ed = w["ed"]("selling-travel", "Dec issue", date.today() + timedelta(days=40))
    body = {"client_name": "Visit Malta", "contact_name": "Ana", "contact_email": "ana@malta.example", "copy_contact_name": "Ben at Creative Co",
            "copy_contact_email": "ben@creative.example", "rep_id": str(w["reps"]["SP"].id), "status": "confirmed",
            "lines": [
                {"key": "spons", "title_id": st_id, "description": "Sponsored feature", "unit_price": 3000, "placements": [{"edition_id": str(ed.id)}],
                 "handoff": {"team": "auto", "format": "How to sell"},
                 "activities": [{"kind": "online", "on": (date.today() + timedelta(days=50)).isoformat()},
                                {"kind": "newsletter", "on": (date.today() + timedelta(days=55)).isoformat(), "note": "Selling Travel Weekly"}]},
                {"key": "page", "title_id": st_id, "description": "Full page advert", "unit_price": 2000, "placements": [{"edition_id": str(ed.id)}]},
                {"key": "spons2", "title_id": st_id, "description": "Sponsored Q&A", "unit_price": 1500, "placements": [{"edition_id": str(ed.id)}],
                 "handoff": {"team": "auto", "format": "TBC"}},
            ]}
    d = client.post("/api/sales/deals", json=body, headers=h).json()
    states = {x["line"]: {t["team"]: t["state"] for t in x["teams"]} for x in d["handoffs"]}
    assert states == {"spons": {"editorial": "waiting_check"}, "page": {"production": "waiting_check"}, "spons2": {"editorial": "waiting_format"}}
    assert not sent
    item = db.query(ReviewQueueItem).filter_by(kind="order_check", status="pending").one()
    db.commit()
    assert client.post(f"/api/review-queue/{item.id}/actions/approve", json={}, headers=h).status_code == 200
    assert sorted(s[0][0] for s in sent) == ["editor-st@bmi.example", "production@bmi.example"]
    ed_mail = next(s for s in sent if s[0] == ["editor-st@bmi.example"])
    assert "Sponsored feature" in ed_mail[2] and "How to sell" in ed_mail[2] and "Selling Travel Weekly" in ed_mail[2]
    assert "Ben at Creative Co" in ed_mail[2] and "Hi Ben," in ed_mail[2] and "Sponsored Q&amp;A" not in ed_mail[2]   # TBC waits
    prod_mail = next(s for s in sent if s[0] == ["production@bmi.example"])
    assert "Full page advert" in prod_mail[2] and "artwork" in prod_mail[2]
    db.expire_all()
    got = client.get(f"/api/sales/deals/{d['id']}", headers=h).json()
    states = {x["line"]: {t["team"]: t["state"] for t in x["teams"]} for x in got["handoffs"]}
    assert states["spons"]["editorial"] == "sent" and states["spons2"]["editorial"] == "waiting_format"
    # the format arrives later: only that item goes
    body["lines"][2]["handoff"]["format"] = "Expert interview"
    n = len(sent)
    assert client.put(f"/api/sales/deals/{d['id']}", json=body, headers=h).status_code == 200
    assert len(sent) == n + 1 and "Expert interview" in sent[-1][2] and "Sponsored feature" not in sent[-1][2]
    # Send again for one line
    r = client.post(f"/api/sales/deals/{d['id']}/handoffs/send", json={"lines": ["page"]}, headers=h)
    assert r.status_code == 200 and len(sent) == n + 2 and sent[-1][0] == ["production@bmi.example"]


def test_no_address_and_no_mailbox(w, client, monkeypatch):
    monkeypatch.setattr(notify, "automation_mailbox_ready", lambda db: False)
    h = w["h"]
    ed = w["ed"]("selling-travel", "Nov issue", date.today() + timedelta(days=20))
    body = {"client_name": "Visit Malta", "rep_id": str(w["reps"]["SP"].id), "status": "confirmed",
            "lines": [{"key": "a", "description": "Sponsored feature", "unit_price": 3000, "placements": [{"edition_id": str(ed.id)}],
                       "handoff": {"format": "Profile"}},
                      {"key": "b", "description": "Full page", "unit_price": 1000, "placements": [{"edition_id": str(ed.id)}],
                       "handoff": {"team": "production", "production_to": "steve@bmi.example"}}]}
    d = client.post("/api/sales/deals", json=body, headers=h).json()
    item = w["db"].query(ReviewQueueItem).filter_by(kind="order_check", status="pending").one()
    w["db"].commit()
    client.post(f"/api/review-queue/{item.id}/actions/approve", json={}, headers=h)
    w["db"].expire_all()
    got = client.get(f"/api/sales/deals/{d['id']}", headers=h).json()
    states = {x["line"]: x["teams"][0] for x in got["handoffs"]}
    assert states["a"]["state"] == "no_address"                                  # routing table blank: nobody to send to
    assert states["b"]["state"] == "failed" and "automation mailbox" in states["b"]["error"]


def test_format_can_be_added_on_a_locked_booking(w, client, monkeypatch):
    sent = []
    monkeypatch.setattr(notify, "automation_mailbox_ready", lambda db: True)
    monkeypatch.setattr(notify, "send_automation_email", lambda db, to, subject, body, attachments=None: sent.append((to, body)))
    db = w["db"]
    sam = make_user(db, role="sales", name="Samantha Elmer")
    sam.can_approve_bookings = True
    sally = make_user(db, role="sales", name="Sally Parker")
    w["reps"]["SP"].user_id = sally.id
    db.commit()
    src = w["titles"]["selling-travel"].crm_source_db
    sam_h, sally_h = identity_headers(sam, access=[(src, None)]), identity_headers(sally, access=[(src, None)])
    ed = w["ed"]("selling-travel", "Jan issue", date.today() + timedelta(days=60))
    body = {"client_name": "Visit Malta", "rep_id": str(w["reps"]["SP"].id), "status": "confirmed",
            "lines": [{"key": "a", "description": "Sponsored feature", "unit_price": 3000, "placements": [{"edition_id": str(ed.id)}],
                       "handoff": {"team": "editorial", "editorial_to": "ed@bmi.example", "format": "TBC"}}]}
    d = client.post("/api/sales/deals", json=body, headers=sally_h).json()
    item = db.query(ReviewQueueItem).filter_by(kind="order_check", status="pending").one()
    db.commit()
    client.post(f"/api/review-queue/{item.id}/actions/approve", json={}, headers=sam_h)
    assert not sent
    assert client.put(f"/api/sales/deals/{d['id']}", json=body, headers=sally_h).status_code == 409   # locked
    r = client.put(f"/api/sales/deals/{d['id']}/lines/a/handoff", json={"handoff": {"team": "editorial", "editorial_to": "ed@bmi.example",
                                                                                     "format": "How to sell"}}, headers=sally_h)
    assert r.status_code == 200 and len(sent) == 1 and "How to sell" in sent[0][1]
