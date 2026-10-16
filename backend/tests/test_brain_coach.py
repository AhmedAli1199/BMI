"""The Brain as a coach (app/brain/coach.py): one tip for the page you're on, hidden once dismissed, nothing at all
when tips are switched off, and the welcome tour remembered per person."""
import uuid
from datetime import date, datetime, timedelta, timezone

from tests.conftest import identity_headers, make_user
from tests.test_orders import _wisconsin, w  # noqa: F401 - fixture

from app.brain import coach
from app.core.identity import Identity
from app.models import SalesDeal


def _me(user):
    return Identity(user_id=str(user.id), role=user.role, access=[("onboard", None), ("sellingtravel", None)])


def test_unsent_confirmation_tip_until_dismissed(w, client):  # noqa: F811
    db = w["db"]
    sally = make_user(db, role="sales", name="Sally Parker")
    w["reps"]["SP"].user_id = sally.id
    db.flush()
    r = client.post("/api/sales/deals", json={**_wisconsin(w), "status": "confirmed"}, headers=w["h"])
    assert r.status_code == 201, r.text
    deal = db.get(SalesDeal, uuid.UUID(r.json()["id"]))
    deal.confirmed_at, deal.sent_at = datetime.now(timezone.utc) - timedelta(days=4), None
    db.flush()

    page = f"/sales/deals/{deal.id}"
    tip = coach.state(db, _me(sally), sally, page)["tip"]
    assert tip["id"] == f"unsent:{deal.id}" and tip["show"] == "Email the confirmation" and "4 days ago" in tip["text"]
    assert coach.state(db, _me(sally), sally, "/")["tip"]["id"].startswith("unsent-list:")
    # someone else's booking: no tip
    other = make_user(db, role="sales", name="Kirsty")
    assert coach.state(db, _me(other), other, page)["tip"] is None
    # "Got it" hides it for good
    coach.dismiss(db, sally, tip["id"], forever=True)
    assert coach.state(db, _me(sally), sally, page)["tip"] is None
    # and once it's sent there's nothing to say anyway
    deal.sent_at = datetime.now(timezone.utc)
    db.flush()
    assert coach.state(db, _me(sally), sally, "/")["tip"] is None or not coach.state(db, _me(sally), sally, "/")["tip"]["id"].startswith("unsent")


def test_deadline_tip_and_the_off_switch(w, client):  # noqa: F811
    db = w["db"]
    e = w["ed"]("obh", "108", date.today() + timedelta(days=20))
    e.ad_deadline, e.status = date.today() + timedelta(days=3), "open"
    admin = make_user(db, role="admin", name="Ahmed")
    db.flush()
    s = coach.state(db, Identity(user_id=str(admin.id), role="admin"), admin, "/sales/editions")
    assert s["tips"] and s["tip"]["id"] == f"deadline:{e.id}" and "in 3 days" in s["tip"]["text"] and s["tip"]["link"].endswith(str(e.id))
    r = client.patch(f"/api/users/{admin.id}/preferences", json={"values": {"brain_tips": "off", "brain_celebrations": "off"}}, headers=identity_headers(admin))
    assert r.status_code == 200, r.text
    db.refresh(admin)
    s = coach.state(db, Identity(user_id=str(admin.id), role="admin"), admin, "/sales/editions")
    assert s == {**s, "tips": False, "celebrations": False, "tip": None}


def test_tour_is_remembered_and_can_be_replayed(w, client):  # noqa: F811
    db = w["db"]
    sally = make_user(db, role="sales", name="Sally Parker")
    db.flush()
    h = identity_headers(sally)
    assert client.get("/api/brain/coach?path=/", headers=h).json()["tours_done"] == []
    assert client.post("/api/brain/coach/tour", json={"tour": "welcome-sales"}, headers=h).status_code == 200
    assert client.get("/api/brain/coach?path=/", headers=h).json()["tours_done"] == ["welcome-sales"]
    client.post("/api/brain/coach/tour", json={"tour": "welcome-sales", "done": False}, headers=h)
    assert client.get("/api/brain/coach?path=/", headers=h).json()["tours_done"] == []
    # the two switches come from the preference registry, so the Settings page shows them by itself
    from app.preferences import PREFERENCE_DEFS
    assert {"brain_tips", "brain_celebrations"} <= {p.key for p in PREFERENCE_DEFS}
