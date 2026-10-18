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


def test_number_settings_refuse_empty_or_broken_values_plainly(client, db_session):
    admin = identity_headers(make_user(db_session, role="admin"))
    url = "/api/automations/settings/mail_merge_per_minute"
    before = client.get("/api/automations/settings", headers=admin).json()
    for bad, msg in ((None, "Enter a number."), ("", "Enter a number."), ("abc", "Enter a number."), ("NaN", "Enter a number."),
                     ("Infinity", "Enter a number."), (True, "Enter a number."), (2.5, "Enter a whole number."),
                     (0, "Mail merge emails per minute must be at least 1."), (31, "Mail merge emails per minute must be at most 30.")):
        r = client.put(url, json={"value": bad}, headers=admin)
        assert (r.status_code, r.json()["detail"]) == (422, msg), bad
    assert client.get("/api/automations/settings", headers=admin).json() == before  # nothing was saved
    # a raw NaN in the request body (JSON.stringify sends null, other callers may not)
    r = client.put("/api/automations/settings/dedupe_confidence_floor", content='{"value": NaN}', headers={**admin, "Content-Type": "application/json"})
    assert (r.status_code, r.json()["detail"]) == (422, "Enter a number.")
    assert client.put(url, json={"value": "12"}, headers=admin).json()["value"] == 12
    assert client.put("/api/automations/settings/dedupe_confidence_floor", json={"value": 0.8}, headers=admin).json()["value"] == 0.8
    assert client.put("/api/automations/settings/not_a_setting", json={"value": 1}, headers=admin).json()["detail"] == "That setting doesn't exist."


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


def test_one_person_can_have_their_own_choice(client, db_session):
    admin = identity_headers(make_user(db_session, role="admin"))
    kirsty_user = make_user(db_session, role="sales", name="Kirsty")
    kirsty, other = identity_headers(kirsty_user), identity_headers(make_user(db_session, role="sales"))
    client.put("/api/ui/sections", json={"hidden": {"sales": ["invoicing"]}, "users": {str(kirsty_user.id): ["groups", "rate_card"]}},
               headers=admin)
    assert client.get("/api/ui/sections", headers=kirsty).json()["mine"] == ["groups", "rate_card"]   # replaces the role's
    assert client.get("/api/ui/sections", headers=other).json()["mine"] == ["invoicing"]
    info = client.get("/api/ui/sections", headers=admin).json()
    assert info["users"] == {str(kirsty_user.id): ["groups", "rate_card"]} and any(p["name"] == "Kirsty" for p in info["people"])
    # saving the roles alone keeps people's own choices
    client.put("/api/ui/sections", json={"hidden": {"sales": []}}, headers=admin)
    assert client.get("/api/ui/sections", headers=kirsty).json()["mine"] == ["groups", "rate_card"]
    client.put("/api/ui/sections", json={"hidden": {"sales": []}, "users": {}}, headers=admin)
    assert client.get("/api/ui/sections", headers=kirsty).json()["mine"] == []
