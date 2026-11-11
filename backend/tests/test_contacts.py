"""Golden-path CRUD for /api/contacts, plus the group-assignment and
company-linking flows exercised from the UI's EntityPicker (see
frontend/src/components/entity-picker.tsx and act-contact-card.tsx)."""
import uuid

from app.models import Company, Group


def _create_contact(client, **overrides):
    # No source_db passed - falls back to the "manual" bucket
    # (MANUAL_SOURCE_DB), same as a contact created by hand in the UI. A
    # real Publication slug like "onboard" would need a seeded Publication
    # row (see resolve_source_db in api/routes/_publications.py), which
    # these tests deliberately don't depend on.
    payload = {"first_name": "Ada", "last_name": "Lovelace"}
    payload.update(overrides)
    resp = client.post("/api/contacts", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_contact(client):
    body = _create_contact(client)
    assert body["first_name"] == "Ada"
    assert body["last_name"] == "Lovelace"
    assert uuid.UUID(body["id"])


def test_get_contact_by_id(client):
    created = _create_contact(client)
    resp = client.get(f"/api/contacts/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_contact_not_found(client):
    resp = client.get(f"/api/contacts/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_list_contacts_includes_created(client):
    created = _create_contact(client, first_name="Grace", last_name="Hopper")
    resp = client.get("/api/contacts", params={"q": "Hopper"})
    assert resp.status_code == 200
    body = resp.json()
    assert any(c["id"] == created["id"] for c in body["items"])


def test_update_contact_fields(client):
    created = _create_contact(client)
    resp = client.patch(f"/api/contacts/{created['id']}", json={"job_title": "Mathematician"})
    assert resp.status_code == 200
    assert resp.json()["job_title"] == "Mathematician"


def test_update_contact_links_company(client, db_session):
    contact = _create_contact(client)
    company = Company(id=uuid.uuid4(), name="Acme Ltd", source_db="onboard", source_act_id="acme-1")
    db_session.add(company)
    db_session.flush()

    resp = client.patch(f"/api/contacts/{contact['id']}", json={"company_id": str(company.id)})
    assert resp.status_code == 200
    assert resp.json()["company"]["id"] == str(company.id)


def test_update_contact_rejects_unknown_company(client):
    contact = _create_contact(client)
    resp = client.patch(f"/api/contacts/{contact['id']}", json={"company_id": str(uuid.uuid4())})
    assert resp.status_code == 400


def test_delete_contact(client):
    created = _create_contact(client)
    resp = client.delete(f"/api/contacts/{created['id']}")
    assert resp.status_code == 204
    resp = client.get(f"/api/contacts/{created['id']}")
    assert resp.status_code == 404


def test_add_and_remove_contact_group(client, db_session):
    contact = _create_contact(client)
    group = Group(id=uuid.uuid4(), name="Newsletter", source_db="onboard", source_act_id="grp-1")
    db_session.add(group)
    db_session.flush()

    resp = client.post(f"/api/contacts/{contact['id']}/groups/{group.id}")
    assert resp.status_code == 204

    resp = client.get(f"/api/contacts/{contact['id']}")
    group_ids = [g["id"] for g in resp.json().get("groups", [])]
    assert str(group.id) in group_ids

    resp = client.delete(f"/api/contacts/{contact['id']}/groups/{group.id}")
    assert resp.status_code == 204

    resp = client.get(f"/api/contacts/{contact['id']}")
    group_ids = [g["id"] for g in resp.json().get("groups", [])]
    assert str(group.id) not in group_ids


def test_add_note_to_contact(client):
    contact = _create_contact(client)
    resp = client.post(
        f"/api/contacts/{contact['id']}/notes",
        json={"body": "Called about renewal.", "note_type": "Call"},
    )
    assert resp.status_code == 201
    assert resp.json()["body"] == "Called about renewal."


def test_extra_fields_show_on_the_contact_and_can_be_edited(client, db_session):
    """Feedback #10: every extra (Act!) field is listed on the contact, True/False ones as yes/no, and editable one by one."""
    from app.contacts.fields import forget_custom_keys
    from app.models import Contact, FieldChange

    cid = _create_contact(client)["id"]
    c = db_session.get(Contact, uuid.UUID(cid))
    c.custom_fields = {"user3": "ABTA 123", "subscriber": "True", "_import": "x"}
    db_session.flush()
    forget_custom_keys()
    got = client.get(f"/api/contacts/{cid}").json()
    kinds = {f["key"]: f["kind"] for f in got["custom_field_catalog"]}
    assert kinds["subscriber"] == "bool" and kinds["user3"] == "text" and "_import" not in kinds

    r = client.patch(f"/api/contacts/{cid}", json={"custom_fields": {"subscriber": False, "user3": "", "region": "North"}})
    assert r.status_code == 200
    db_session.expire_all()
    cf = db_session.get(Contact, uuid.UUID(cid)).custom_fields
    assert cf == {"subscriber": "False", "region": "North", "_import": "x"}
    changed = {f.field for f in db_session.query(FieldChange).filter_by(entity_id=uuid.UUID(cid))}
    assert {"custom:subscriber", "custom:user3", "custom:region"} <= changed


def test_email_already_on_another_contact_is_flagged(client):
    """Feedback #17: typing an email that's already in the CRM shows who has it (case and spaces ignored)."""
    a = _create_contact(client, first_name="Jane", last_name="Smith", email="jane@acme.test")
    b = _create_contact(client, first_name="Other", last_name="Person", email="other@acme.test")
    got = client.get("/api/contacts/email-matches", params={"email": "  JANE@acme.test "}).json()
    assert [g["id"] for g in got] == [a["id"]] and got[0]["name"] == "Jane Smith"
    assert client.get("/api/contacts/email-matches", params={"email": "jane@acme.test", "exclude": a["id"]}).json() == []
    assert client.get("/api/contacts/email-matches", params={"email": "nobody@acme.test"}).json() == []
    assert b["id"]


def test_anything_rule_matches_like_the_quick_search(client):
    """The quick search box carried into Advanced search as an "Anything contains" rule finds the same people."""
    import json

    a = _create_contact(client, first_name="Quincy", last_name="Rulefinder", email="q.rule@acme.test")
    _create_contact(client, first_name="Other", last_name="Person")
    quick = client.get("/api/contacts", params={"q": "quincy acme"}).json()
    rule = client.get("/api/contacts", params={"conds": json.dumps([{"field": "anything", "op": "contains", "value": "quincy acme"}])}).json()
    assert [i["id"] for i in quick["items"]] == [i["id"] for i in rule["items"]] == [a["id"]]
    fields = {f["key"]: f for f in client.get("/api/contacts/fields").json()}
    assert [o["op"] for o in fields["anything"]["ops"]] == ["contains", "not_contains"]


def test_quick_search_finds_names_made_of_digits(client):
    """Craig's test contacts are called "006 006": searching "006" must find them (feedback #19)."""
    a = _create_contact(client, first_name="006", last_name="006")
    found = client.get("/api/contacts", params={"q": "006", "page_size": 10}).json()
    assert a["id"] in [i["id"] for i in found["items"]]


def test_relevance_sort_puts_name_matches_first(client):
    """A picker search for "006" shows the person called 006 before people whose phone or postcode has 006 in it."""
    for i in range(12):
        _create_contact(client, first_name="Aaron", last_name=f"Aardvark{i}", phone=f"0207 006 00{i:02d}")
    a = _create_contact(client, first_name="006", last_name="Zz006")
    found = client.get("/api/contacts", params={"q": "006", "page_size": 10, "sort": "relevance"}).json()
    assert found["items"][0]["id"] == a["id"]
