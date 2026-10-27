"""Subscription sign-ups from the Wufoo, Elementor and Stova subscribe forms (app/automations/subscription_forms.py)."""
import json
import uuid

from tests.conftest import identity_headers, make_user

from app.automations import subscription_forms as sf
from app.models import Contact, Email, Group, GroupMembership, ReviewQueueItem

WUFOO_STRUCTURE = {"Fields": [
    {"ID": "Field1", "Title": "Name", "SubFields": [{"ID": "Field1", "Label": "First"}, {"ID": "Field2", "Label": "Last"}]},
    {"ID": "Field3", "Title": "Email"},
    {"ID": "Field4", "Title": "Company"},
    {"ID": "Field5", "Title": "Job title"},
    {"ID": "Field6", "Title": "Country"},
    {"ID": "Field7", "Title": "Would you like print or digital?"},
]}


def _wufoo(email="jo@gmail.com", country="Spain", entry="17"):
    return {"Field1": "Jo", "Field2": "Bloggs", "Field3": email, "Field4": "Sun Holidays", "Field5": "Agent", "Field6": country,
            "Field7": "Print", "FieldStructure": json.dumps(WUFOO_STRUCTURE), "EntryId": entry, "HandshakeKey": ""}


def test_reading_wufoo_elementor_and_json():
    ref, answers = sf.parse("application/x-www-form-urlencoded", b"", _wufoo())
    assert ref == "17" and answers["Name (First)"] == "Jo" and answers["Email"] == "jo@gmail.com"
    g = sf.guess(answers)
    assert g["name"] == "Jo Bloggs" and g["company"] == "Sun Holidays" and g["job_title"] == "Agent" and g["country"] == "Spain"
    # Elementor, simple and with Advanced data on
    _, simple = sf.parse("application/x-www-form-urlencoded", b"", {"Name": "Ali Khan", "Email": "ali@air.example", "form_id": "a1", "form_name": "Subscribe"})
    assert simple == {"Name": "Ali Khan", "Email": "ali@air.example"}
    _, adv = sf.parse("application/x-www-form-urlencoded", b"", {"fields[name][title]": "Name", "fields[name][value]": "Ali Khan",
                                                                 "fields[email][title]": "Email", "fields[email][value]": "ali@air.example",
                                                                 "form[id]": "a1", "meta[date][value]": "today"})
    assert adv == {"Name": "Ali Khan", "Email": "ali@air.example"}
    assert sf.parse("application/json", json.dumps({"entry_id": "s-9", "answers": {"Email": "x@y.example"}}).encode()) == ("s-9", {"Email": "x@y.example"})


def test_signups_arrive_checked_and_can_be_added(client, db_session):
    admin = make_user(db_session, role="admin")
    h = identity_headers(admin)
    forms = client.get("/api/subscription-forms", headers=h).json()
    assert [f["key"] for f in forms] == ["selling-travel", "tbtm", "obh-digital", "obh-print"]
    st = next(f for f in forms if f["key"] == "selling-travel")
    token = st["address"].rsplit("/", 1)[1]
    assert client.get("/api/subscription-forms", headers=identity_headers(make_user(db_session, role="sales"))).status_code == 403

    # an overseas reader asking for print, with a personal address
    r = client.post(f"/api/subscription-forms/receive/selling-travel/{token}", data=_wufoo(), headers=h)
    assert r.json() == {"ok": True, "queued": True}
    assert not client.post(f"/api/subscription-forms/receive/selling-travel/{token}", data=_wufoo(), headers=h).json()["queued"]   # sent twice
    assert client.post("/api/subscription-forms/receive/selling-travel/wrong-token-123", data=_wufoo(), headers=h).status_code == 404
    item = db_session.query(ReviewQueueItem).filter_by(kind="subscription_signup").one()
    notes = item.payload["checks"]
    assert any(n.startswith("Personal email address") for n in notes)
    assert any("only posts to UK addresses" in n for n in notes)
    assert item.payload["facets"] == {"form": "Selling Travel", "check": "Overseas, print"}

    db_session.add(Group(id=uuid.uuid4(), source_db="sellingtravel", source_act_id="g-1", name="Full Export Email Only"))
    db_session.flush()
    r = client.post(f"/api/review-queue/{item.id}/actions/add", json={"fields": {"name": "Jo Bloggs", "newsletter": "true"}}, headers=h)
    assert r.status_code == 200, r.text
    contact = db_session.query(Contact).filter_by(full_name="Jo Bloggs").one()
    assert contact.source_db == "sellingtravel" and contact.job_title == "Agent"
    assert db_session.query(Email).filter_by(contact_id=contact.id, address="jo@gmail.com").count() == 1
    assert db_session.query(GroupMembership).filter_by(contact_id=contact.id).count() == 1

    # the same person signing up again is flagged as already on the database, and can't be added twice
    client.post(f"/api/subscription-forms/receive/selling-travel/{token}", data=_wufoo(entry="18", country="UK"), headers=h)
    again = db_session.query(ReviewQueueItem).filter_by(kind="subscription_signup", status="pending").one()
    assert again.payload["facets"]["check"] == "Already on the database" and again.payload["contact_id"] == str(contact.id)
    r = client.post(f"/api/review-queue/{again.id}/actions/add", json={"fields": {"name": "Jo Bloggs"}}, headers=h)
    assert r.status_code == 400 and "Already on file" in r.json()["detail"]
