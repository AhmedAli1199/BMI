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
    assert resp.status_code == 204
    resp = client.get(f"/api/companies/{created['id']}")
    assert resp.status_code == 404


def test_list_companies_search(client):
    created = _create_company(client, name="Very Unique Company Name Ltd")
    resp = client.get("/api/companies", params={"q": "Very Unique Company"})
    assert resp.status_code == 200
    assert any(c["id"] == created["id"] for c in resp.json()["items"])
