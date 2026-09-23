def test_root_ok(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["service"]


def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_missing_api_key_rejected(client):
    client.headers.pop("X-API-Key", None)
    resp = client.get("/api/health")
    assert resp.status_code == 401
