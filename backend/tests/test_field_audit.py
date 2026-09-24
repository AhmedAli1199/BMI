"""Per-user audit trail for Contact/Company field edits - "the ability to
identify which BMI user has made changes to specific data" (BMI's Act
pain-points doc). See app/services/field_audit.py."""
import uuid

from tests.conftest import identity_headers, make_user


def _create_contact(client, **overrides):
    payload = {"first_name": "Ada", "last_name": "Lovelace"}
    payload.update(overrides)
    resp = client.post("/api/contacts", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_company(client, **overrides):
    payload = {"name": "Acme Ltd"}
    payload.update(overrides)
    resp = client.post("/api/companies", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_editing_a_field_records_who_changed_it(client, db_session):
    rep = make_user(db_session, role="sales", name="Jane Rep")
    contact = _create_contact(client)

    resp = client.patch(
        f"/api/contacts/{contact['id']}", json={"job_title": "Mathematician"},
        headers=identity_headers(rep),
    )
    assert resp.status_code == 200

    resp = client.get(f"/api/contacts/{contact['id']}/field-changes")
    assert resp.status_code == 200
    changes = resp.json()
    assert len(changes) == 1
    assert changes[0]["field"] == "job_title"
    assert changes[0]["old_value"] is None
    assert changes[0]["new_value"] == "Mathematician"
    assert changes[0]["changed_by"]["name"] == "Jane Rep"


def test_editing_multiple_fields_records_one_row_each(client, db_session):
    contact = _create_contact(client)
    resp = client.patch(
        f"/api/contacts/{contact['id']}", json={"job_title": "Mathematician", "department": "R&D"},
    )
    assert resp.status_code == 200

    changes = client.get(f"/api/contacts/{contact['id']}/field-changes").json()
    fields = {c["field"] for c in changes}
    assert fields == {"job_title", "department"}


def test_resubmitting_the_same_value_records_nothing(client, db_session):
    contact = _create_contact(client)
    client.patch(f"/api/contacts/{contact['id']}", json={"job_title": "Mathematician"})
    # Same value again - a no-op edit shouldn't clutter the trail.
    client.patch(f"/api/contacts/{contact['id']}", json={"job_title": "Mathematician"})

    changes = client.get(f"/api/contacts/{contact['id']}/field-changes").json()
    assert len(changes) == 1


def test_a_second_edit_shows_the_real_old_value(client, db_session):
    contact = _create_contact(client)
    client.patch(f"/api/contacts/{contact['id']}", json={"job_title": "Mathematician"})
    client.patch(f"/api/contacts/{contact['id']}", json={"job_title": "Scientist"})

    changes = client.get(f"/api/contacts/{contact['id']}/field-changes").json()
    # Newest first.
    assert changes[0]["old_value"] == "Mathematician"
    assert changes[0]["new_value"] == "Scientist"
    assert changes[1]["old_value"] is None
    assert changes[1]["new_value"] == "Mathematician"


def test_an_edit_with_no_identity_header_still_writes_a_row_with_no_attribution(client, db_session):
    """identity.py fails open (no headers forwarded = unrestricted, per
    its own trust-model docstring) - the edit must still succeed and be
    recorded, just without a name attached."""
    contact = _create_contact(client)
    resp = client.patch(f"/api/contacts/{contact['id']}", json={"job_title": "Mathematician"})
    assert resp.status_code == 200

    changes = client.get(f"/api/contacts/{contact['id']}/field-changes").json()
    assert len(changes) == 1
    assert changes[0]["changed_by"] is None


def test_company_field_edits_are_also_recorded(client, db_session):
    rep = make_user(db_session, role="admin", name="Admin User")
    company = _create_company(client)

    resp = client.patch(
        f"/api/companies/{company['id']}", json={"industry": "Travel"},
        headers=identity_headers(rep),
    )
    assert resp.status_code == 200

    changes = client.get(f"/api/companies/{company['id']}/field-changes").json()
    assert len(changes) == 1
    assert changes[0]["field"] == "industry"
    assert changes[0]["new_value"] == "Travel"
    assert changes[0]["changed_by"]["name"] == "Admin User"


def test_field_changes_are_scoped_per_entity(client, db_session):
    a = _create_contact(client, first_name="A")
    b = _create_contact(client, first_name="B")
    client.patch(f"/api/contacts/{a['id']}", json={"job_title": "Title A"})
    client.patch(f"/api/contacts/{b['id']}", json={"job_title": "Title B"})

    changes_a = client.get(f"/api/contacts/{a['id']}/field-changes").json()
    assert len(changes_a) == 1
    assert changes_a[0]["new_value"] == "Title A"


def test_field_changes_for_unknown_contact_is_an_empty_list_not_an_error(client):
    resp = client.get(f"/api/contacts/{uuid.uuid4()}/field-changes")
    assert resp.status_code == 200
    assert resp.json() == []
