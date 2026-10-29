"""Brevo: unsubscribes kept in step both ways, and clients spotted in the newsletters (app/automations/brevo_sync.py)."""
import uuid
from datetime import date, datetime, timezone

import httpx

from tests.conftest import identity_headers, make_user
from tests.test_sales_orders import _NoCloseSession

from app.automations import brevo_sync as bs
from app.automations import runtime_settings
from app.automations import subscription_changes as sc
from app.core.config import settings
from app.models import (Company, Contact, Email, FieldChange, Group, GroupMembership, Note, ReviewQueueItem, SalesEdition, SalesOrder,
                        SalesRep, SalesTitle)
from app.sales.reference import ensure_reference_data
from app.services import brevo
from tests.test_subscription_changes import _msg


def _person(db, name, email, source_db="sellingtravel", company=None, title=None):
    c = Contact(id=uuid.uuid4(), source_db=source_db, source_act_id=uuid.uuid4().hex, full_name=name, first_name=name.split()[0],
                job_title=title, company_id=company.id if company else None, custom_fields={})
    db.add(c)
    db.flush()
    db.add(Email(id=uuid.uuid4(), source_db=source_db, source_act_id=uuid.uuid4().hex, contact_id=c.id, address=email, is_primary=True))
    db.flush()
    return c


def _settings(monkeypatch, **values):
    real_bool, real_csv = runtime_settings.get_bool, runtime_settings.get_csv
    monkeypatch.setattr(runtime_settings, "get_bool", lambda db, k: values[k] if k in values else real_bool(db, k))
    monkeypatch.setattr(runtime_settings, "get_csv", lambda db, k: values[k] if k in values else real_csv(db, k))


def test_the_brevo_calls(monkeypatch):
    sent = []

    def fake(method, url, **kw):
        sent.append((method, url, kw.get("json"), kw.get("params"), kw["headers"]["api-key"]))
        if "nobody" in url:
            return httpx.Response(404)
        if url.endswith("/contacts"):
            return httpx.Response(200, json={"contacts": [{"email": "a@x.example", "emailBlacklisted": True}], "count": 1})
        return httpx.Response(204)
    monkeypatch.setattr(settings, "brevo_api_key", "test-key")
    monkeypatch.setattr(httpx, "request", fake)
    assert brevo.update_contact("jo+news@agency.example", blacklist=True)
    assert sent[-1][:3] == ("PUT", "https://api.brevo.com/v3/contacts/jo%2Bnews%40agency.example", {"emailBlacklisted": True})
    assert sent[-1][4] == "test-key"
    assert brevo.update_contact("j@x.example", remove_from=[12])
    assert sent[-1][2] == {"unlinkListIds": [12]}
    assert not brevo.update_contact("nobody@x.example", blacklist=True)        # not in Brevo: nothing to do
    people, carry_on = brevo.contacts_changed_since(datetime(2026, 10, 1, tzinfo=timezone.utc))
    assert people[0]["emailBlacklisted"] and carry_on == 0 and sent[-1][3]["modifiedSince"] == "2026-10-01T00:00:00.000Z"
    monkeypatch.setattr(httpx, "request", lambda *a, **k: httpx.Response(401))
    try:
        brevo.update_contact("j@x.example", blacklist=True)
        raise AssertionError("should have refused")
    except brevo.BrevoError as exc:
        assert "didn't accept BMI Brain's key" in str(exc)
    monkeypatch.setattr(settings, "brevo_api_key", "")
    assert not brevo.configured()


def test_unsubscribes_go_to_brevo_and_come_back(client, db_session, monkeypatch):
    jo = _person(db_session, "Jo Bloggs", "jo@agency.example")
    calls = []
    monkeypatch.setattr(settings, "brevo_api_key", "test-key")
    monkeypatch.setattr(brevo, "update_contact", lambda email, blacklist=False, remove_from=None: calls.append((email, blacklist, remove_from)) or True)
    _settings(monkeypatch, automations_brevo_unsubscribes_enabled=True, brevo_title_lists=["sellingtravel:12", "prospects:7"])
    h = identity_headers(make_user(db_session, role="admin"))

    item = sc.queue(db_session, "enquiries@bmipublishing.co.uk", _msg("Unsubscribe me"),
                    {"kind": "unsubscribe", "magazine": "Selling Travel"})
    db_session.commit()
    r = client.post(f"/api/review-queue/{item.id}/actions/unsubscribe", json={"fields": {"email": "jo@agency.example"}}, headers=h)
    assert r.status_code == 200, r.text
    assert calls == [("jo@agency.example", False, [12])]                       # off Selling Travel's list only
    db_session.refresh(item)
    assert any(d["label"] == "Brevo" and "Brevo list too" in d["value"] for d in item.payload["details"])

    # Brevo's own unsubscribes come back: blacklisted everywhere, or off one title's list
    db_session.add(Group(id=uuid.uuid4(), source_db="sellingtravel", source_act_id="g", name="Full Export Email Only"))
    db_session.flush()
    kim = _person(db_session, "Kim Lee", "kim@tmc.example")
    g = db_session.query(Group).filter_by(name="Full Export Email Only").one()
    db_session.add(GroupMembership(id=uuid.uuid4(), group_id=g.id, contact_id=kim.id))
    db_session.commit()
    monkeypatch.setattr(bs, "SessionLocal", lambda: _NoCloseSession(db_session))
    monkeypatch.setattr(brevo, "contacts_changed_since", lambda since, offset=0: ([
        {"email": "JO@agency.example", "emailBlacklisted": True},
        {"email": "kim@tmc.example", "emailBlacklisted": False, "listUnsubscribed": [12]},
        {"email": "stranger@x.example", "emailBlacklisted": True}], 0))
    bs.sync_unsubscribes()
    db_session.refresh(jo)
    db_session.refresh(kim)
    assert jo.is_unsubscribed and not kim.is_unsubscribed
    assert db_session.query(FieldChange).filter_by(entity_id=jo.id, field="is_unsubscribed").count() == 1
    assert db_session.query(GroupMembership).filter_by(contact_id=kim.id).count() == 0
    assert db_session.query(Note).filter_by(entity_id=kim.id, note_type="Subscription").count() == 1


def test_when_brevo_isnt_connected_the_card_says_so(db_session, monkeypatch):
    monkeypatch.setattr(settings, "brevo_api_key", "")
    jo = _person(db_session, "Jo Bloggs", "jo@agency.example")
    assert "by hand" in bs.push_unsubscribe(db_session, [jo], everything=True, source_db=None)
    monkeypatch.setattr(settings, "brevo_api_key", "k")
    _settings(monkeypatch, automations_brevo_unsubscribes_enabled=True, brevo_title_lists=[])
    assert "no Brevo list is set" in bs.push_unsubscribe(db_session, [jo], everything=False, source_db="sellingtravel")
    monkeypatch.setattr(brevo, "update_contact", lambda *a, **k: (_ for _ in ()).throw(brevo.BrevoError("Brevo couldn't be reached just now.")))
    assert "by hand" in bs.push_unsubscribe(db_session, [jo], everything=True, source_db=None)


def test_clients_in_a_newsletter(client, db_session, monkeypatch):
    ensure_reference_data(db_session)
    sally = make_user(db_session, role="sales", name="Sally")
    rep = SalesRep(id=uuid.uuid4(), code="ZB", name="Sally", user_id=sally.id, active=True)
    db_session.add(rep)
    t = db_session.query(SalesTitle).filter_by(slug="obh").one()
    ed = SalesEdition(id=uuid.uuid4(), title_id=t.id, year=date.today().year, name="T9", edition_date=date.today())
    gg = Company(id=uuid.uuid4(), source_db="onboard", source_act_id=uuid.uuid4().hex, name="Gate Gourmet Ltd")
    old = Company(id=uuid.uuid4(), source_db="onboard", source_act_id=uuid.uuid4().hex, name="Ancient Airways")
    tiny = Company(id=uuid.uuid4(), source_db="onboard", source_act_id=uuid.uuid4().hex, name="Sky")
    db_session.add_all([ed, gg, old, tiny])
    db_session.flush()
    db_session.add_all([SalesOrder(id=uuid.uuid4(), edition_id=ed.id, client_name="Gate Gourmet", company_id=gg.id, rep_id=rep.id, booked_on=date.today()),
                        SalesOrder(id=uuid.uuid4(), edition_id=ed.id, client_name="Sky", company_id=tiny.id, rep_id=rep.id, booked_on=date.today()),
                        SalesOrder(id=uuid.uuid4(), edition_id=ed.id, client_name="Ancient", company_id=old.id, rep_id=rep.id, booked_on=date(2019, 1, 1))])
    mo = _person(db_session, "Mo King", "mo@gg.example", "onboard", gg, "Marketing Manager")
    db_session.commit()
    campaign = {"id": 501, "subject": "OBH Weekly: new menus take off", "sentDate": "2026-10-29T08:00:00.000Z",
                "shareLink": "https://sendibt.example/abc",
                "htmlContent": "<p>This week <b>Gate Gourmet</b> launched a menu. Ancient Airways too. The sky is blue.</p><style>.sky{}</style>"}
    assert [c.name for c in bs.clients_in(db_session, bs._text(campaign["htmlContent"]))] == ["Gate Gourmet Ltd"]   # not a past client, not a short name

    monkeypatch.setattr(settings, "brevo_api_key", "k")
    monkeypatch.setattr(bs, "SessionLocal", lambda: _NoCloseSession(db_session))
    monkeypatch.setattr(brevo, "sent_campaigns", lambda start, end: [campaign])
    bs.scan_coverage()
    bs.scan_coverage()   # the same newsletter isn't read twice
    card = db_session.query(ReviewQueueItem).filter_by(kind="newsletter_coverage").one()
    p = card.payload
    assert p["owner_user_id"] == str(sally.id) and p["merge"]["contact_ids"] == [str(mo.id)]
    assert "https://sendibt.example/abc" in p["merge"]["body"] and "{{company}}" in p["merge"]["body"]
    assert any(d.get("href") == f"/companies/{gg.id}" for d in p["details"])
    r = client.post(f"/api/review-queue/{card.id}/actions/open_merge", json={}, headers=identity_headers(sally, access=[("onboard", None)]))
    assert r.status_code == 200 and r.json()["payload"]["open_href"] == f"/mail-merge?review={card.id}"
