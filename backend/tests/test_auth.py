"""/api/auth/login - the one unauthenticated-identity route (no X-BMI-User-*
headers are meaningful for login itself, only the shared API key)."""
from tests.conftest import make_user


def test_login_success(client, db_session):
    make_user(db_session, role="sales", email="jane@example.com", name="Jane Rep")
    resp = client.post("/api/auth/login", json={"email": "jane@example.com", "password": "correct-horse-battery-staple"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "jane@example.com"
    assert body["role"] == "sales"


def test_login_wrong_password(client, db_session):
    make_user(db_session, role="sales", email="jane@example.com")
    resp = client.post("/api/auth/login", json={"email": "jane@example.com", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_email(client):
    resp = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "whatever"})
    assert resp.status_code == 401


def test_login_disabled_account(client, db_session):
    user = make_user(db_session, role="sales", email="left@example.com")
    user.is_active = False
    db_session.flush()
    resp = client.post("/api/auth/login", json={"email": "left@example.com", "password": "correct-horse-battery-staple"})
    assert resp.status_code == 401
