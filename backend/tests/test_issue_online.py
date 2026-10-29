"""SALES-003: new issues on BMI's Issuu page, matched to their issue, and the advertisers told (app/automations/issue_online.py)."""
import uuid
from datetime import date, timedelta

from tests.conftest import identity_headers, make_user
from tests.test_sales_orders import _NoCloseSession

from app.automations import issue_online as io
from app.models import Company, Contact, Email, FieldChange, ReviewQueueItem, SalesEdition, SalesOrder, SalesRep, SalesTitle
from app.sales.reference import ensure_reference_data

TODAY = date.today()


def _card(slug, title, when):
    return (f'<li><div data-testid="publication-card" class="x"><a href="/bmipublishingltd/docs/{slug}" class="y"><div><img alt="" src="t.jpg"/></div>'
            f'<div><p class="z" data-testid="publication-card-title" lang="en">{title}</p></div></a><div class="d">{when:%B %-d, %Y}</div>'
            '<div>by <a href="/bmipublishingltd">BMI Publishing Ltd</a></div></div></li>')


def _issues(db):
    ensure_reference_data(db)
    obh = db.query(SalesTitle).filter_by(slug="obh").one()
    st = db.query(SalesTitle).filter_by(slug="selling-travel").one()
    e107 = SalesEdition(id=uuid.uuid4(), title_id=obh.id, year=TODAY.year, name="107", kind="issue", edition_date=TODAY - timedelta(days=5))
    e106 = SalesEdition(id=uuid.uuid4(), title_id=obh.id, year=TODAY.year, name="106", kind="issue", edition_date=TODAY - timedelta(days=70))
    est = SalesEdition(id=uuid.uuid4(), title_id=st.id, year=TODAY.year, name=f"{TODAY:%B} {TODAY.year}", kind="issue", edition_date=TODAY)
    db.add_all([e107, e106, est])
    db.flush()
    return e107, e106, est


def test_reading_issuu_and_matching_the_issue(db_session):
    e107, e106, est = _issues(db_session)
    page = "".join([_card("obh-107", "﻿Onboard Hospitality 107 2026", TODAY), _card("pittsburgh_guide_2026", "Pittsburgh Guide 2026", TODAY),
                    _card("obh_awards_2026", "OBH Awards 2026", TODAY), _card("st", f"Selling Travel {TODAY:%B} {TODAY.year}", TODAY)])
    pubs = io.parse_profile(page)
    assert [p["title"] for p in pubs] == ["Onboard Hospitality 107 2026", "Pittsburgh Guide 2026", "OBH Awards 2026", f"Selling Travel {TODAY:%B} {TODAY.year}"]
    assert pubs[0]["url"] == "https://issuu.com/bmipublishingltd/docs/obh-107" and pubs[0]["published"] == TODAY
    assert io.candidates(db_session, pubs[0])[0][1].id == e107.id        # the issue number
    assert io.candidates(db_session, pubs[1]) == []                     # a guide that isn't in the plan
    assert io.candidates(db_session, pubs[2]) == []                     # the awards aren't an ordinary issue
    assert io.candidates(db_session, pubs[3])[0][1].id == est.id         # the magazine's name and the month


def test_linking_an_issue_and_telling_the_advertisers(client, db_session, monkeypatch):
    e107, _, _ = _issues(db_session)
    sally = make_user(db_session, role="sales", name="Sally")
    rep = SalesRep(id=uuid.uuid4(), code="ZQ", name="Sally", user_id=sally.id, active=True)
    db_session.add(rep)
    co = Company(id=uuid.uuid4(), source_db="onboard", source_act_id=uuid.uuid4().hex, name="Gate Gourmet")
    db_session.add(co)
    db_session.flush()
    pr = Contact(id=uuid.uuid4(), source_db="onboard", source_act_id=uuid.uuid4().hex, full_name="Pat Reed", job_title="PR", company_id=co.id, custom_fields={})
    mk = Contact(id=uuid.uuid4(), source_db="onboard", source_act_id=uuid.uuid4().hex, full_name="Mo King", job_title="Marketing Manager", company_id=co.id, custom_fields={})
    db_session.add_all([pr, mk])
    db_session.flush()
    for c in (pr, mk):
        db_session.add(Email(id=uuid.uuid4(), source_db="onboard", source_act_id=uuid.uuid4().hex, contact_id=c.id, address=f"{c.id.hex[:6]}@gg.example"))
    db_session.add_all([SalesOrder(id=uuid.uuid4(), edition_id=e107.id, client_name="Gate Gourmet", company_id=co.id, rep_id=rep.id, status="booked"),
                        SalesOrder(id=uuid.uuid4(), edition_id=e107.id, client_name="No Contact Ltd", rep_id=rep.id, status="booked"),
                        SalesOrder(id=uuid.uuid4(), edition_id=e107.id, client_name="Gone Ltd", company_id=co.id, rep_id=rep.id, status="cancelled")])
    db_session.commit()

    monkeypatch.setattr(io, "SessionLocal", lambda: _NoCloseSession(db_session))
    monkeypatch.setattr(io, "fetch", lambda url: io.parse_profile(_card("obh-107", "Onboard Hospitality 107 2026", TODAY)
                                                                  + _card("old", "Onboard Hospitality 100", TODAY - timedelta(days=400))))
    io.scan()
    io.scan()   # the same publication isn't brought up twice
    item = db_session.query(ReviewQueueItem).filter_by(kind="issue_online").one()          # the old one is left alone
    p = item.payload
    assert p["field_defaults"]["edition_id"] == str(e107.id) and p["facets"]["match"] == "Sure match"
    assert any(d.get("href") == "https://issuu.com/bmipublishingltd/docs/obh-107" for d in p["details"])
    assert any(d.get("href") == f"/sales/editions/{e107.id}" for d in p["details"])

    h = identity_headers(make_user(db_session, role="admin"))
    r = client.post(f"/api/review-queue/{item.id}/actions/link", json={"fields": {"edition_id": str(e107.id)}}, headers=h)
    assert r.status_code == 200, r.text
    db_session.refresh(e107)
    assert e107.digital_url == "https://issuu.com/bmipublishingltd/docs/obh-107"
    assert db_session.query(FieldChange).filter_by(entity_id=e107.id, field="digital_url").count() == 1

    notes = db_session.query(ReviewQueueItem).filter_by(kind="issue_live_notes").one()
    n = notes.payload
    assert n["owner_user_id"] == str(sally.id) and n["merge"]["contact_ids"] == [str(mk.id)]     # marketing, not PR; cancelled left out
    assert "obh-107" in n["merge"]["body"] and "{{salutation|colleague}}" in n["merge"]["body"]
    assert any(d["label"] == "No one to email at" and "No Contact Ltd" in d["value"] for d in n["details"])
    r = client.post(f"/api/review-queue/{notes.id}/actions/open_merge", json={}, headers=identity_headers(sally, access=[("onboard", None)]))
    assert r.status_code == 200 and r.json()["payload"]["open_href"] == f"/mail-merge?review={notes.id}"
    # another salesperson doesn't see Sally's advertisers
    other = make_user(db_session, role="sales")
    seen = client.get("/api/review-queue?kind=issue_live_notes", headers=identity_headers(other, access=[("onboard", None)])).json()["items"]
    assert not seen
