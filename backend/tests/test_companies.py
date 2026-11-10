"""Golden-path CRUD for /api/companies."""
import uuid


def _create_company(client, **overrides):
    payload = {"name": "Acme Publishing"}
    payload.update(overrides)
    resp = client.post("/api/companies", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_company_requires_name(client):
    resp = client.post("/api/companies", json={})
    assert resp.status_code == 422


def test_create_company(client):
    body = _create_company(client, website="https://acme.example")
    assert body["name"] == "Acme Publishing"
    assert body["website"] == "https://acme.example"


def test_get_company_not_found(client):
    resp = client.get(f"/api/companies/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_update_company(client):
    created = _create_company(client)
    resp = client.patch(f"/api/companies/{created['id']}", json={"industry": "Travel"})
    assert resp.status_code == 200
    assert resp.json()["industry"] == "Travel"


def test_delete_company(client):
    created = _create_company(client)
    resp = client.delete(f"/api/companies/{created['id']}")
    assert resp.status_code == 200 and resp.json()["deleted"] is True
    resp = client.get(f"/api/companies/{created['id']}")
    assert resp.status_code == 404


def test_list_companies_search(client):
    created = _create_company(client, name="Very Unique Company Name Ltd")
    resp = client.get("/api/companies", params={"q": "Very Unique Company"})
    assert resp.status_code == 200
    assert any(c["id"] == created["id"] for c in resp.json()["items"])


def test_similar_companies_spot_duplicates(client):
    """Feedback #12: before adding a company, the same or close names already in the CRM are shown."""
    a = _create_company(client, name="Acme Travel Ltd")
    _create_company(client, name="Zebra Holidays")
    got = client.get("/api/companies/similar", params={"name": "ACME travel"}).json()
    assert got and got[0]["id"] == a["id"] and got[0]["exact"] is True
    assert all(g["name"] != "Zebra Holidays" for g in got)
    close = client.get("/api/companies/similar", params={"name": "Acme Travl"}).json()
    assert any(g["id"] == a["id"] for g in close)


def test_delete_company_keeps_or_deletes_its_contacts(client, db_session):
    """Feedback #11: deleting a company asks what happens to its contacts; refused while it has bookings."""
    from app.models import Contact

    keep = _create_company(client, name="Keep Co")
    drop = _create_company(client, name="Drop Co")
    c1 = client.post("/api/contacts", json={"first_name": "K", "company_id": keep["id"]}).json()
    c2 = client.post("/api/contacts", json={"first_name": "D", "company_id": drop["id"]}).json()
    assert client.get(f"/api/companies/{keep['id']}/usage").json()["contacts"] == 1
    assert client.delete(f"/api/companies/{keep['id']}").json()["contacts_kept"] == 1
    assert client.delete(f"/api/companies/{drop['id']}", params={"contacts": "delete"}).json()["contacts_deleted"] == 1
    db_session.expire_all()
    assert db_session.get(Contact, uuid.UUID(c1["id"])).company_id is None
    assert db_session.get(Contact, uuid.UUID(c2["id"])) is None


def test_merge_companies_moves_everything(client, db_session):
    """Feedback #12: a duplicate is merged into the right company - contacts and notes move, the spare goes."""
    from app.models import Contact, HistoryEntry

    right = _create_company(client, name="C005")
    dup = _create_company(client, name="C005 ")
    c = client.post("/api/contacts", json={"first_name": "M", "company_id": dup["id"]}).json()
    client.post(f"/api/companies/{dup['id']}/notes", json={"body": "Old note"})
    r = client.post(f"/api/companies/{dup['id']}/merge", json={"into_id": right["id"]})
    assert r.status_code == 200 and r.json()["contacts"] == 1
    db_session.expire_all()
    assert str(db_session.get(Contact, uuid.UUID(c["id"])).company_id) == right["id"]
    assert client.get(f"/api/companies/{dup['id']}").status_code == 404
    notes = client.get(f"/api/companies/{right['id']}").json()["notes"]
    assert any(n["body"] == "Old note" for n in notes)
    assert db_session.query(HistoryEntry).filter_by(entity_id=uuid.UUID(right["id"]), history_type="Merged").count() == 1
    assert client.post(f"/api/companies/{right['id']}/merge", json={"into_id": right["id"]}).status_code == 422
