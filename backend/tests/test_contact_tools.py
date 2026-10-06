"""Act! feedback B1-B3: search every field, copy emails, bulk update + undo."""
import json
import uuid

import pytest

from app.contacts import fields as F
from app.models import Contact, Email, FieldChange, Group, GroupMembership, Note
from app.models.contact_channel import Address, Phone
from tests.conftest import identity_headers, make_user


def mk(db, first, last, *, title=None, custom=None, email=None, phone=None, postcode=None, source="onboardhospitality", **kw):
    c = Contact(id=uuid.uuid4(), source_db=source, source_act_id=uuid.uuid4().hex[:12], first_name=first, last_name=last,
                full_name=f"{first} {last}", job_title=title, custom_fields=custom or {}, **kw)
    db.add(c)
    db.flush()
    if email:
        db.add(Email(id=uuid.uuid4(), source_db=source, source_act_id=uuid.uuid4().hex[:12], contact_id=c.id, address=email, is_primary=True))
    if phone:
        db.add(Phone(id=uuid.uuid4(), source_db=source, source_act_id=uuid.uuid4().hex[:12], contact_id=c.id, number=phone, type_label="Mobile"))
    if postcode:
        db.add(Address(id=uuid.uuid4(), source_db=source, source_act_id=uuid.uuid4().hex[:12], contact_id=c.id, postal_code=postcode, city="London"))
    db.flush()
    return c


@pytest.fixture()
def people(db_session):
    F.forget_custom_keys()
    a = mk(db_session, "Ann", "Lee", title="Travel Counsellor", custom={"user3": "A1234", "user4": "Travel Counsellor"}, email="ann@x.test", phone="+44 (0)20 7946 0001", postcode="SW1A 1AA")
    b = mk(db_session, "Bob", "Marsh", title="Buyer", custom={"user3": "B9999"}, email="bob@y.test", phone="07700 900123", postcode="M1 1AA")
    c = mk(db_session, "Cy", "Dunn", title="Travel Counsellor", custom={"user4": "Travel Counsellor"}, email="cy@x.test", is_unsubscribed=True)
    return a, b, c


def ids(r):
    return {i["id"] for i in r.json()["items"]}


def test_quick_search_covers_phone_postcode_custom_and_word_order(client, people):
    a, b, c = people
    assert ids(client.get("/api/contacts", params={"q": "7946 0001"})) == {str(a.id)}       # phone, digits only
    assert ids(client.get("/api/contacts", params={"q": "m1 1aa"})) == {str(b.id)}          # postcode
    assert ids(client.get("/api/contacts", params={"q": "A1234"})) == {str(a.id)}           # custom field value
    assert ids(client.get("/api/contacts", params={"q": "lee ann"})) == {str(a.id)}         # any word order


def test_advanced_conditions(client, people):
    a, b, c = people
    def q(conds, match="all"):
        return ids(client.get("/api/contacts", params={"conds": json.dumps(conds), "match": match}))
    assert q([{"field": "postcode", "op": "starts_with", "value": "SW1"}]) == {str(a.id)}
    assert q([{"field": "custom:user4", "op": "equals", "value": "travel counsellor"}]) == {str(a.id), str(c.id)}
    assert q([{"field": "custom:user4", "op": "equals", "value": "Travel Counsellor"}, {"field": "postcode", "op": "is_empty"}]) == {str(c.id)}
    assert q([{"field": "custom:user3", "op": "is_empty"}]) == {str(c.id)}
    assert q([{"field": "is_unsubscribed", "op": "is_yes"}]) == {str(c.id)}
    assert q([{"field": "job_title", "op": "contains", "value": "buyer"}, {"field": "phone", "op": "contains", "value": "7946"}], "any") == {str(a.id), str(b.id)}
    assert q([{"field": "email", "op": "not_contains", "value": "x.test"}]) == {str(b.id)}


def test_bad_condition_is_a_readable_error(client, people):
    r = client.get("/api/contacts", params={"conds": json.dumps([{"field": "nope", "op": "contains", "value": "x"}])})
    assert r.status_code == 422 and "no field" in r.json()["detail"]
    r = client.get("/api/contacts", params={"conds": json.dumps([{"field": "job_title", "op": "contains"}])})
    assert r.status_code == 422


def test_fields_list_names_custom_fields_and_labels_win(client, db_session, people):
    keys = {f["key"]: f for f in client.get("/api/contacts/fields").json()}
    assert "custom:user3" in keys and keys["custom:user3"]["label"] == "User3"
    admin = make_user(db_session, role="admin")
    r = client.put("/api/contacts/fields/custom", json={"user3": "ABTA number"}, headers=identity_headers(admin))
    assert r.status_code == 200
    keys = {f["key"]: f for f in client.get("/api/contacts/fields").json()}
    assert keys["custom:user3"]["label"] == "ABTA number"
    rep = make_user(db_session, role="sales")
    assert client.put("/api/contacts/fields/custom", json={"user3": "x"}, headers=identity_headers(rep)).status_code == 403


def test_copy_emails_skips_unsubscribed_and_dedupes(client, db_session, people):
    a, b, c = people
    mk(db_session, "Ann", "Twin", email="ANN@x.test")
    r = client.post("/api/contacts/emails", json={"scope": None} if False else {"q": "test"}).json()
    assert sorted(x.lower() for x in r["addresses"]) == ["ann@x.test", "bob@y.test"]
    assert r["skipped_unsubscribed"] == 1 and r["duplicates_removed"] == 1
    assert "; " in r["text"]


def test_bulk_update_preview_apply_audit_and_undo(client, db_session, people):
    a, b, c = people
    admin = make_user(db_session, role="admin")
    h = identity_headers(admin)
    scope = {"conds": json.dumps([{"field": "custom:user4", "op": "equals", "value": "Travel Counsellor"}]), "label": "Travel Counsellors"}
    body = {"scope": scope, "field": "custom:user3", "op": "set", "value": "T-100"}
    pv = client.post("/api/contacts/bulk-update/preview", json=body, headers=h).json()
    assert pv["total"] == 2 and pv["will_change"] == 2 and {s["old"] for s in pv["samples"]} == {"A1234", None}
    assert db_session.get(Contact, a.id).custom_fields["user3"] == "A1234"          # preview changed nothing
    r = client.post("/api/contacts/bulk-update", json=body, headers=h)
    assert r.status_code == 200 and r.json()["changed"] == 2
    db_session.expire_all()
    assert db_session.get(Contact, a.id).custom_fields["user3"] == "T-100" and db_session.get(Contact, c.id).custom_fields["user3"] == "T-100"
    assert db_session.get(Contact, b.id).custom_fields["user3"] == "B9999"           # not in scope
    assert db_session.query(FieldChange).filter_by(entity_id=a.id, field="custom:user3", new_value="T-100").count() == 1
    assert client.post("/api/contacts/bulk-update", json=body, headers=h).status_code == 409  # nothing left to change
    # someone edits Cy again, then undo: Cy is left alone
    cc = db_session.get(Contact, c.id)
    cc.custom_fields = {**cc.custom_fields, "user3": "MANUAL"}
    db_session.flush()
    u = client.post(f"/api/contacts/bulk-update/{r.json()['id']}/undo", headers=h).json()
    assert u == {"restored": 1, "skipped": 1}
    db_session.expire_all()
    assert db_session.get(Contact, a.id).custom_fields["user3"] == "A1234"
    assert db_session.get(Contact, c.id).custom_fields["user3"] == "MANUAL"


def test_bulk_text_field_name_updates_full_name_and_replace(client, db_session, people):
    a, b, c = people
    h = identity_headers(make_user(db_session, role="data_manager"), access=[("onboardhospitality", None)])
    r = client.post("/api/contacts/bulk-update", json={"scope": {"ids": [str(a.id)]}, "field": "first_name", "op": "set", "value": "Anne"}, headers=h)
    assert r.status_code == 200
    db_session.expire_all()
    assert db_session.get(Contact, a.id).full_name == "Anne Lee"
    r = client.post("/api/contacts/bulk-update", json={"scope": {"ids": [str(a.id), str(c.id)]}, "field": "job_title", "op": "replace", "find": "Counsellor", "value": "Advisor"}, headers=h)
    assert r.json()["changed"] == 2
    assert client.post("/api/contacts/bulk-update/preview", json={"scope": {"ids": [str(a.id)]}, "field": "email", "op": "set", "value": "x"}, headers=h).status_code == 422


def test_bool_bulk_and_database_scoping(client, db_session, people):
    a, b, c = people
    other = mk(db_session, "Zed", "Zee", source="sellingtravel")
    rep = make_user(db_session, role="sales")
    h = identity_headers(rep, access=[("onboardhospitality", None)])
    r = client.post("/api/contacts/bulk-update", json={"scope": {"ids": [str(a.id), str(other.id)]}, "field": "is_email_opted_out", "op": "set", "value": "yes"}, headers=h)
    assert r.status_code == 200 and r.json()["total"] == 1                          # the other database is out of reach
    db_session.expire_all()
    assert db_session.get(Contact, a.id).is_email_opted_out is True and db_session.get(Contact, other.id).is_email_opted_out is False


def test_export_includes_custom_field_columns(db_session, people):
    import io
    import openpyxl
    from app.services.contact_export import contacts_xlsx
    a, b, c = people
    wb = openpyxl.load_workbook(io.BytesIO(contacts_xlsx(db_session, [a.id, b.id, c.id]).read()))
    rows = list(wb.active.iter_rows(values_only=True))
    assert rows[0][-2:] == ("User3", "User4")
    assert rows[1][-2:] == ("A1234", "Travel Counsellor") and rows[3][-2:] == (None, "Travel Counsellor")
