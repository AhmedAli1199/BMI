"""Accounts (Samantha) is the only one who checks bookings and approves changes to checked ones; confirmations
copy production and accounts."""
from tests.conftest import identity_headers, make_user
from tests.test_orders import _wisconsin, w  # noqa: F401 - fixture

from app.models import Notification, ReviewQueueItem, SalesDeal, SalesOrder


def _setup(w):
    db = w["db"]
    sally = make_user(db, role="sales", name="Sally Parker")
    w["reps"]["SP"].user_id = sally.id
    sam = make_user(db, role="sales", name="Samantha Elmer")
    db.flush()
    return db, identity_headers(sally), sam


def _kinds(client, h):
    return {k["kind"] for k in client.get("/api/review-queue/kinds", headers=h).json()}


def test_only_accounts_checks_bookings_once_someone_has_the_permission(w, client):
    db, sally_h, sam = _setup(w)
    admin_h = w["h"]
    # nobody has the permission yet: managers check, as before
    assert "order_check" in _kinds(client, admin_h) and "order_check" not in _kinds(client, identity_headers(sam))
    sam.can_approve_bookings = True
    db.commit()
    sam_h = identity_headers(sam)
    assert "order_check" in _kinds(client, sam_h) and "booking_change" in _kinds(client, sam_h)   # even though she's a sales login
    assert "order_check" not in _kinds(client, admin_h)                                          # the admin no longer does it
    d = client.post("/api/sales/deals", json=_wisconsin(w), headers=sally_h).json()
    item = db.query(ReviewQueueItem).filter_by(kind="order_check", status="pending").one()
    db.commit()
    assert client.post(f"/api/review-queue/{item.id}/actions/approve", json={}, headers=admin_h).status_code == 404
    assert client.post(f"/api/review-queue/{item.id}/actions/approve", json={}, headers=sam_h).status_code == 200
    db.expire_all()
    assert client.get(f"/api/sales/deals/{d['id']}", headers=sally_h).json()["check"]["state"] == "checked"


def test_checked_booking_changes_go_through_accounts(w, client):
    db, sally_h, sam = _setup(w)
    sam.can_approve_bookings = True
    db.commit()
    sam_h = identity_headers(sam)
    body = _wisconsin(w)
    d = client.post("/api/sales/deals", json=body, headers=sally_h).json()
    item = db.query(ReviewQueueItem).filter_by(kind="order_check", status="pending").one()
    db.commit()
    client.post(f"/api/review-queue/{item.id}/actions/approve", json={}, headers=sam_h)
    db.expire_all()
    got = client.get(f"/api/sales/deals/{d['id']}", headers=sally_h).json()
    assert got["locked"] and not got["can_approve"]

    # the salesperson can't edit or cancel it any more
    changed = {**body, "package_price_gbp": 3500, "lines": [{**ln, "key": got["lines"][i]["key"],
               "placements": [{**pl, "order_id": got["lines"][i]["placements"][j]["order_id"]} for j, pl in enumerate(ln["placements"])]}
               for i, ln in enumerate(body["lines"])]}
    r = client.put(f"/api/sales/deals/{d['id']}", json=changed, headers=sally_h)
    assert r.status_code == 409 and "Request a change" in r.json()["detail"]
    assert client.post(f"/api/sales/deals/{d['id']}/status", json={"status": "cancelled", "reason": "x"}, headers=sally_h).status_code == 409

    # an invoiced item shows up as a knock-on
    o = db.query(SalesOrder).filter_by(deal_id=d["id"]).first()
    o.invoice_number = "INV-1001"
    db.commit()
    r = client.post(f"/api/sales/deals/{d['id']}/change-request", json={"reason": "Client upgraded the package", "booking": changed}, headers=sally_h)
    assert r.status_code == 201, r.text
    assert r.json()["pending_change"]["requested_by"] == "Sally Parker"
    req = db.query(ReviewQueueItem).filter_by(kind="booking_change", status="pending").one()
    text = " ".join(x["value"] for x in req.payload["details"])
    assert "£3,000.00  →  £3,500.00" in text and "INV-1001" in text and "credit note" in text
    assert db.query(Notification).filter_by(user_id=sam.id, kind="booking_change").count() == 1
    # nothing has changed yet
    assert float(db.get(SalesDeal, req.payload["deal_id"]).total_gbp) == 3000

    # declining needs a reason; approving applies it and the booking stays checked
    db.commit()
    assert client.post(f"/api/review-queue/{req.id}/actions/decline", json={}, headers=sam_h).status_code == 400
    assert client.post(f"/api/review-queue/{req.id}/actions/approve", json={}, headers=sam_h).status_code == 200
    db.expire_all()
    got = client.get(f"/api/sales/deals/{d['id']}", headers=sally_h).json()
    assert got["totals"]["total_gbp"] == 3500 and got["check"]["state"] == "checked" and not got["pending_change"]
    assert db.query(Notification).filter_by(kind="booking_change").filter(Notification.title.like("%approved%")).count() == 1

    # cancelling through a request
    client.post(f"/api/sales/deals/{d['id']}/change-request", json={"reason": "Client pulled out", "cancel": True,
                                                                  "cancel_reason": "Budget cut"}, headers=sally_h)
    req2 = db.query(ReviewQueueItem).filter_by(kind="booking_change", status="pending").one()
    db.commit()
    client.post(f"/api/review-queue/{req2.id}/actions/approve", json={}, headers=sam_h)
    db.expire_all()
    assert client.get(f"/api/sales/deals/{d['id']}", headers=sally_h).json()["status"] == "cancelled"


def test_accounts_can_change_a_checked_booking_directly(w, client):
    db, sally_h, sam = _setup(w)
    sam.can_approve_bookings = True
    db.commit()
    sam_h = identity_headers(sam)
    body = _wisconsin(w)
    d = client.post("/api/sales/deals", json=body, headers=sally_h).json()
    item = db.query(ReviewQueueItem).filter_by(kind="order_check", status="pending").one()
    db.commit()
    client.post(f"/api/review-queue/{item.id}/actions/approve", json={}, headers=sam_h)
    r = client.put(f"/api/sales/deals/{d['id']}", json={**body, "client_name": "Cellet Travel"}, headers=sam_h)
    assert r.status_code == 200 and r.json()["check"]["state"] == "checked"   # no need to check her own change


def test_confirmations_copy_production_and_accounts(w, client):
    h = w["h"]
    cur = client.get("/api/sales/deals/settings", headers=h).json()
    bad = client.put("/api/sales/deals/settings", json={**cur, "production_emails": "not-an-email"}, headers=h)
    assert bad.status_code == 422
    r = client.put("/api/sales/deals/settings", json={**cur, "production_emails": "production@bmi.example; ads@bmi.example",
                                                       "accounts_emails": "samantha@bmi.example"}, headers=h)
    assert r.status_code == 200 and r.json()["production_emails"] == "production@bmi.example, ads@bmi.example"
    d = client.post("/api/sales/deals", json=_wisconsin(w), headers=h).json()
    draft = client.get(f"/api/sales/deals/{d['id']}/email-draft", headers=h).json()
    assert draft["cc"] == ["production@bmi.example", "ads@bmi.example", "samantha@bmi.example"]
