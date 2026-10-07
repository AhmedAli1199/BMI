"""Editorial plan + rate card hook-ups: proposals pick the issue and apply offers, renewals offer the next issue,
"who should we pitch?", and advertising deadline reminders."""
import io
import uuid
from datetime import date, timedelta

import docx
import pytest

from app.automations import editorial_deadlines
from app.automations.sales_orders import _renewal_facts
from app.models import Company, EditionFeature, RateOffer, SalesEdition, SalesOrder, SalesRate, SalesRep, SalesTitle
from app.models.messaging import Notification
from app.models.automation_setting import AutomationSetting
from app.sales.reference import ensure_reference_data
from tests.conftest import identity_headers, make_user

TODAY = date.today()
Y = TODAY.year


@pytest.fixture()
def world(db_session):
    ensure_reference_data(db_session)
    obh = db_session.query(SalesTitle).filter_by(slug="obh").one()
    company = Company(id=uuid.uuid4(), name="Delta Air Lines", industry="Airline", source_db="onboardhospitality", source_act_id=uuid.uuid4().hex[:12])
    caterer = Company(id=uuid.uuid4(), name="Gate Foods", industry="Inflight catering", source_db="onboardhospitality", source_act_id=uuid.uuid4().hex[:12])
    db_session.add_all([company, caterer])
    last = SalesEdition(id=uuid.uuid4(), title_id=obh.id, year=Y - 1, name="101", kind="issue", edition_date=TODAY + timedelta(days=40) - timedelta(days=364))
    prev = SalesEdition(id=uuid.uuid4(), title_id=obh.id, year=Y, name="104", kind="issue", edition_date=TODAY - timedelta(days=60))
    nxt = SalesEdition(id=uuid.uuid4(), title_id=obh.id, year=Y, name="105", kind="issue", edition_date=TODAY + timedelta(days=40),
                       ad_deadline=TODAY + timedelta(days=7), theme="Sustainability")
    later = SalesEdition(id=uuid.uuid4(), title_id=obh.id, year=Y, name="106", kind="issue", edition_date=TODAY + timedelta(days=120),
                         ad_deadline=TODAY + timedelta(days=100))
    db_session.add_all([last, prev, nxt, later])
    db_session.flush()
    db_session.add_all([
        EditionFeature(id=uuid.uuid4(), edition_id=nxt.id, title="Catering trends", sponsorable=True, sort_order=1),
        EditionFeature(id=uuid.uuid4(), edition_id=nxt.id, title="Seat design", sort_order=2),
        SalesOrder(id=uuid.uuid4(), edition_id=last.id, client_name="Delta Air Lines", company_id=company.id, value_gbp=4200, size="FP",
                   booked_on=TODAY - timedelta(days=400)),
        SalesOrder(id=uuid.uuid4(), edition_id=prev.id, client_name="Gate Foods", company_id=caterer.id, value_gbp=1500, size="HP",
                   booked_on=TODAY - timedelta(days=90)),
    ])
    fp = SalesRate(id=uuid.uuid4(), title_id=obh.id, year=Y, section="print", product="Full page", price_gbp=3000)
    db_session.add(fp)
    db_session.add(RateOffer(id=uuid.uuid4(), brand="obh", year=Y, kind="volume", label="Book 2 adverts, save 10%", section="print",
                             rules={"tiers": [{"qty": 2, "discount_pct": 10}]}))
    db_session.flush()
    rep = make_user(db_session, role="sales")
    return {"obh": obh, "company": company, "caterer": caterer, "last": last, "prev": prev, "next": nxt, "later": later, "fp": fp,
            "rep": rep, "h": identity_headers(rep), "admin": identity_headers(make_user(db_session, role="admin"))}


def _create(client, w, **kw):
    body = {"company_id": str(w["company"].id), "title_id": str(w["obh"].id), "use_ai": False,
            "lines": [{"product": "Full page", "qty": 2, "source": "rate_card", "rate_id": str(w["fp"].id)},
                      {"product": "Sneaky discount", "qty": 1, "unit_price": 5, "source": "offer"}], **kw}
    return client.post("/api/proposals", json=body, headers=w["h"])


def test_proposal_picks_next_issue_and_applies_offer(client, world):
    r = _create(client, world)
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["edition_id"] == str(world["next"].id) and p["issue"]["label"] == "Issue 105"
    assert any(f.startswith("We picked Issue 105") for f in p["flags"])
    offers = [ln for ln in p["lines"] if ln["source"] == "offer"]
    assert len(offers) == 1 and offers[0]["unit_price"] == -600 and "Sneaky" not in str(p["lines"])
    assert p["total_gbp"] == 5400
    proposal = next(s for s in p["sections"] if s["kind"] == "proposal")["body"]
    assert "Issue 105 publishes on" in proposal and "Catering trends" in proposal and "Book 2 adverts" in proposal
    nxt = next(s for s in p["sections"] if s["kind"] == "next_steps")["body"]
    assert "Copy and artwork are needed by" in nxt
    d = client.get(f"/api/proposals/{p['id']}/download", headers=world["h"])
    text = "\n".join(par.text for par in docx.Document(io.BytesIO(d.content)).paragraphs)
    assert "-£600.00" in text and "Total: £5,400.00" in text

    # one advert -> the offer drops off
    r = client.patch(f"/api/proposals/{p['id']}", json={"lines": [{"product": "Full page", "qty": 1, "source": "rate_card", "rate_id": str(world["fp"].id)}]},
                     headers=world["h"])
    assert [ln["source"] for ln in r.json()["lines"]] == ["rate_card"] and r.json()["total_gbp"] == 3000


def test_proposal_issue_choice(client, db_session, world):
    p = _create(client, world, edition_id=str(world["later"].id)).json()
    assert p["issue"]["label"] == "Issue 106" and not any(f.startswith("We picked") for f in p["flags"])
    r = client.patch(f"/api/proposals/{p['id']}", json={"edition_id": str(world["next"].id)}, headers=world["h"])
    assert r.json()["issue"]["label"] == "Issue 105"
    stm = db_session.query(SalesTitle).filter_by(slug="selling-travel").one()
    other = SalesEdition(id=uuid.uuid4(), title_id=stm.id, year=Y, name="Winter", kind="issue", edition_date=TODAY + timedelta(days=30))
    db_session.add(other)
    db_session.flush()
    assert _create(client, world, edition_id=str(other.id)).status_code == 422
    up = client.get(f"/api/editorial/upcoming?title_id={world['obh'].id}", headers=world["h"]).json()
    assert [u["label"] for u in up] == ["Issue 105", "Issue 106"] and up[0]["suggested"]


def test_who_to_pitch(client, db_session, world):
    r = client.get(f"/api/editorial/issues/{world['next'].id}/pitch", headers=world["h"]).json()
    assert [c["name"] for c in r["lapsed"]] == ["Delta Air Lines"] and r["compared_with"]["label"] == "Issue 101"
    assert [c["name"] for c in r["previous"]] == ["Gate Foods"]
    assert r["feature_matches"] == []  # Gate Foods is already listed once
    # once Delta rebooks, it drops off the list
    db_session.add(SalesOrder(id=uuid.uuid4(), edition_id=world["next"].id, client_name="Delta Air Lines", company_id=world["company"].id, value_gbp=4000))
    db_session.flush()
    r = client.get(f"/api/editorial/issues/{world['next'].id}/pitch", headers=world["h"]).json()
    assert r["lapsed"] == [] and r["already_booked"] == 1
    # a past advertiser from an older issue whose business fits a feature
    older = SalesEdition(id=uuid.uuid4(), title_id=world["obh"].id, year=Y - 2, name="97", kind="issue", edition_date=TODAY - timedelta(days=700))
    db_session.add(older)
    db_session.flush()
    fresh = Company(id=uuid.uuid4(), name="SkyChef", industry="Catering", source_db="onboardhospitality", source_act_id=uuid.uuid4().hex[:12])
    db_session.add(fresh)
    db_session.flush()
    db_session.add(SalesOrder(id=uuid.uuid4(), edition_id=older.id, client_name="SkyChef", company_id=fresh.id, value_gbp=900))
    db_session.flush()
    r = client.get(f"/api/editorial/issues/{world['next'].id}/pitch", headers=world["h"]).json()
    assert [(c["name"], c["reason"]) for c in r["feature_matches"]] == [("SkyChef", "Fits the feature “Catering trends”")]


def test_renewal_offers_this_years_issue(db_session, world):
    order = db_session.query(SalesOrder).filter_by(edition_id=world["last"].id).one()
    facts = _renewal_facts(db_session, world["obh"], world["last"], order, Y)
    assert facts["issue"]["label"] == "Issue 105"
    assert facts["issue_text"].startswith("Issue 105 publishes on") and "It features Catering trends." in facts["issue_text"]


def test_deadline_reminders(db_session, world):
    sw = db_session.query(SalesRep).filter_by(code="SW").one()  # an OBH publisher
    sw.user_id = world["rep"].id
    db_session.add(AutomationSetting(key="editorial_deadline_alert_days", value={"v": "7,1"}))
    db_session.flush()
    assert editorial_deadlines.remind(db_session, TODAY) == 1
    n = db_session.query(Notification).filter_by(user_id=world["rep"].id, kind="editorial_deadline").one()
    assert "Issue 105: advertising deadline in 7 days" in n.title and "1 of last year's advertisers" in n.body
    assert n.link == f"/editorial/issues/{world['next'].id}"
    assert editorial_deadlines.remind(db_session, TODAY) == 0  # once only
