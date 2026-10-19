"""Screen fixes from the 17 Oct check: shared bookings in the salesperson filters, items that belong to a booking,
the Pencilled and Draft in Xero filters, who may change edition costs, deadline reminder catch-up, Plan next year
copying the theme, the proposal requests report's person filter, proposals paging and the unbooked-advert message."""
import uuid
from datetime import datetime, timedelta, timezone

from app.automations import editorial_deadlines
from app.automations.proposal_requests import stamp_salesperson
from app.models import ReviewQueueItem, SalesDeal, SalesEdition, SalesOrder, SalesRep, SalesTitle
from app.models.automation_setting import AutomationSetting
from app.models.messaging import Notification
from app.models.xero import XeroInvoice
from app.sales.invoice_numbers import canonical
from app.sales.reference import ensure_reference_data
from tests.conftest import identity_headers, make_user
from tests.test_editorial_hookups import TODAY, Y, world  # noqa: F401 - the shared editorial fixture


def _setup(db_session):
    ensure_reference_data(db_session)
    title = db_session.query(SalesTitle).filter_by(slug="obh").one()
    ed = SalesEdition(id=uuid.uuid4(), title_id=title.id, year=TODAY.year, name="Screen fixes", kind="issue", edition_date=TODAY)
    db_session.add(ed)
    db_session.flush()
    return title, ed


def _deal(db_session, number, **kw):
    d = SalesDeal(id=uuid.uuid4(), number=number, status="confirmed", client_name=f"Client {number}", booked_on=TODAY, lines=[],
                  split=kw.pop("split", []), **kw)
    db_session.add(d)
    db_session.flush()
    return d


def test_shared_bookings_show_under_my_bookings_and_the_salesperson_filter(client, db_session):
    _setup(db_session)
    me_user = make_user(db_session, role="sales")
    reps = db_session.query(SalesRep).limit(2).all()
    me, other = reps
    me.user_id = me_user.id
    db_session.flush()
    mine = _deal(db_session, 990001, rep_id=me.id)
    shared = _deal(db_session, 990002, rep_id=other.id, split=[{"rep_id": str(other.id), "pct": 0.5}, {"rep_id": str(me.id), "pct": 0.5}])
    theirs = _deal(db_session, 990003, rep_id=other.id)
    h = identity_headers(make_user(db_session, role="admin"))

    got = {d["number"] for d in client.get("/api/sales/deals?mine=true&limit=200", headers=identity_headers(me_user)).json()["items"]}
    assert {mine.number, shared.number} <= got and theirs.number not in got
    got = {d["number"] for d in client.get(f"/api/sales/deals?rep_id={me.id}&limit=200", headers=h).json()["items"]}
    assert {mine.number, shared.number} <= got and theirs.number not in got


def test_an_item_on_a_booking_is_changed_and_removed_on_the_booking(client, db_session):
    _, ed = _setup(db_session)
    d = _deal(db_session, 990010)
    o = SalesOrder(id=uuid.uuid4(), edition_id=ed.id, deal_id=d.id, client_name="Client 990010", value_gbp=1000, booked_on=TODAY)
    db_session.add(o)
    db_session.flush()
    h = identity_headers(make_user(db_session, role="admin"))
    r = client.patch(f"/api/sales/orders/{o.id}", json={"value_gbp": 5}, headers=h)
    assert r.status_code == 409 and "on the booking" in r.json()["detail"]
    r = client.delete(f"/api/sales/orders/{o.id}", headers=h)
    assert r.status_code == 409 and "booking 990010" in r.json()["detail"]
    assert db_session.get(SalesOrder, o.id) is not None
    # invoice details can still be changed on the item
    assert client.patch(f"/api/sales/orders/{o.id}", json={"notes": "Checked"}, headers=h).status_code == 200


def test_pencilled_and_draft_in_xero_filters(client, db_session):
    _, ed = _setup(db_session)
    pencil = SalesOrder(id=uuid.uuid4(), edition_id=ed.id, client_name="Pencil Ltd", value_gbp=500, booked_on=TODAY, status="pencilled")
    draft = SalesOrder(id=uuid.uuid4(), edition_id=ed.id, client_name="Draft Ltd", value_gbp=700, booked_on=TODAY, invoice_number="INV-SF-1",
                       invoiced_on=TODAY)
    db_session.add_all([pencil, draft])
    db_session.add(XeroInvoice(id=uuid.uuid4(), xero_id=str(uuid.uuid4()), invoice_number="INV-SF-1", number_key=canonical("INV-SF-1"), status="DRAFT",
                               amount_due=840, amount_paid=0, total=840))
    db_session.flush()
    h = identity_headers(make_user(db_session, role="admin"))
    rows = client.get(f"/api/sales/orders?edition_id={ed.id}&status=pencilled", headers=h).json()
    assert [r["client_name"] for r in rows["items"]] == ["Pencil Ltd"]
    rows = client.get(f"/api/sales/orders?edition_id={ed.id}&xero=draft", headers=h).json()
    assert [r["client_name"] for r in rows["items"]] == ["Draft Ltd"]


def test_only_people_who_may_change_costs_are_offered_the_controls(client, db_session):
    _, ed = _setup(db_session)
    sales, admin = make_user(db_session, role="sales"), make_user(db_session, role="admin")
    assert client.get(f"/api/sales/editions/{ed.id}", headers=identity_headers(sales)).json()["costs"]["can_edit"] is False
    assert client.get(f"/api/sales/editions/{ed.id}", headers=identity_headers(admin)).json()["costs"]["can_edit"] is True
    line = {"kind": "cost", "label": "Printing", "amount_gbp": 100}
    assert client.post(f"/api/sales/editions/{ed.id}/costs", json=line, headers=identity_headers(sales)).status_code == 403
    r = client.post(f"/api/sales/editions/{ed.id}/costs", json=line, headers=identity_headers(admin))
    assert r.status_code == 201 and r.json()["can_edit"] is True
    ed.costs_signed_off_at = datetime.now(timezone.utc)   # signed off: nobody changes them until reopened
    db_session.flush()
    assert client.get(f"/api/sales/editions/{ed.id}/costs", headers=identity_headers(admin)).json()["can_edit"] is False


def test_a_missed_deadline_reminder_is_caught_up_once(db_session, world):  # noqa: F811
    sw = db_session.query(SalesRep).filter_by(code="SW").one()
    sw.user_id = world["rep"].id
    db_session.add(AutomationSetting(key="editorial_deadline_alert_days", value={"v": "7,1"}))
    db_session.flush()
    # the job didn't run on day 7: two days later it sends the 7-day reminder, saying how long is really left
    assert editorial_deadlines.remind(db_session, TODAY + timedelta(days=2)) == 1
    n = db_session.query(Notification).filter_by(user_id=world["rep"].id, kind="editorial_deadline").one()
    assert "advertising deadline in 5 days" in n.title
    assert editorial_deadlines.remind(db_session, TODAY + timedelta(days=3)) == 0   # not again
    assert editorial_deadlines.remind(db_session, TODAY + timedelta(days=7)) == 1   # the 1-day one, missed too: "today"
    assert editorial_deadlines.remind(db_session, TODAY + timedelta(days=7)) == 0
    titles = sorted(x.title for x in db_session.query(Notification).filter_by(user_id=world["rep"].id, kind="editorial_deadline"))
    assert any("deadline today" in t for t in titles) and len(titles) == 2


def test_plan_next_year_copies_the_theme_but_not_the_notes(client, db_session, world):  # noqa: F811
    nxt = world["next"]
    nxt.notes = "Ask Sam about the cover"
    db_session.flush()
    res = client.post("/api/editorial/next-year", json={"brand": "obh", "from_year": Y}, headers=world["admin"]).json()
    assert res["created"] >= 1
    new = db_session.query(SalesEdition).filter(SalesEdition.year == Y + 1, SalesEdition.title_id == nxt.title_id,
                                                SalesEdition.theme == "Sustainability").one()
    assert new.notes is None and new.plan_needs_check


def test_proposal_requests_can_be_filtered_by_salesperson(client, db_session):
    owner = make_user(db_session, role="sales", name="Sally Parker")
    old = ReviewQueueItem(id=uuid.uuid4(), kind="proposal_request", status="pending",
                          payload={"summary": "Old card", "owner_user_id": str(owner.id), "facets": {"magazine": "OBH"}})
    db_session.add(old)
    db_session.flush()
    assert stamp_salesperson(db_session) == 1
    assert old.payload["facets"] == {"magazine": "OBH", "salesperson": "Sally Parker"}
    assert stamp_salesperson(db_session) == 0
    db_session.flush()
    admin = identity_headers(make_user(db_session, role="admin"))
    rep = client.get("/api/proposal-report?days=30", headers=admin).json()
    row = next(r for r in rep["rows"] if r["user_id"] == str(owner.id))
    assert row["queue_filter"] == "salesperson:Sally Parker"
    # picking one person keeps everyone in the chips
    other = make_user(db_session, role="sales", name="Other Person")
    db_session.add(ReviewQueueItem(id=uuid.uuid4(), kind="proposal_request", status="pending",
                                   payload={"summary": "x", "owner_user_id": str(other.id), "facets": {"salesperson": "Other Person"}}))
    db_session.flush()
    rep = client.get(f"/api/proposal-report?days=30&user_id={owner.id}", headers=admin).json()
    assert {o["user_id"] for o in rep["owners"]} >= {str(owner.id), str(other.id)}
    assert [r["user_id"] for r in rep["rows"]] == [str(owner.id)]
    cards = client.get("/api/review-queue?kind=proposal_request&status=pending&facet=salesperson:Sally Parker", headers=admin).json()
    assert [c["id"] for c in cards["items"]] == [str(old.id)]


def test_unbooked_advert_explains_a_salesperson_without_a_login(client, db_session):
    _, ed = _setup(db_session)
    rep = SalesRep(id=uuid.uuid4(), code="ZZ", name="Zed Without-Login", active=True)
    db_session.add(rep)
    db_session.flush()
    r = client.post("/api/sales/deals/unbooked-ad", json={"edition_id": str(ed.id), "client_name": "Acme", "rep_id": str(rep.id),
                                                          "outcome": "needs_booking"}, headers=identity_headers(make_user(db_session, role="admin")))
    assert r.status_code == 422 and "can't sign in" in r.json()["detail"]


def test_proposals_list_pages(client, db_session):
    h = identity_headers(make_user(db_session, role="admin"))
    assert client.get("/api/proposals?limit=1&offset=0", headers=h).status_code == 200
    assert client.get("/api/proposals?limit=0", headers=h).status_code == 422
