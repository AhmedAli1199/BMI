"""Groups CRUD and the bulk member-remove flow (Track A item 1 - BMI's
top Act pain point: removing several contacts from a group one at a time
reset their scroll position to the top of the list each time)."""
import uuid

from app.models import Contact, Group, GroupMembership


def _create_group(client, **overrides):
    payload = {"name": "Newsletter"}
    payload.update(overrides)
    resp = client.post("/api/groups", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _add_member(db_session, group_id: str, contact: Contact) -> None:
    db_session.add(GroupMembership(id=uuid.uuid4(), group_id=uuid.UUID(group_id), contact_id=contact.id))
    db_session.flush()


def _make_contact(db_session, **overrides) -> Contact:
    defaults = dict(id=uuid.uuid4(), source_db="manual", source_act_id=str(uuid.uuid4()), first_name="A", last_name="B")
    defaults.update(overrides)
    contact = Contact(**defaults)
    db_session.add(contact)
    db_session.flush()
    return contact


def test_get_group_lists_members(client, db_session):
    group = _create_group(client)
    contact = _make_contact(db_session, first_name="Ada", last_name="Lovelace")
    _add_member(db_session, group["id"], contact)

    resp = client.get(f"/api/groups/{group['id']}")
    assert resp.status_code == 200
    member_ids = [m["id"] for m in resp.json()["members"]]
    assert str(contact.id) in member_ids


def test_bulk_remove_members(client, db_session):
    group = _create_group(client)
    a = _make_contact(db_session, first_name="Ada")
    b = _make_contact(db_session, first_name="Bea")
    c = _make_contact(db_session, first_name="Cat")
    for contact in (a, b, c):
        _add_member(db_session, group["id"], contact)

    resp = client.post(
        f"/api/groups/{group['id']}/members/remove",
        json={"contact_ids": [str(a.id), str(b.id)]},
    )
    assert resp.status_code == 204

    resp = client.get(f"/api/groups/{group['id']}")
    member_ids = {m["id"] for m in resp.json()["members"]}
    assert member_ids == {str(c.id)}


def test_bulk_remove_requires_at_least_one_contact(client, db_session):
    group = _create_group(client)
    resp = client.post(f"/api/groups/{group['id']}/members/remove", json={"contact_ids": []})
    assert resp.status_code == 422


def test_bulk_remove_unknown_group_404s(client):
    resp = client.post(
        f"/api/groups/{uuid.uuid4()}/members/remove",
        json={"contact_ids": [str(uuid.uuid4())]},
    )
    assert resp.status_code == 404


def test_bulk_remove_is_idempotent_for_ids_not_in_group(client, db_session):
    """A contact id that was never a member (already removed by someone
    else, or a stale client-side selection) doesn't error the whole
    batch - it's just a no-op for that id."""
    group = _create_group(client)
    a = _make_contact(db_session, first_name="Ada")
    _add_member(db_session, group["id"], a)
    not_a_member = _make_contact(db_session, first_name="Stranger")

    resp = client.post(
        f"/api/groups/{group['id']}/members/remove",
        json={"contact_ids": [str(a.id), str(not_a_member.id)]},
    )
    assert resp.status_code == 204

    resp = client.get(f"/api/groups/{group['id']}")
    assert resp.json()["members"] == []
