"""Admin-only platform settings, and sections an admin can hide from other roles."""
from tests.conftest import identity_headers, make_user


def test_only_admins_change_automation_settings(client, db_session):
    admin = identity_headers(make_user(db_session, role="admin"))
    dm = identity_headers(make_user(db_session, role="data_manager"))
    body = {"value": True}
    assert client.put("/api/automations/settings/sales_use_financial_year", json=body, headers=dm).status_code == 403
    assert client.delete("/api/automations/settings/sales_use_financial_year", headers=dm).status_code == 403
    assert client.get("/api/automations/settings", headers=dm).status_code == 200  # still readable
    assert client.put("/api/automations/settings/sales_use_financial_year", json=body, headers=admin).status_code == 200


def test_admin_hides_sections_per_role(client, db_session):
    admin = identity_headers(make_user(db_session, role="admin"))
    sales = identity_headers(make_user(db_session, role="sales"))
    dm = identity_headers(make_user(db_session, role="data_manager"))
    out = client.put("/api/ui/sections", json={"hidden": {"sales": ["invoicing", "rate_card", "not-a-section"], "data_manager": ["groups"],
                                                          "admin": ["contacts"]}}, headers=admin).json()
    assert out["hidden"] == {"sales": ["invoicing", "rate_card"], "data_manager": ["groups"]}
    assert client.get("/api/ui/sections", headers=sales).json()["mine"] == ["invoicing", "rate_card"]
    me = client.get("/api/ui/sections", headers=dm).json()
    assert me["mine"] == ["groups"] and me["hidden"] == {}  # others' settings aren't shown to non-admins
    assert client.get("/api/ui/sections", headers=admin).json()["mine"] == []  # admins always see everything
    assert client.put("/api/ui/sections", json={"hidden": {}}, headers=sales).status_code == 403
