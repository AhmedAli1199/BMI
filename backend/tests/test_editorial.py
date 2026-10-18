"""Editorial plan: loading the published plan, planner, deadlines, issue editing, features, rules, next year, rights, re-import safety."""
import uuid
from datetime import date, timedelta

import pytest

from app.models import EditionFeature, SalesEdition, SalesOrder, SalesRep, SalesTitle
from app.sales.editorial import compute_deadlines, describe_rule, shift_year
from app.sales.reference import ensure_reference_data
from tests.conftest import identity_headers, make_user

Y = 2026


@pytest.fixture()
def world(db_session):
    ensure_reference_data(db_session)
    admin = make_user(db_session, role="admin")
    kirsty = make_user(db_session, role="sales")
    db_session.query(SalesRep).filter_by(code="KH").one().user_id = kirsty.id
    db_session.flush()
    obh = db_session.query(SalesTitle).filter_by(slug="obh").one()
    return {"admin": identity_headers(admin), "kirsty": identity_headers(kirsty), "obh": obh}


def test_rules():
    assert compute_deadlines([{"key": "copy", "kind": "day_prev_month", "value": 25}], date(2026, 3, 1)) == {"copy": date(2026, 2, 25)}
    assert compute_deadlines([{"key": "copy", "kind": "day_prev_month", "value": 31}], date(2026, 3, 5))["copy"] == date(2026, 2, 28)
    assert compute_deadlines([{"key": "editorial", "kind": "days_before", "value": 9}], date(2026, 6, 11))["editorial"] == date(2026, 6, 2)
    assert compute_deadlines([{"key": "copy", "kind": "day_prev_month", "value": 25}], date(2026, 1, 10))["copy"] == date(2025, 12, 25)
    assert describe_rule({"kind": "day_prev_month", "value": 25}) == "25th of the month before publication"
    d = shift_year(date(2026, 3, 19))
    assert d.weekday() == date(2026, 3, 19).weekday() and abs((d - date(2027, 3, 19)).days) <= 3


def test_load_plan_matches_existing_issue_and_fills_planner(client, db_session, world):
    # the order register already has OBH 105 with bookings
    e105 = SalesEdition(id=uuid.uuid4(), title_id=world["obh"].id, year=Y, name="105", kind="issue", edition_date=date(2026, 3, 1), source_file="x.xls")
    db_session.add(e105)
    db_session.flush()
    db_session.add(SalesOrder(id=uuid.uuid4(), edition_id=e105.id, client_name="Delta", value_gbp=2990))
    db_session.flush()
    pl = client.get(f"/api/editorial/planner?year={Y}", headers=world["admin"]).json()
    obh = next(b for b in pl["brands"] if b["key"] == "obh")
    assert obh["seed_available"] == 4  # the 2027 awards item counts in 2027
    r = client.post(f"/api/editorial/brands/obh/load-plan?year={Y}", headers=world["admin"]).json()
    assert r["issues"] == 5 and r["features"] > 50
    db_session.expire_all()
    e = db_session.get(SalesEdition, e105.id)
    assert e.edition_date == date(2026, 3, 19) and e.ad_deadline == date(2026, 3, 10) and e.editorial_deadline == date(2026, 2, 16)
    assert "Hamburg" in e.distribution and db_session.query(EditionFeature).filter_by(edition_id=e.id).count() == 17
    pl = client.get(f"/api/editorial/planner?year={Y}", headers=world["admin"]).json()
    obh = next(b for b in pl["brands"] if b["key"] == "obh")
    issues = next(row for row in obh["rows"] if row["title_name"].startswith("OnBoard"))["issues"]
    assert [i["name"] for i in issues] == ["105", "106", "107", "108"]
    assert issues[0]["booked_gbp"] == 2990 and obh["seed_available"] == 0
    # loading again changes nothing
    assert client.post(f"/api/editorial/brands/obh/load-plan?year={Y}", headers=world["admin"]).json()["features"] == 0


def test_tbtm_dates_from_rules_are_flagged(client, db_session, world):
    client.post(f"/api/editorial/brands/tbtm/load-plan?year={Y}", headers=world["admin"])
    pl = client.get(f"/api/editorial/planner?year={Y}", headers=world["admin"]).json()
    tbtm = next(b for b in pl["brands"] if b["key"] == "tbtm")
    spring = next(i for row in tbtm["rows"] for i in row["issues"] if i["name"] == "Spring issue")
    assert spring["copy_deadline"] == "2026-02-25" and spring["needs_check"]
    assert {"label": "Sponsored content deadline", "date": "2026-02-18", "rule": "sponsored"} in spring["milestones"]
    dinners = [i for row in tbtm["rows"] for i in row["issues"] if i["name"].startswith("Dinner Club")]
    assert len(dinners) == 4 and not dinners[0]["needs_check"]


def test_deadlines_list(client, db_session, world):
    soon = date.today() + timedelta(days=5)
    client.post("/api/editorial/issues", json={"brand": "obh", "title_id": str(world["obh"].id), "year": soon.year, "name": "Test issue",
                                               "edition_date": (soon + timedelta(days=10)).isoformat(), "ad_deadline": soon.isoformat(), "use_rules": False},
                headers=world["admin"])
    d = client.get("/api/editorial/deadlines?days=30&brand=obh", headers=world["admin"]).json()
    kinds = [(x["type"], x["days"]) for x in d if x["issue"]["name"] == "Test issue"]
    assert ("advertising", 5) in kinds and ("publication", 15) in kinds


def test_issue_crud_features_and_rights(client, db_session, world):
    h = world["admin"]
    client.put("/api/editorial/brands/obh/settings", json={"deadline_rules": [{"key": "advertising", "label": "Advertising deadline", "kind": "days_before", "value": 9},
                                                                            {"key": "press", "label": "Press day", "kind": "days_before", "value": 3}],
                                                         "regular_sections": [{"name": "Retail"}], "about": "Quarterly"}, headers=h)
    r = client.post("/api/editorial/issues", json={"brand": "obh", "title_id": str(world["obh"].id), "year": 2027, "name": "109", "edition_date": "2027-03-18"}, headers=h)
    assert r.status_code == 201, r.text
    iss = r.json()
    assert iss["ad_deadline"] == "2027-03-09" and iss["milestones"] == [{"label": "Press day", "date": "2027-03-15", "rule": "press"}]
    assert iss["settings"]["regular_sections"][0]["name"] == "Retail" and iss["can_delete"]
    assert client.post("/api/editorial/issues", json={"brand": "obh", "title_id": str(world["obh"].id), "year": 2027, "name": "109"}, headers=h).status_code == 409
    # features
    f = client.post(f"/api/editorial/issues/{iss['id']}/features", json={"title": "Seafood", "sponsorable": True}, headers=h).json()
    client.post(f"/api/editorial/issues/{iss['id']}/features", json={"title": "Napkins"}, headers=h)
    client.patch(f"/api/editorial/features/{f['id']}", json={"status": "confirmed"}, headers=h)
    det = client.get(f"/api/editorial/issues/{iss['id']}", headers=h).json()
    assert [x["title"] for x in det["feature_list"]] == ["Seafood", "Napkins"] and det["feature_list"][0]["status"] == "confirmed"
    client.post(f"/api/editorial/issues/{iss['id']}/features/reorder", json={"ids": [det["feature_list"][1]["id"], f["id"]]}, headers=h)
    assert client.get(f"/api/editorial/issues/{iss['id']}", headers=h).json()["feature_list"][0]["title"] == "Napkins"
    # edit date -> needs_check cleared; apply rules
    client.patch(f"/api/editorial/issues/{iss['id']}", json={"edition_date": "2027-03-25", "theme": "WTCE"}, headers=h)
    det = client.post(f"/api/editorial/issues/{iss['id']}/apply-rules", headers=h).json()
    assert det["ad_deadline"] == "2027-03-16" and det["theme"] == "WTCE"
    # a TBTM publisher can't change OBH
    assert client.patch(f"/api/editorial/issues/{iss['id']}", json={"theme": "x"}, headers=world["kirsty"]).status_code == 403
    assert client.post(f"/api/editorial/issues/{iss['id']}/features", json={"title": "x"}, headers=world["kirsty"]).status_code == 403
    assert client.delete(f"/api/editorial/issues/{iss['id']}", headers=h).status_code == 204


def _rules(client, h, press_label="Press day"):
    r = client.put("/api/editorial/brands/obh/settings", headers=h, json={"deadline_rules": [
        {"key": "advertising", "label": "Advertising deadline", "kind": "days_before", "value": 9},
        {"key": "editorial", "label": "Editorial deadline", "kind": "days_before", "value": 28},
        {"key": "press", "label": press_label, "kind": "days_before", "value": 3}]})
    assert r.status_code == 200


def test_moving_the_date_moves_year_and_rule_deadlines_but_not_typed_ones(client, db_session, world):
    h = world["admin"]
    _rules(client, h)
    iss = client.post("/api/editorial/issues", json={"brand": "obh", "title_id": str(world["obh"].id), "year": 2026, "name": "Winter",
                                                     "edition_date": "2026-12-10", "editorial_deadline": "2026-11-01"}, headers=h).json()
    assert iss["ad_deadline"] == "2026-12-01" and iss["editorial_deadline"] == "2026-11-01"  # editorial typed by hand
    ms = iss["milestones"] + [{"label": "Launch party", "date": "2026-12-05"}]
    client.patch(f"/api/editorial/issues/{iss['id']}", json={"milestones": ms}, headers=h)
    # saving the "Change dates" form: everything is sent, only the publication date changed - into the next year
    det = client.patch(f"/api/editorial/issues/{iss['id']}", headers=h, json={
        "edition_date": "2027-01-14", "ad_deadline": iss["ad_deadline"], "editorial_deadline": "2026-11-01", "copy_deadline": None, "milestones": ms}).json()
    assert det["year"] == 2027 and det["ad_deadline"] == "2027-01-05" and det["editorial_deadline"] == "2026-11-01"
    assert det["milestones"] == [{"label": "Press day", "date": "2027-01-11", "rule": "press"}, {"label": "Launch party", "date": "2026-12-05", "rule": None}]
    pl = client.get("/api/editorial/planner?year=2027", headers=h).json()
    assert any(i["id"] == iss["id"] for b in pl["brands"] for row in b["rows"] for i in row["issues"])
    # a deadline the person changes in the same save as the date is kept
    det = client.patch(f"/api/editorial/issues/{iss['id']}", headers=h, json={"edition_date": "2027-01-21", "ad_deadline": "2027-01-08"}).json()
    assert det["ad_deadline"] == "2027-01-08" and det["milestones"][0]["date"] == "2027-01-18"
    # can't move into a year that already has an issue with the same name
    client.post("/api/editorial/issues", json={"brand": "obh", "title_id": str(world["obh"].id), "year": 2028, "name": "Winter"}, headers=h)
    assert client.patch(f"/api/editorial/issues/{iss['id']}", json={"edition_date": "2028-01-20"}, headers=h).status_code == 409


def test_undated_issue_gets_deadlines_when_dated(client, db_session, world):
    h = world["admin"]
    _rules(client, h)
    iss = client.post("/api/editorial/issues", json={"brand": "obh", "title_id": str(world["obh"].id), "year": 2027, "name": "Spring"}, headers=h).json()
    assert iss["ad_deadline"] is None and iss["milestones"] == []
    det = client.patch(f"/api/editorial/issues/{iss['id']}", json={"edition_date": "2027-04-15"}, headers=h).json()
    assert det["ad_deadline"] == "2027-04-06" and det["editorial_deadline"] == "2027-03-18" and det["milestones"][0]["rule"] == "press"


def test_renamed_rule_updates_its_key_date_instead_of_adding_one(client, db_session, world):
    h = world["admin"]
    _rules(client, h)
    iss = client.post("/api/editorial/issues", json={"brand": "obh", "title_id": str(world["obh"].id), "year": 2027, "name": "Summer",
                                                     "edition_date": "2027-06-17"}, headers=h).json()
    client.patch(f"/api/editorial/issues/{iss['id']}", json={"milestones": iss["milestones"] + [{"label": "Launch party", "date": "2027-06-10"}]}, headers=h)
    _rules(client, h, press_label="Press day (print)")
    det = client.post(f"/api/editorial/issues/{iss['id']}/apply-rules", headers=h).json()
    assert det["milestones"] == [{"label": "Launch party", "date": "2027-06-10", "rule": None},
                                 {"label": "Press day (print)", "date": "2027-06-14", "rule": "press"}]


def test_next_year_numbers_issues_and_moves_dates(client, db_session, world):
    h = world["admin"]
    client.post(f"/api/editorial/brands/obh/load-plan?year={Y}", headers=h)
    pv = client.post("/api/editorial/next-year/preview", json={"brand": "obh", "from_year": Y}, headers=h).json()
    names = {r["old_name"]: r["new_name"] for r in pv}
    assert names["105"] == "109" and names["108"] == "112"
    row = next(r for r in pv if r["old_name"] == "105")
    assert date.fromisoformat(row["new_date"]).weekday() == date(2026, 3, 19).weekday()
    res = client.post("/api/editorial/next-year", json={"brand": "obh", "from_year": Y}, headers=h).json()
    assert res["created"] == 4
    e = db_session.query(SalesEdition).filter_by(name="109", year=Y + 1).one()
    assert e.plan_needs_check and (e.edition_date - e.ad_deadline).days == 9
    assert db_session.query(EditionFeature).filter_by(edition_id=e.id).count() == 17
    assert client.post("/api/editorial/next-year/preview", json={"brand": "obh", "from_year": Y}, headers=h).json() == []


def test_settings_validation(client, world):
    bad = {"deadline_rules": [{"key": "copy", "label": "Copy", "kind": "day_prev_month", "value": 40}]}
    assert client.put("/api/editorial/brands/tbtm/settings", json=bad, headers=world["admin"]).status_code == 422
    assert client.put("/api/editorial/brands/tbtm/settings", json={"deadline_rules": []}, headers=world["kirsty"]).status_code == 200
    assert client.put("/api/editorial/brands/obh/settings", json={"deadline_rules": []}, headers=world["kirsty"]).status_code == 403


def test_migration_tags_existing_rule_key_dates(client, db_session, world):
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    _rules(client, world["admin"])
    e = SalesEdition(id=uuid.uuid4(), title_id=world["obh"].id, year=2031, name="Old", kind="issue",
                     milestones=[{"label": "Press day", "date": "2031-03-15"}, {"label": "Party", "date": "2031-03-01"}])
    db_session.add(e)
    db_session.flush()
    spec = importlib.util.spec_from_file_location("m0062", Path(__file__).parents[1] / "alembic/versions/0062_milestone_rule_keys.py")
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)
    with Operations.context(MigrationContext.configure(db_session.connection())):
        mig.upgrade()
    db_session.expire_all()
    assert db_session.get(SalesEdition, e.id).milestones == [{"label": "Press day", "date": "2031-03-15", "rule": "press"},
                                                             {"label": "Party", "date": "2031-03-01"}]
