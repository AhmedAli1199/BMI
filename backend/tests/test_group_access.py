"""Access limited to one group inside a database is enforced on the server, on every screen's data."""
import uuid

import pytest

from app.models import Company, Contact, Email, Group, GroupMembership, ReviewQueueItem, UserAccess
from tests.conftest import identity_headers, make_user


def _id():
    return str(uuid.uuid4())


@pytest.fixture()
def w(db_session):
    db = db_session
    st = Group(id=uuid.uuid4(), name="1 Selling Travel", source_db="prospects", source_act_id=_id(), hier_level=0)
    db.add(st)
    db.flush()
    sub = Group(id=uuid.uuid4(), name="Agents", source_db="prospects", source_act_id=_id(), hier_level=1, parent_group_id=st.id)
    other = Group(id=uuid.uuid4(), name="2 Business Travel", source_db="prospects", source_act_id=_id(), hier_level=0)
    db.add_all([sub, other])
    co_in = Company(id=uuid.uuid4(), name="Inside Travel", source_db="prospects", source_act_id=_id())
    co_out = Company(id=uuid.uuid4(), name="Outside Corp", source_db="prospects", source_act_id=_id())
    db.add_all([co_in, co_out])
    db.flush()

    def person(first, sdb, company=None, group=None):
        c = Contact(id=uuid.uuid4(), source_db=sdb, source_act_id=_id(), first_name=first, last_name="Test", full_name=f"{first} Test",
                    company_id=company.id if company else None)
        db.add(c)
        db.flush()
        db.add(Email(id=uuid.uuid4(), source_db=sdb, source_act_id=_id(), contact_id=c.id, address=f"{first.lower()}@x.test", is_primary=True))
        if group:
            db.add(GroupMembership(id=uuid.uuid4(), group_id=group.id, contact_id=c.id))
        db.flush()
        return c

    a = person("Ann", "prospects", co_in, st)
    b = person("Ben", "prospects", None, sub)
    c = person("Cat", "prospects", co_out, other)
    d = person("Dan", "onboardhospitality")
    sally = make_user(db, role="sales", name="Sally Parker")
    db.add(UserAccess(id=uuid.uuid4(), user_id=sally.id, source_db="prospects", group_id=st.id))
    full = make_user(db, role="sales")
    db.add(UserAccess(id=uuid.uuid4(), user_id=full.id, source_db="prospects", group_id=None))
    db.flush()
    return {"a": a, "b": b, "c": c, "d": d, "st": st, "sub": sub, "other": other, "co_in": co_in, "co_out": co_out,
            "sally": identity_headers(sally), "full": identity_headers(full), "admin": identity_headers(make_user(db, role="admin"))}


def names(r):
    return sorted(x["first_name"] for x in r.json()["items"])


def test_group_user_sees_only_their_group_and_subgroups(client, w):
    assert names(client.get("/api/contacts", headers=w["sally"])) == ["Ann", "Ben"]
    assert names(client.get("/api/contacts?source_db=prospects", headers=w["sally"])) == ["Ann", "Ben"]
    assert names(client.get("/api/contacts?q=cat", headers=w["sally"])) == []
    assert client.get(f"/api/contacts/{w['a'].id}", headers=w["sally"]).status_code == 200
    for who in ("c", "d"):
        assert client.get(f"/api/contacts/{w[who].id}", headers=w["sally"]).status_code == 404
        assert client.patch(f"/api/contacts/{w[who].id}", json={"job_title": "x"}, headers=w["sally"]).status_code == 404
    ids = client.get("/api/contacts/lookup-ids", headers=w["sally"]).json()
    assert set(ids) == {str(w["a"].id), str(w["b"].id)}


def test_companies_groups_and_tools(client, w):
    assert [x["name"] for x in client.get("/api/companies", headers=w["sally"]).json()["items"]] == ["Inside Travel"]
    assert client.get(f"/api/companies/{w['co_out'].id}", headers=w["sally"]).status_code == 404
    detail = client.get(f"/api/companies/{w['co_in'].id}", headers=w["sally"]).json()
    assert [c["first_name"] for c in detail["contacts"]] == ["Ann"]
    groups = sorted(g["name"] for g in client.get("/api/groups?source_db=prospects&page_size=200", headers=w["sally"]).json()["items"])
    assert groups == ["1 Selling Travel", "Agents"]
    assert client.get(f"/api/groups/{w['other'].id}", headers=w["sally"]).status_code == 404
    r = client.post("/api/contacts/emails", json={"q": "test"}, headers=w["sally"]).json()
    assert sorted(r["text"].split("; ")) == ["ann@x.test", "ben@x.test"]


def test_review_items_and_whole_database_grants(client, db_session, w):
    db_session.add(ReviewQueueItem(id=uuid.uuid4(), kind="bounce_uncertain", source_db="prospects", entity_type="contact",
                                   entity_id=w["c"].id, payload={"summary": "Cat bounced"}, status="pending"))
    db_session.flush()
    seen = [i["payload"].get("summary") for i in client.get("/api/review-queue", headers=w["sally"]).json()["items"]]
    assert "Cat bounced" not in seen
    assert names(client.get("/api/contacts", headers=w["full"])) == ["Ann", "Ben", "Cat"]
    assert names(client.get("/api/contacts", headers=w["admin"])) == ["Ann", "Ben", "Cat", "Dan"]

