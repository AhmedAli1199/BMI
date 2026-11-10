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


def test_data_managers_dont_see_everyones_commission_or_costs(client, db_session):
    """Commission and costs and profit are for administrators and accounts, not data managers."""
    dm = make_user(db_session, role="data_manager")
    acc = make_user(db_session, role="data_manager")
    acc.can_approve_bookings = True
    db_session.commit()
    r = client.get("/api/commission/overview", headers=identity_headers(dm)).json()
    assert r["scoped_to_me"] is True and r["reps"] == []
    assert client.get("/api/sales/costs-report", headers=identity_headers(dm)).status_code == 403
    assert client.get("/api/commission/overview", headers=identity_headers(acc)).json()["scoped_to_me"] is False
    assert client.get("/api/sales/costs-report", headers=identity_headers(acc)).status_code == 200
