"""Anyone signed in changes their own password."""
from tests.conftest import identity_headers, make_user

from app.core.security import verify_password


def test_change_own_password(client, db_session):
    u = make_user(db_session, role="sales")
    db_session.flush()
    from app.core.security import hash_password
    u.hashed_password = hash_password("old-password-1")
    db_session.commit()
    h = identity_headers(u)
    r = client.post("/api/auth/password", json={"current_password": "wrong", "new_password": "new-password-1"}, headers=h)
    assert r.status_code == 400 and "current password isn't right" in r.json()["detail"]
    assert client.post("/api/auth/password", json={"current_password": "old-password-1", "new_password": "short"}, headers=h).status_code == 422
    r = client.post("/api/auth/password", json={"current_password": "old-password-1", "new_password": "new-password-1"}, headers=h)
    assert r.status_code == 200
    db_session.refresh(u)
    assert verify_password("new-password-1", u.hashed_password)
