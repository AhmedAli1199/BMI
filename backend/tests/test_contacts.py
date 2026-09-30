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
