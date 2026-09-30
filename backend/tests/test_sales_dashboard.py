"""SALES-026 dashboard (/api/sales/dashboard) and the edition-pace logic in
app/sales/analytics.py that SALES-028's alerts share."""
import uuid
from datetime import date, timedelta

import pytest

from app.models import SalesEdition, SalesOrder, SalesOrderCredit, SalesRep, SalesTitle
from app.sales.analytics import comparison_cutoff, edition_pace
from app.sales.reference import ensure_reference_data

TODAY = date.today()
KW = dict(threshold=0.25, min_prior_gbp=2000, min_prior_orders=3)


@pytest.fixture()
def world(db_session):
    ensure_reference_data(db_session)
    title = db_session.query(SalesTitle).filter_by(slug="obh").one()
    reps = {r.code: r for r in db_session.query(SalesRep).all()}
    pub = TODAY + timedelta(days=40)
    this = SalesEdition(id=uuid.uuid4(), title_id=title.id, year=pub.year, name="105", edition_date=pub)
    # Last cycle's issue published a fortnight later in the calendar than a
    # straight year-ago date would suggest - issue-relative logic must cope.
    last_pub = pub - timedelta(days=364 - 14)
    last = SalesEdition(id=uuid.uuid4(), title_id=title.id, year=last_pub.year if last_pub.year != pub.year else pub.year - 1,
                        name="101", edition_date=last_pub, status="closed")
    last.year = pub.year - 1
    db_session.add_all([this, last])
    db_session.flush()
    return {"title": title, "reps": reps, "this": this, "last": last, "pub": pub, "last_pub": last_pub}


def order(db, ed, client, value, rep=None, booked_on=None, **kw):
    o = SalesOrder(id=uuid.uuid4(), edition_id=ed.id, client_name=client, value_gbp=value, rep_id=rep.id if rep else None,
                   booked_on=booked_on, **kw)
    db.add(o)
    db.flush()
    if rep and value:
        db.add(SalesOrderCredit(id=uuid.uuid4(), order_id=o.id, rep_id=rep.id, amount_gbp=value))
        db.flush()
    return o


def test_cutoff_is_issue_relative(world):
    # 40 days before this issue publishes == 40 days before last cycle's issue published
    assert comparison_cutoff(world["this"], world["last"], TODAY) == world["last_pub"] - timedelta(days=40)
    world["last"].edition_date = None
    assert comparison_cutoff(world["this"], world["last"], TODAY).year == TODAY.year - 1


def test_behind_when_far_below_last_cycle_at_same_point(db_session, world):
    early = world["last_pub"] - timedelta(days=60)  # booked well before the comparison point
    for i in range(4):
        order(db_session, world["last"], f"C{i}", 1000, booked_on=early)
    order(db_session, world["last"], "Late", 9000, booked_on=world["last_pub"] - timedelta(days=5))  # after the point: ignored
    order(db_session, world["this"], "Now", 1000, booked_on=TODAY - timedelta(days=3))
    row = next(r for r in edition_pace(db_session, TODAY, **KW) if r["edition"].id == world["this"].id)
    assert row["prev_point_gbp"] == 4000 and row["prev_point_orders"] == 4
    assert row["prev_total_gbp"] == 13000
    assert row["gap_gbp"] == -3000 and row["gap_pct"] == pytest.approx(-0.75) and row["state"] == "behind"


def test_ahead_and_on_pace(db_session, world):
    early = world["last_pub"] - timedelta(days=60)
    for i in range(4):
        order(db_session, world["last"], f"C{i}", 1000, booked_on=early)
    order(db_session, world["this"], "Big", 4100, booked_on=TODAY)
    assert edition_pace(db_session, TODAY, **KW)[0]["state"] == "on_pace"  # +2.5%
    order(db_session, world["this"], "Bigger", 2000, booked_on=TODAY)
    assert edition_pace(db_session, TODAY, **KW)[0]["state"] == "ahead"


def test_thin_comparison_is_never_judged(db_session, world):
    early = world["last_pub"] - timedelta(days=60)
    order(db_session, world["last"], "Only", 5000, booked_on=early)  # £5k but a single booking
    row = edition_pace(db_session, TODAY, **KW)[0]
    assert row["state"] == "not_comparable" and "too little" in row["reason"]


def test_no_equivalent_edition_is_not_comparable(db_session, world):
    world["last"].year = TODAY.year - 5  # nothing from last cycle to pair with
    db_session.flush()
    row = edition_pace(db_session, TODAY, editions=[world["this"]], **KW)[0]
    assert row["state"] == "not_comparable" and row["prev"] is None and "No equivalent" in row["reason"]


def test_cancelled_orders_not_counted(db_session, world):
    early = world["last_pub"] - timedelta(days=60)
    for i in range(3):
        order(db_session, world["last"], f"C{i}", 1000, booked_on=early)
    order(db_session, world["last"], "Cancelled", 5000, booked_on=early, status="cancelled")
    order(db_session, world["this"], "Cancelled now", 9000, booked_on=TODAY, status="cancelled")
    row = edition_pace(db_session, TODAY, **KW)[0]
    assert row["prev_point_gbp"] == 3000 and row["booked"] == 0 and row["state"] == "behind"


def test_dashboard_endpoint(client, db_session, world):
    sp, st = world["reps"]["SP"], world["reps"]["ST"]
    early = world["last_pub"] - timedelta(days=60)
    for i in range(3):
        order(db_session, world["last"], f"C{i}", 1000, sp, booked_on=early)
    order(db_session, world["this"], "Now A", 500, sp, booked_on=TODAY - timedelta(days=2))
    order(db_session, world["this"], "Now B", 300, st, booked_on=TODAY - timedelta(days=9))
    order(db_session, world["this"], "Orphan", 250, None, booked_on=TODAY - timedelta(days=1))  # no credit
    d = client.get("/api/sales/dashboard").json()
    assert d["threshold_pct"] == 0.25
    pace = next(p for p in d["pace"] if p["edition"]["id"] == str(world["this"].id))
    assert pace["state"] == "behind" and pace["booked_gbp"] == 1050
    assert len(d["weekly"]) == 12 and sum(w["value_gbp"] for w in d["weekly"]) == 1050
    by_rep = {a["rep"]["code"]: a for a in d["activity"]}
    assert by_rep["SP"]["bookings"] == 1 and by_rep["SP"]["booked_gbp"] == 500 and by_rep["ST"]["bookings"] == 1
    assert [a["rep"]["name"] for a in d["activity"]] == sorted(a["rep"]["name"] for a in d["activity"])  # alphabetical, not ranked
    if world["this"].year == TODAY.year:
        assert d["unattributed"] == {"orders": 1, "value_gbp": 250.0}
