"""Packages still to be allocated, online booking forms, the issue-gone-to-press check and filler ads."""
import json
import uuid
from datetime import date, timedelta

from tests.conftest import identity_headers, make_user
from tests.test_orders import w  # noqa: F401 - fixture
from tests.test_sales_orders import _NoCloseSession

from app.automations import allocations, sor_checks
from app.models import BookingForm, Notification, ReviewQueueItem, SalesDeal, SalesOrder


def _package(w, ed, title_slug="selling-travel"):
    t = w["titles"][title_slug]
    return {
        "client_name": "Visit Malta", "rep_id": str(w["reps"]["SP"].id), "booked_on": date.today().isoformat(),
        "pricing": "package", "package_price_gbp": 4000,
        "lines": [{"description": "Full page", "title_id": str(t.id), "list_price": 2000,
                   "allocate_by": (date.today() + timedelta(days=5)).isoformat(),
                   "placements": [{"edition_id": str(ed.id)}, {"tba": True}, {"tba": True}, {"tba": True}]}],
    }


def test_items_to_be_allocated_are_priced_but_stay_off_the_register_until_given_an_issue(w, client, monkeypatch):
    db = w["db"]
    ed = w["ed"]("selling-travel", "Spring", date.today() + timedelta(days=40))
    body = _package(w, ed)
    r = client.post("/api/sales/deals", json=body, headers=w["h"])
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["totals"]["total_gbp"] == 4000 and d["totals"]["unallocated_count"] == 3 and d["totals"]["unallocated_gbp"] == 3000
    assert sum(1 for s in d["schedule"] if s.get("to_allocate")) == 3
    assert db.query(SalesOrder).filter_by(deal_id=uuid.UUID(d["id"])).count() == 1   # only the allocated one is on the register
    doc = client.get(f"/api/sales/deals/{d['id']}/document", headers=w["h"]).json()
    assert "3 insertions with dates to be confirmed" in doc["insertions"]
    listed = client.get("/api/sales/deals?to_allocate=true", headers=w["h"]).json()
    assert listed["unallocated_gbp"] == 3000 and listed["items"][0]["unallocated_count"] == 3

    # a line with items to allocate needs a title
    bad = json.loads(json.dumps(body))
    bad["lines"][0].pop("title_id")
    assert "Choose the title" in client.post("/api/sales/deals", json=bad, headers=w["h"]).json()["detail"]

    # the reminder comes up as the decide-by date gets close, for the salesperson
    sally = make_user(db, role="sales")
    w["reps"]["SP"].user_id = sally.id
    db.commit()
    monkeypatch.setattr(allocations, "SessionLocal", lambda: _NoCloseSession(db))
    allocations.scan()
    allocations.scan()
    item = db.query(ReviewQueueItem).filter_by(kind="allocation_due", status="pending").one()
    assert item.payload["owner_user_id"] == str(sally.id) and any(x.get("href") == f"/sales/deals/{d['id']}" for x in item.payload["details"])
    assert client.post(f"/api/review-queue/{item.id}/actions/done", json={}, headers=w["h"]).status_code == 400

    # allocating them puts them on the register and closes the reminder by itself
    later = [w["ed"]("selling-travel", n, date.today() + timedelta(days=k)) for n, k in (("Summer", 120), ("Autumn", 200), ("Winter", 280))]
    got = d["lines"][0]
    body["lines"][0]["key"] = got["key"]
    body["lines"][0]["placements"] = [{"edition_id": str(ed.id), "order_id": got["placements"][0]["order_id"]}] + [{"edition_id": str(e.id)} for e in later]
    r = client.put(f"/api/sales/deals/{d['id']}", json=body, headers=w["h"])
    assert r.status_code == 200, r.text
    assert r.json()["totals"]["unallocated_count"] == 0
    assert db.query(SalesOrder).filter_by(deal_id=uuid.UUID(d["id"])).count() == 4
    db.refresh(item)
    assert item.status == "approved" and item.resolved_action == "allocated"


def test_accounts_hear_about_every_new_booking(w, client):
    db = w["db"]
    sam = make_user(db, role="sales", name="Samantha Elmer")
    sam.can_approve_bookings = True
    db.commit()
    ed = w["ed"]("selling-travel", "Spring", date.today() + timedelta(days=40))
    client.post("/api/sales/deals", json=_package(w, ed), headers=w["h"])
    n = db.query(Notification).filter_by(user_id=sam.id, kind="booking_new").one()
    assert "Visit Malta" in n.title and "3 items still to be allocated" in n.body


def test_online_booking_form_entry_becomes_a_booking(w, client):
    db = w["db"]
    ed = w["ed"]("selling-travel", "Awards 2026", date.today() + timedelta(days=60), kind="event")
    r = client.post("/api/sales/booking-forms", json={"name": "Onboard Awards entries", "edition_id": str(ed.id),
                                                      "description": "Awards entry", "unit_price": 295}, headers=w["h"])
    assert r.status_code == 201, r.text
    form = r.json()
    assert form["address"].endswith(f"/api/booking-forms/{db.get(BookingForm, uuid.UUID(form['id'])).token}")
    token = db.get(BookingForm, uuid.UUID(form["id"])).token
    sally_h = identity_headers(make_user(db, role="sales"))
    assert client.get("/api/sales/booking-forms", headers=sally_h).status_code == 403

    raw = {"q3_companyName": "SkyHigh Airlines", "q4_fullName": {"first": "Ana", "last": "Lopes"}, "q5_email": "ana@skyhigh.example",
           "q6_numberOf": "2", "q7_category": "Best Lounge"}
    post = {"formID": "123", "submissionID": "5550001", "rawRequest": json.dumps(raw)}
    assert client.post(f"/api/sales/booking-forms/receive/{token}", data=post, headers=w["h"]).json()["queued"]
    assert not client.post(f"/api/sales/booking-forms/receive/{token}", data=post, headers=w["h"]).json()["queued"]   # sent twice
    assert client.post("/api/sales/booking-forms/receive/nope", data=post, headers=w["h"]).status_code == 404
    item = db.query(ReviewQueueItem).filter_by(kind="online_booking").one()
    assert item.payload["guess"] == {"company": "SkyHigh Airlines", "name": "Ana Lopes", "email": "ana@skyhigh.example", "quantity": "2",
                                     "category": "Best Lounge"}
    assert item.payload["facets"]["client"] == "New client"

    r = client.post(f"/api/review-queue/{item.id}/actions/create", json={}, headers=w["h"])
    assert r.status_code == 200, r.text
    db.refresh(item)
    deal = db.get(SalesDeal, uuid.UUID(item.payload["deal_id"]))
    assert deal.status == "pencilled" and deal.client_name == "SkyHigh Airlines" and float(deal.total_gbp) == 590
    assert db.query(SalesOrder).filter_by(deal_id=deal.id, edition_id=ed.id).count() == 2
    assert db.query(ReviewQueueItem).filter_by(kind="order_check", status="pending").count() == 1

    # plain JSON works too (Stova, or anything else)
    client.post(f"/api/sales/booking-forms/receive/{token}", json={"submission_id": "s-1", "answers": {"Company": "Jet2", "Email": "x@jet2.example"}},
                headers=w["h"])
    assert db.query(ReviewQueueItem).filter_by(kind="online_booking", status="pending").count() == 1


def test_issue_gone_to_press_check_lists_what_needs_a_look(w, client, monkeypatch):
    db = w["db"]
    ed = w["ed"]("selling-travel", "Spring", date.today() - timedelta(days=3))
    ed.copy_deadline = date.today() - timedelta(days=10)
    d = client.post("/api/sales/deals", json=_package(w, ed), headers=w["h"]).json()
    client.post(f"/api/sales/deals/{d['id']}/status", json={"status": "confirmed"}, headers=w["h"])
    typed = SalesOrder(id=uuid.uuid4(), edition_id=ed.id, client_name="Direct Ltd", value_gbp=500, status="booked", extra={})
    filler = SalesOrder(id=uuid.uuid4(), edition_id=ed.id, client_name="House ad", value_gbp=0, status="booked", extra={}, filler=True,
                        pages=1, source_file="sheet.xlsx")
    db.add_all([typed, filler])
    db.commit()
    monkeypatch.setattr(sor_checks, "SessionLocal", lambda: _NoCloseSession(db))
    sor_checks.scan()
    sor_checks.scan()
    item = db.query(ReviewQueueItem).filter_by(kind="sor_issue_check").one()
    labels = [x["label"] for x in item.payload["details"]]
    assert "No booking behind it" in labels and "Confirmation not sent" in labels and "Package still to allocate" in labels
    assert any(x["label"] == "Filler ads" and x["value"].startswith("1 ") for x in item.payload["details"])
    assert all(x.get("href") for x in item.payload["details"])   # every record on the card opens
    assert item.payload["facets"]["state"] == "Needs a look"

    # filler ads can be marked and filtered on the register
    r = client.patch(f"/api/sales/orders/{typed.id}", json={"filler": True}, headers=w["h"])
    assert r.status_code == 200 and r.json()["filler"]
    assert client.get(f"/api/sales/orders?edition_id={ed.id}&filler=true", headers=w["h"]).json()["total"] == 2
