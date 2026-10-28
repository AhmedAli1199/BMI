"""Subscription changes and reader questions from the subscriptions inbox (app/automations/subscription_changes.py)."""
import uuid
from datetime import datetime, timezone

from tests.conftest import identity_headers, make_user

from app.automations import subscription_changes as sc
from app.automations.mail_parsing import ParsedMessage
from app.models import Address, Contact, Email, FieldChange, Group, GroupMembership, Note, ReviewQueueItem

BOX = "enquiries@bmipublishing.co.uk"


def _msg(body, subject="Subscription", sender="jo@agency.example", name="Jo Bloggs", mid=None):
    return ParsedMessage(message_id=mid or uuid.uuid4().hex, internet_message_id=None, from_address=sender, from_name=name,
                         subject=subject, received_at=datetime(2026, 10, 27, 9, tzinfo=timezone.utc), body_text=body)


def _reader(db, source_db="sellingtravel", email="jo@agency.example", name="Jo Bloggs"):
    c = Contact(id=uuid.uuid4(), source_db=source_db, source_act_id=uuid.uuid4().hex, full_name=name, first_name=name.split()[0],
                custom_fields={})
    db.add(c)
    db.flush()
    db.add(Email(id=uuid.uuid4(), source_db=source_db, source_act_id=uuid.uuid4().hex, contact_id=c.id, address=email, is_primary=True))
    g = db.query(Group).filter_by(source_db=source_db).first() or Group(
        id=uuid.uuid4(), source_db=source_db, source_act_id=uuid.uuid4().hex, name=sc.NEWSLETTER_GROUP[source_db])
    db.add(g)
    db.flush()
    db.add(GroupMembership(id=uuid.uuid4(), group_id=g.id, contact_id=c.id))
    db.flush()
    return c


def test_which_emails_are_read():
    domains = {"bmipublishing.co.uk"}
    assert sc.candidate(_msg("Please unsubscribe me from Selling Travel."), BOX, domains)
    assert sc.candidate(_msg("We've moved - our new address is 1 High St, Leeds LS1 1AA."), BOX, domains)
    assert not sc.candidate(_msg("Lovely to meet you yesterday.", subject="Hello"), BOX, domains)                         # nothing about a subscription
    assert not sc.candidate(_msg("Please unsubscribe me", sender="kim@bmipublishing.co.uk"), BOX, domains)   # a colleague
    assert not sc.candidate(_msg("unsubscribe", sender="noreply@mailer.example"), BOX, domains)           # automatic
    # without the Brain only a plain unsubscribe is queued, marked as not checked
    assert sc.classify(_msg("Please take me off your list.")) ["kind"] == "unsubscribe"
    assert sc.classify(_msg("My copy hasn't arrived this month.")) is None
    assert sc.title_key("the TBTM newsletter") == "prospects" and sc.title_key("Onboard Hospitality") == "onboard"


def test_unsubscribe_from_one_title_or_everything(client, db_session):
    h = identity_headers(make_user(db_session, role="admin"))
    jo = _reader(db_session)
    jo_tbtm = _reader(db_session, source_db="prospects")
    item = sc.queue(db_session, BOX, _msg("Please unsubscribe me from Selling Travel"),
                    {"kind": "unsubscribe", "magazine": "Selling Travel", "summary": "Wants to stop Selling Travel."})
    db_session.flush()
    p = item.payload
    assert item.kind == "subscription_change" and p["primary_action"] == "unsubscribe"
    assert "update_address" in p["hidden_actions"] and "unsubscribe" not in p["hidden_actions"]
    assert p["facets"] == {"change": "Unsubscribe", "magazine": "Selling Travel", "record": "On the database"}
    assert p["contact_id"] == str(jo.id) and any(d.get("href") == f"/contacts/{jo.id}" for d in p["details"])
    assert p["field_defaults"]["email"] == "jo@agency.example"

    r = client.post(f"/api/review-queue/{item.id}/actions/unsubscribe", json={"fields": {"email": "jo@agency.example", "everything": "false"}}, headers=h)
    assert r.status_code == 200, r.text
    assert db_session.query(GroupMembership).filter_by(contact_id=jo.id).count() == 0
    assert db_session.query(GroupMembership).filter_by(contact_id=jo_tbtm.id).count() == 1     # other title untouched
    assert not jo.is_unsubscribed

    again = sc.queue(db_session, BOX, _msg("Stop sending me everything"), {"kind": "unsubscribe", "everything": True, "magazine": None})
    db_session.flush()
    assert again.payload["field_defaults"]["everything"] == "true"
    r = client.post(f"/api/review-queue/{again.id}/actions/unsubscribe", json={"fields": {"email": "jo@agency.example", "everything": "true"}}, headers=h)
    assert r.status_code == 200, r.text
    db_session.refresh(jo_tbtm)
    assert jo_tbtm.is_unsubscribed and db_session.query(GroupMembership).filter_by(contact_id=jo_tbtm.id).count() == 0
    assert db_session.query(FieldChange).filter_by(entity_id=jo_tbtm.id, field="is_unsubscribed").count() == 1

    # an address nobody has on file is refused plainly
    third = sc.queue(db_session, BOX, _msg("unsubscribe", sender="new@else.example"), {"kind": "unsubscribe", "magazine": "Selling Travel"})
    db_session.flush()
    assert third.payload["facets"]["record"] == "Not found"
    r = client.post(f"/api/review-queue/{third.id}/actions/unsubscribe", json={"fields": {"email": "new@else.example"}}, headers=h)
    assert r.status_code == 400 and "No one on the database" in r.json()["detail"]


def test_address_details_subscribe_and_reader_questions(client, db_session):
    h = identity_headers(make_user(db_session, role="admin"))
    jo = _reader(db_session)
    item = sc.queue(db_session, BOX, _msg("We've moved office"), {"kind": "change_address", "magazine": "Selling Travel",
                    "new_address": {"line1": "1 High St", "city": "Leeds", "postcode": "LS1 1AA", "country": "UK"}})
    db_session.flush()
    assert item.payload["field_defaults"]["postcode"] == "LS1 1AA" and item.payload["primary_action"] == "update_address"
    r = client.post(f"/api/review-queue/{item.id}/actions/update_address", json={"fields": {
        "email": "jo@agency.example", "line1": "1 High St", "city": "Leeds", "postcode": "LS1 1AA", "country": "UK"}}, headers=h)
    assert r.status_code == 200, r.text
    addr = db_session.query(Address).filter_by(contact_id=jo.id).one()
    assert addr.postal_code == "LS1 1AA" and addr.city == "Leeds"
    assert db_session.query(FieldChange).filter_by(entity_id=jo.id, field="address_postal_code").count() == 1

    item = sc.queue(db_session, BOX, _msg("I've a new job"), {"kind": "change_details", "magazine": "Selling Travel",
                    "new_details": {"job_title": "Head of Sales"}})
    db_session.flush()
    r = client.post(f"/api/review-queue/{item.id}/actions/update_details", json={"fields": {
        "email": "jo@agency.example", "job_title": "Head of Sales", "new_email": "jo@newjob.example"}}, headers=h)
    assert r.status_code == 200, r.text
    db_session.refresh(jo)
    assert jo.job_title == "Head of Sales"
    assert db_session.query(Email).filter_by(contact_id=jo.id).one().address == "jo@newjob.example"

    # someone new subscribing is added to the title's database and newsletter group
    db_session.add(Group(id=uuid.uuid4(), source_db="prospects", source_act_id="g-2", name=sc.NEWSLETTER_GROUP["prospects"]))
    db_session.flush()
    item = sc.queue(db_session, BOX, _msg("Please add me to TBTM", sender="sam@tmc.example", name="Sam Lee"),
                    {"kind": "subscribe", "magazine": "The Business Travel Magazine"})
    db_session.flush()
    r = client.post(f"/api/review-queue/{item.id}/actions/subscribe", json={"fields": {"email": "sam@tmc.example", "name": "Sam Lee"}}, headers=h)
    assert r.status_code == 200, r.text
    sam = db_session.query(Contact).filter_by(full_name="Sam Lee").one()
    assert sam.source_db == "prospects" and db_session.query(GroupMembership).filter_by(contact_id=sam.id).count() == 1
    assert db_session.query(Note).filter_by(entity_id=sam.id, note_type="Subscription").count() == 1

    # a change with no button of its own is noted on the record
    item = sc.queue(db_session, BOX, _msg("Can I have the digital edition instead?"), {"kind": "format", "magazine": "Selling Travel", "format": "digital"})
    db_session.flush()
    assert item.payload["primary_action"] == "noted"
    assert client.post(f"/api/review-queue/{item.id}/actions/noted", json={"fields": {"email": "jo@newjob.example"}}, headers=h).status_code == 200
    assert any("digital edition" in n.body for n in db_session.query(Note).filter_by(entity_id=jo.id))

    # a question gets a drafted reply; sending needs Outlook connected, said plainly
    q = sc.queue(db_session, BOX, _msg("My copy of Selling Travel hasn't arrived", subject="Missing copy", sender="jo@newjob.example"),
                 {"kind": "reader_query", "magazine": "Selling Travel"})
    db_session.commit()
    assert q.kind == "reader_query" and q.payload["suggested_to"] == "jo@newjob.example"
    assert q.payload["original_text"].startswith("Subject: RE: Missing copy") and "Dear Jo" in q.payload["original_text"]
    r = client.post(f"/api/review-queue/{q.id}/actions/send", json={"note": q.payload["original_text"]}, headers=h)
    assert r.status_code == 400 and "Connect your Outlook" in r.json()["detail"]
    assert client.post(f"/api/review-queue/{q.id}/actions/replied", json={}, headers=h).status_code == 200
