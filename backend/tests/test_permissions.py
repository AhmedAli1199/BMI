"""Who may do what (docs/app-review-notes.md, "Security"): team accounts, other people's preferences, bulk-update
history, exporting a selection, deletes, switched-off accounts, editions, sent proposals."""
import io
import uuid
from datetime import date

import openpyxl

from app.models import BulkEdit, Contact, SalesEdition, SalesTitle
from app.sales.reference import ensure_reference_data
from tests.conftest import identity_headers, make_user


def _contact(db, source="onboardhospitality", name="Ann Lee"):
    first, last = name.split()
    c = Contact(id=uuid.uuid4(), source_db=source, source_act_id=uuid.uuid4().hex[:12], first_name=first, last_name=last, full_name=name)
    db.add(c)
    db.flush()
    return c


def test_only_admins_manage_team_accounts(client, db_session):
    admin, sales = make_user(db_session, role="admin"), make_user(db_session, role="sales")
    body = {"email": "new.person@example.com", "name": "New Person", "password": "a-long-password-1", "role": "admin", "access": []}
    assert client.post("/api/users", json=body, headers=identity_headers(sales)).status_code == 403
    assert client.patch(f"/api/users/{sales.id}", json={"role": "admin"}, headers=identity_headers(sales)).status_code == 403
    assert client.get("/api/users", headers=identity_headers(sales)).status_code == 403
    assert client.post("/api/users", json=body, headers=identity_headers(admin)).status_code == 201


def test_preferences_are_your_own(client, db_session):
    me, other = make_user(db_session), make_user(db_session)
    r = client.patch(f"/api/users/{other.id}/preferences", json={"values": {"brain_tips": "off"}}, headers=identity_headers(me))
    assert r.status_code == 403
    assert client.get(f"/api/users/{other.id}/preferences", headers=identity_headers(me)).status_code == 403
    r = client.patch(f"/api/users/{me.id}/preferences", json={"values": {"brain_tips": "off"}}, headers=identity_headers(me))
    assert r.status_code == 200


def test_bulk_update_history_and_undo_are_yours(client, db_session):
    me, other = make_user(db_session, role="data_manager"), make_user(db_session, role="data_manager")
    admin = make_user(db_session, role="admin")
    theirs = BulkEdit(id=uuid.uuid4(), user_id=other.id, field_key="job_title", field_label="Job title", op="set", total=0, changed=0, before={})
    db_session.add(theirs)
    db_session.flush()
    access = [("onboardhospitality", None)]
    assert client.get("/api/contacts/bulk-update/history", headers=identity_headers(me, access=access)).json() == []
    assert client.post(f"/api/contacts/bulk-update/{theirs.id}/undo", headers=identity_headers(me, access=access)).status_code == 403
    assert [e["id"] for e in client.get("/api/contacts/bulk-update/history", headers=identity_headers(admin)).json()] == [str(theirs.id)]
    assert client.post(f"/api/contacts/bulk-update/{theirs.id}/undo", headers=identity_headers(admin)).status_code == 200


def test_exporting_a_selection_leaves_out_contacts_you_cant_see(client, db_session):
    mine, hidden = _contact(db_session, name="Ann Mine"), _contact(db_session, source="sellingtravel", name="Bob Hidden")
    me = make_user(db_session, role="sales")
    r = client.post("/api/contacts/export", json={"ids": [str(mine.id), str(hidden.id)]},
                    headers=identity_headers(me, access=[("onboardhospitality", None)]))
    assert r.status_code == 200
    text = " ".join(str(c.value) for row in openpyxl.load_workbook(io.BytesIO(r.content)).active.iter_rows() for c in row if c.value)
    assert "Mine" in text and "Hidden" not in text


def test_only_staff_delete_contacts_companies_and_groups(client, db_session):
    c = _contact(db_session)
    sales, manager = make_user(db_session, role="sales"), make_user(db_session, role="data_manager")
    access = [("onboardhospitality", None)]
    assert client.delete(f"/api/contacts/{c.id}", headers=identity_headers(sales, access=access)).status_code == 403
    assert client.delete(f"/api/contacts/{c.id}", headers=identity_headers(manager, access=access)).status_code == 204


def test_switched_off_account_is_turned_away_and_role_changes_apply_at_once(client, db_session):
    user = make_user(db_session, role="sales")
    headers = identity_headers(user)
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200 and me.json()["role"] == "sales"
    user.role = "admin"   # promoted after signing in: the old session still says "sales"
    db_session.flush()
    assert client.get("/api/users", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=headers).json()["role"] == "admin"
    user.is_active = False
    db_session.flush()
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 401 and r.headers.get("X-BMI-Signed-Out") == "1"
    assert "switched off" in r.json()["detail"]


def test_only_staff_add_or_close_editions_but_anyone_keeps_notes(client, db_session):
    ensure_reference_data(db_session)
    title = db_session.query(SalesTitle).filter_by(slug="obh").one()
    ed = SalesEdition(id=uuid.uuid4(), title_id=title.id, year=date.today().year, name="Z1", edition_date=date.today())
    db_session.add(ed)
    db_session.flush()
    sales, manager = make_user(db_session, role="sales"), make_user(db_session, role="data_manager")
    new = {"title_id": str(title.id), "year": date.today().year, "name": "Z2"}
    assert client.post("/api/sales/editions", json=new, headers=identity_headers(sales)).status_code == 403
    assert client.patch(f"/api/sales/editions/{ed.id}", json={"status": "closed"}, headers=identity_headers(sales)).status_code == 403
    assert client.patch(f"/api/sales/editions/{ed.id}", json={"notes": "Late copy"}, headers=identity_headers(sales)).status_code == 200
    assert client.post("/api/sales/editions", json=new, headers=identity_headers(manager)).status_code == 201
