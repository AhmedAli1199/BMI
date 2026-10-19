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


def test_group_page_lists_sub_group_members_marked_and_paged(client, db_session):
    """The members list matches Export and Mail merge: the group and its sub-groups, each person once."""
    parent = _create_group(client, name="Airlines")
    child = _create_group(client, name="Airlines - UK", parent_group_id=parent["id"])
    grandchild = _create_group(client, name="Airlines - London", parent_group_id=child["id"])
    direct = _make_contact(db_session, first_name="Dee", last_name="Aaa")
    both = _make_contact(db_session, first_name="Bo", last_name="Bbb")
    deep = _make_contact(db_session, first_name="Lon", last_name="Ccc")
    _add_member(db_session, parent["id"], direct)
    _add_member(db_session, parent["id"], both)
    _add_member(db_session, child["id"], both)
    _add_member(db_session, grandchild["id"], deep)

    body = client.get(f"/api/groups/{parent['id']}").json()
    assert body["member_count"] == 3 and body["direct_member_count"] == 2 and body["has_sub_groups"] is True
    by_id = {m["id"]: m for m in body["members"]}
    assert set(by_id) == {str(direct.id), str(both.id), str(deep.id)}
    assert by_id[str(both.id)]["via_group_id"] is None                 # directly in the group wins
    assert by_id[str(deep.id)]["via_group_name"] == "Airlines - London"
    assert by_id[str(deep.id)]["via_group_id"] == grandchild["id"]

    # a page at a time, in name order, with "start after" for Show more
    first = client.get(f"/api/groups/{parent['id']}", params={"page_size": 2}).json()["members"]
    rest = client.get(f"/api/groups/{parent['id']}", params={"offset": 2}).json()["members"]
    assert [m["last_name"] for m in first + rest] == ["Aaa", "Bbb", "Ccc"]

    # the sub-group itself only lists its own subtree
    sub = client.get(f"/api/groups/{child['id']}").json()
    assert sub["member_count"] == 2 and sub["direct_member_count"] == 1
