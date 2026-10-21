"""Who looks after each client (Matt, 20 Oct): product first, then whoever was last in touch or last booked them in
the last two years, then Onboard Hospitality new business for Craig, then Selling Travel by destination - and the
Review Queue asks when it isn't sure, remembering the answer."""
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from app.automations import client_owners as co
from app.automations.registry import get_kind
from app.models import ClientOwner, Company, Contact, HistoryEntry, Note, ReviewQueueItem, SalesEdition, SalesOrder, SalesRep, SalesTitle
from app.sales import ownership
from app.sales.reference import ensure_reference_data
from app.sales.regions import spot, spot_website
from tests.conftest import identity_headers, make_user

TODAY = date(2026, 10, 21)


@pytest.fixture()
def w(db_session):
    ensure_reference_data(db_session)
    reps = {r.code: r for r in db_session.query(SalesRep).all()}
    titles = {t.slug: t for t in db_session.query(SalesTitle).all()}

    def company(name, source_db="sellingtravel", **kw):
        c = Company(id=uuid.uuid4(), name=name, source_db=source_db, source_act_id=str(uuid.uuid4()), **kw)
        db_session.add(c)
        db_session.flush()
        return c

    def note(c, author, on, *, via_contact=False, user_id=None):
        eid, et = c.id, "company"
        if via_contact:
            p = Contact(id=uuid.uuid4(), source_db=c.source_db, source_act_id=str(uuid.uuid4()), company_id=c.id, full_name="Pat Client")
            db_session.add(p)
            db_session.flush()
            eid, et = p.id, "contact"
        db_session.add(Note(id=uuid.uuid4(), source_db=c.source_db, source_act_id=str(uuid.uuid4()), entity_type=et, entity_id=eid,
                            body="Spoke to them", act_author=author, created_by_user_id=user_id,
                            act_created_at=datetime(on.year, on.month, on.day, tzinfo=timezone.utc)))
        db_session.flush()

    def booking(c, slug, rep, on):
        e = SalesEdition(id=uuid.uuid4(), title_id=titles[slug].id, year=on.year, name=f"Ed {uuid.uuid4().hex[:4]}", edition_date=on, kind="issue")
        db_session.add(e)
        db_session.flush()
        db_session.add(SalesOrder(id=uuid.uuid4(), edition_id=e.id, client_name=c.name, company_id=c.id, value_gbp=1000,
                                  rep_id=reps[rep].id, booked_on=on, status="booked"))
        db_session.flush()

    def owners(c):
        ownership.refresh(db_session, [c.id], today=TODAY)
        return {r.area: r for r in db_session.query(ClientOwner).filter_by(company_id=c.id)}

    return {"reps": reps, "company": company, "note": note, "booking": booking, "owners": owners}


def code(w, row):
    return next((k for k, r in w["reps"].items() if r.id == row.rep_id), None)


def test_regions_follow_the_destination_not_the_office():
    assert spot("Visit Malta UK") == [("Western Europe", "malta")]          # London office, Malta client
    assert spot("Royal Caribbean International") == [("Ocean and river cruise", "royal caribbean")]
    assert spot("New Jersey Tourism") == [("North America", "new jersey")]  # not Jersey, Channel Islands
    assert spot("Jersey Tourism") == [("Channel Islands", "jersey")]
    assert spot("Travel UK Ltd") == [("UK", "uk")]                          # UK words count only on their own
    assert {r for r, _ in spot("Kuoni (Asia, Africa, Caribbean)")} == {"Asia", "Africa", "Caribbean"}
    assert spot("Turkish Airlines") == [] and spot("Gate Gourmet") == []    # left for a person to decide
    assert spot_website("www.visitmalta.com") == [("Western Europe", "malta")]


def test_product_rules_and_selling_travel_regions(w):
    malta = w["company"]("Visit Malta", website="visitmalta.com")
    rows = w["owners"](malta)
    assert code(w, rows["tbtm"]) == "KH" and rows["tbtm"].rule == "product"
    assert code(w, rows["stm-events"]) == "ST" and code(w, rows["accessibility"]) == "DW"
    assert code(w, rows["stm"]) == "DW" and rows["stm"].rule == "region"
    assert "Malta (Western Europe)" in rows["stm"].reason and "obh" not in rows

    dubai = w["company"]("Dubai Tourism")
    assert code(w, w["owners"](dubai)["stm"]) == "ST"
    jamaica = w["company"]("Jamaica Tourist Board")
    assert code(w, w["owners"](jamaica)["stm"]) == "SP"


def test_an_existing_client_stays_with_whoever_was_last_in_touch(w):
    malta = w["company"]("Visit Malta")
    w["note"](malta, "Sally Parker", TODAY - timedelta(days=90), via_contact=True)   # a note on one of their people counts
    row = w["owners"](malta)["stm"]
    assert code(w, row) == "SP" and row.rule == "last_contact" and "Sally Parker was the last in touch" in row.reason

    w["booking"](malta, "selling-travel", "DW", TODAY - timedelta(days=10))        # a later booking wins
    row = w["owners"](malta)["stm"]
    assert code(w, row) == "DW" and row.rule == "last_booking"

    w["note"](malta, "Kirsty Hicks", TODAY - timedelta(days=1))                     # not on the Selling Travel team
    assert code(w, w["owners"](malta)["stm"]) == "DW"


def test_onboard_hospitality_sue_keeps_hers_and_new_business_goes_to_craig(w):
    sues = w["company"]("Gate Gourmet", "onboard")
    w["note"](sues, "Sue Wiliams", TODAY - timedelta(days=400))                    # Act!'s typo still counts as Sue
    row = w["owners"](sues)["obh"]
    assert code(w, row) == "SW" and row.rule == "last_contact" and set(w["owners"](sues)) == {"obh"}

    old = w["company"]("Old Airline", "onboard")
    w["note"](old, "Sue Williams", TODAY - timedelta(days=3 * 365))                # older than two years
    row = w["owners"](old)["obh"]
    assert code(w, row) == "CM" and row.rule == "new_business" and "last 2 years" in row.reason


def test_several_regions_go_to_the_last_contact_or_whoever_takes_it_first(w):
    tour = w["company"]("Kuoni Asia & Caribbean")
    row = w["owners"](tour)["stm"]
    assert row.rep_id is None and row.rule == "first_to_take"
    w["note"](tour, "David Wilcox", TODAY - timedelta(days=5 * 365))               # however long ago
    row = w["owners"](tour)["stm"]
    assert code(w, row) == "DW" and row.rule == "last_contact" and "several regions" in row.reason


def test_not_sure_asks_once_and_the_answer_is_kept(w, db_session):
    admin = make_user(db_session, role="admin", name="Matt Bonner")
    mystery = w["company"]("Wanderlust Partners")
    w["note"](mystery, "David Wilcox", TODAY - timedelta(days=4 * 365))
    stats = ownership.refresh(db_session, [mystery.id], today=TODAY)
    row = db_session.query(ClientOwner).filter_by(company_id=mystery.id, area="stm").one()
    assert row.rule == "not_sure" and code(w, row) == "DW" and (mystery.id, "stm") in stats["not_sure"]

    assert co.ask(db_session, stats["not_sure"], 50) == 1
    assert co.ask(db_session, stats["not_sure"], 50) == 0                           # asked once only
    item = db_session.query(ReviewQueueItem).filter_by(kind="client_owner").one()
    p = item.payload
    assert p["summary"] == "Who looks after Wanderlust Partners on Selling Travel?"
    assert p["details"][0]["href"] == f"/companies/{mystery.id}"                    # opens the client
    assert p["facets"]["suggestion"] == "David Wilcox" and p["sort_date"]
    assert {o["label"] for o in p["field_options"]["rep_id"]} == {"Sally Parker", "Steven Thompson", "David Wilcox"}
    kind = get_kind("client_owner")
    assert kind.facets and kind.date_sort_label

    sally = w["reps"]["SP"]
    kind.handler(db_session, item, "choose", {"rep_id": str(sally.id), "_actor_user_id": str(admin.id)})
    row = db_session.query(ClientOwner).filter_by(company_id=mystery.id, area="stm").one()
    assert row.chosen and row.rep_id == sally.id and "Chosen by Matt Bonner" in row.reason
    w["booking"](mystery, "selling-travel", "DW", TODAY - timedelta(days=3))
    assert w["owners"](mystery)["stm"].rep_id == sally.id                           # the answer is kept

    with pytest.raises(ValueError, match="Pick the salesperson"):
        kind.handler(db_session, item, "choose", {"rep_id": str(w["reps"]["KH"].id)})


def test_a_question_closes_itself_once_a_note_settles_it(w, db_session):
    mystery = w["company"]("Bright Horizons Travel")
    w["note"](mystery, "Steven Thompson", TODAY - timedelta(days=4 * 365))
    co.ask(db_session, ownership.refresh(db_session, [mystery.id], today=TODAY)["not_sure"], 50)
    w["note"](mystery, "Sally Parker", TODAY - timedelta(days=2))
    ownership.refresh(db_session, [mystery.id], today=TODAY)
    assert co.settle(db_session) == 1
    item = db_session.query(ReviewQueueItem).filter_by(kind="client_owner").one()
    assert item.status == "approved" and item.resolved_action == "settled" and "Sally Parker" in item.review_note


def test_company_page_shows_and_changes_who_looks_after_them(client, db_session, w):
    admin = make_user(db_session, role="admin", name="Matt Bonner")
    sales = make_user(db_session, role="sales", name="Sally")
    malta = w["company"]("Visit Malta")
    r = client.get(f"/api/companies/{malta.id}/owners", headers=identity_headers(admin))
    assert r.status_code == 200, r.text
    out = r.json()
    stm = next(o for o in out["owners"] if o["area"] == "stm")
    assert stm["rep_name"] == "David Wilcox" and stm["rule_label"] == "By region" and out["can_change"]

    sally = w["reps"]["SP"]
    r = client.put(f"/api/companies/{malta.id}/owners/stm", json={"rep_id": str(sally.id)}, headers=identity_headers(sales, access=[("sellingtravel", None)]))
    assert r.status_code == 403 and "administrators and data managers" in r.json()["detail"]
    r = client.put(f"/api/companies/{malta.id}/owners/stm", json={"rep_id": str(sally.id)}, headers=identity_headers(admin))
    stm = next(o for o in r.json()["owners"] if o["area"] == "stm")
    assert stm["rep_name"] == "Sally Parker" and stm["chosen"] and stm["rule_label"] == "Chosen by a person"

    r = client.put(f"/api/companies/{malta.id}/owners/stm", json={"rep_id": None, "back_to_rules": True}, headers=identity_headers(admin))
    stm = next(o for o in r.json()["owners"] if o["area"] == "stm")
    assert stm["rep_name"] == "David Wilcox" and not stm["chosen"]
    r = client.put(f"/api/companies/{malta.id}/owners/nope", json={"rep_id": None}, headers=identity_headers(admin))
    assert r.status_code == 400 and r.json()["detail"] == "That magazine isn't one we know."


def test_renewals_go_to_whoever_looks_after_the_client(w, db_session):
    from app.sales.renewals import owner_user_id

    david_login = make_user(db_session, role="sales", name="David Wilcox")
    sally_login = make_user(db_session, role="sales", name="Sally Parker")
    w["reps"]["DW"].user_id, w["reps"]["SP"].user_id = david_login.id, sally_login.id
    malta = w["company"]("Visit Malta")
    w["booking"](malta, "selling-travel", "SP", TODAY - timedelta(days=5 * 365))   # Sally sold it years ago
    w["owners"](malta)
    order = db_session.query(SalesOrder).filter_by(company_id=malta.id).one()
    assert owner_user_id(db_session, order) == david_login.id                       # Malta is David's now
