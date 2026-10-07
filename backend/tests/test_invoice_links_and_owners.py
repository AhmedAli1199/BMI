"""Linking invoices by hand (the amount and date always come from Xero), and renewals landing on their salesperson."""
import uuid
from datetime import timedelta

from tests.conftest import identity_headers, make_user
from tests.test_sales_orders import sor  # noqa: F401 - fixture reuse
from tests.test_xero_matching import TODAY, booking, invoice

from app.automations.morning_queue import build_today_queue
from app.automations.state import set_state
from app.automations.xero_matching import UNMATCHED_STATE
from app.models import ReviewQueueItem
from app.sales import invoice_match as im


def test_typed_number_takes_amount_and_date_from_xero(client, db_session, sor):
    admin = identity_headers(make_user(db_session, role="admin"))
    b = booking(db_session, sor, "Atlantic Canada", 500)
    inv = invoice(db_session, "INV-3438", "Atlantic Canada", 480, issued=TODAY - timedelta(days=12), paid=False)
    r = client.patch(f"/api/sales/orders/{b.id}", json={"invoice_number": "inv 3438"}, headers=admin).json()
    assert r["invoice_value_gbp"] == 480 and r["invoiced_on"] == inv.issued_on.isoformat()
    assert r["xero"]["link"] == "typed" and r["xero"]["state"] == "unpaid"
    # a number that isn't in Xero: saved, not linked
    r = client.patch(f"/api/sales/orders/{b.id}", json={"invoice_number": "INV-9999"}, headers=admin).json()
    assert r["xero"] is None and r["invoice_number"] == "INV-9999"


def test_one_invoice_for_two_bookings_keeps_each_value_and_figures_follow_xero(db_session, sor):
    a = booking(db_session, sor, "Delta", 1000, invoice_number="5001")
    b = booking(db_session, sor, "Delta", 600, invoice_number="5001")
    solo = booking(db_session, sor, "Qantas", 900, invoice_number="5002")
    invoice(db_session, "5001", "Delta", 1600)
    q = invoice(db_session, "5002", "Qantas", 900)
    from app.services.xero import link_typed_numbers
    link_typed_numbers(db_session)
    for o in (a, b, solo):
        db_session.refresh(o)
    assert (float(a.invoice_value_gbp), float(b.invoice_value_gbp), float(solo.invoice_value_gbp)) == (1000, 600, 900)
    q.sub_total = 850  # credited in Xero
    db_session.flush()
    assert im.refresh_figures(db_session) == 1
    db_session.flush()
    db_session.refresh(solo)
    assert float(solo.invoice_value_gbp) == 850


def test_pick_an_invoice_for_a_booking(client, db_session, sor):
    admin = identity_headers(make_user(db_session, role="admin"))
    b = booking(db_session, sor, "Foodcase", 1000)
    other = invoice(db_session, "7001", "Someone Else", 300)
    mine = invoice(db_session, "7002", "Foodcase Ltd", 1000)
    choices = client.get(f"/api/sales/orders/{b.id}/xero-choices", headers=admin).json()
    assert choices[0]["number"] == "7002" and set(choices[0]["fit"]) == {"Same client", "Same amount"}
    assert all(c["number"] != "7001" for c in choices)  # no fit at all is left out unless searched
    assert client.get(f"/api/sales/orders/{b.id}/xero-choices?q=7001", headers=admin).json()[0]["number"] == "7001"
    r = client.post(f"/api/sales/orders/{b.id}/xero-link", json={"invoice_id": str(mine.id)}, headers=admin).json()
    assert r["invoice_number"] == "7002" and r["xero"]["link"] == "confirmed" and r["invoice_value_gbp"] == 1000
    assert other.id not in {i.id for i in im.unclaimed_invoices(db_session) if i.id == mine.id}


def test_link_an_unmatched_invoice_to_a_booking(client, db_session, sor):
    admin = identity_headers(make_user(db_session, role="admin"))
    b = booking(db_session, sor, "Monty's", 2000)
    inv = invoice(db_session, "8001", "Montys Ltd", 2000)
    set_state(db_session, UNMATCHED_STATE, {"ids": [str(inv.id)], "at": "2026-10-01T00:00:00+00:00"})
    assert len(client.get("/api/sales/xero/unmatched", headers=admin).json()["items"]) == 1
    ch = client.get(f"/api/sales/xero/invoices/{inv.id}/choices", headers=admin).json()
    assert ch[0]["suggested"] and ch[0]["bookings"][0]["id"] == str(b.id)
    found = client.get(f"/api/sales/xero/invoices/{inv.id}/choices?q=monty", headers=admin).json()
    assert any(c["bookings"][0]["id"] == str(b.id) for c in found)
    r = client.post(f"/api/sales/xero/invoices/{inv.id}/link", json={"order_ids": [str(b.id)]}, headers=admin)
    assert r.status_code == 200 and r.json()[0]["invoice_number"] == "8001"
    assert client.get("/api/sales/xero/unmatched", headers=admin).json()["items"] == []


def test_renewal_goes_to_its_salesperson_once_their_login_is_linked(client, db_session, sor):
    admin_user = make_user(db_session, role="admin")
    sue = make_user(db_session, role="sales", name="Sue Williams")
    other = make_user(db_session, role="sales", name="Other Rep")
    sw = sor["reps"]["SW"]
    o = booking(db_session, sor, "Monty's", 2000, edition="last", rep="SW")
    item = ReviewQueueItem(id=uuid.uuid4(), kind="renewal_due", source_db=None, status="pending",
                           payload={"order_id": str(o.id), "owner_user_id": None, "summary": "Renewal due: Monty's"})
    db_session.add(item)
    db_session.flush()
    sw.user_id = None
    db_session.flush()
    assert build_today_queue(db_session)[0]["owner_name"] == "Unassigned"
    assert build_today_queue(db_session, owner_user_id=str(sue.id)) == []
    # link Sue's login to SW in Settings > Users
    r = client.patch(f"/api/users/{sue.id}", json={"sales_rep_id": str(sw.id)}, headers=identity_headers(admin_user))
    assert r.status_code == 200 and r.json()["sales_rep_code"] == "SW"
    assert [x["owner_name"] for x in build_today_queue(db_session, owner_user_id=str(sue.id))] == ["Sue Williams"]
    # the review queue shows it to Sue, not to another salesperson
    def ids(user):
        return [x["id"] for x in client.get("/api/review-queue?kind=renewal_due", headers=identity_headers(user)).json()["items"]]
    assert str(item.id) in ids(sue) and str(item.id) not in ids(other)
    # one login per salesperson
    r = client.patch(f"/api/users/{other.id}", json={"sales_rep_id": str(sw.id)}, headers=identity_headers(admin_user))
    assert r.status_code == 409
