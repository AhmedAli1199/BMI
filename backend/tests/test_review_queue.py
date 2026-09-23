"""Review-queue read/write flows, and the identity-based visibility model
discussed with the client: items are scoped by kind-audience + database
access, NOT by which mailbox/rep an item originated from - any sales rep
with access to a database (and every admin) can see and act on an item,
not just the "owner" morning_queue.py resolves it to."""
import uuid
from datetime import datetime, timezone

from tests.conftest import identity_headers, make_user

from app.models import Activity, Contact, ReviewQueueItem


def _make_followup_item(db_session, *, source_db: str = "onboard", status: str = "pending") -> ReviewQueueItem:
    """A followup_due item, backed by a real Activity - see
    followup_queue.py's _handle_followup, which resolves entity_id
    against Activity, not Contact directly."""
    contact = Contact(
        id=uuid.uuid4(), source_db=source_db, source_act_id=str(uuid.uuid4()),
        first_name="Neil", last_name="Hicks",
    )
    db_session.add(contact)
    db_session.flush()
    activity = Activity(
        id=uuid.uuid4(), source_db=source_db, source_act_id=str(uuid.uuid4()),
        contact_id=contact.id, subject="Follow up on renewal",
        start_at=datetime.now(timezone.utc), is_cleared=False,
    )
    db_session.add(activity)
    db_session.flush()
    item = ReviewQueueItem(
        id=uuid.uuid4(),
        kind="followup_due",
        source_db=source_db,
        entity_type="activity",
        entity_id=activity.id,
        payload={"summary": "Renewal date for Neil Hicks", "confidence": 0.8},
        status=status,
    )
    db_session.add(item)
    db_session.flush()
    return item


def test_list_review_items_default_pending(client, db_session):
    item = _make_followup_item(db_session)
    resp = client.get("/api/review-queue")
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert str(item.id) in ids


def test_resolve_review_item_dismiss(client, db_session):
    item = _make_followup_item(db_session)
    resp = client.post(f"/api/review-queue/{item.id}/actions/dismiss", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_resolve_already_resolved_item_conflicts(client, db_session):
    item = _make_followup_item(db_session, status="approved")
    resp = client.post(f"/api/review-queue/{item.id}/actions/dismiss", json={})
    assert resp.status_code == 409


def test_resolve_unknown_action_rejected(client, db_session):
    item = _make_followup_item(db_session)
    resp = client.post(f"/api/review-queue/{item.id}/actions/not_a_real_action", json={})
    assert resp.status_code == 400


def test_sales_identity_only_sees_own_database(client, db_session):
    """A sales rep granted access to 'onboard' only should never see a
    'prospects' item, even by guessing its id - review_queue.py's
    _apply_scope / _is_visible."""
    onboard_item = _make_followup_item(db_session, source_db="onboard")
    prospects_item = _make_followup_item(db_session, source_db="prospects")
    rep = make_user(db_session, role="sales")

    resp = client.get(
        "/api/review-queue", headers=identity_headers(rep, access=[("onboard", None)])
    )
    ids = [i["id"] for i in resp.json()["items"]]
    assert str(onboard_item.id) in ids
    assert str(prospects_item.id) not in ids

    # Not just filtered from the list - a direct id lookup 404s, not 403,
    # so it doesn't confirm the other database's item even exists.
    resp = client.get(
        f"/api/review-queue/{prospects_item.id}", headers=identity_headers(rep, access=[("onboard", None)])
    )
    assert resp.status_code == 404


def test_admin_identity_sees_every_database(client, db_session):
    """Confirms the visibility model explained to the client: an admin
    sees every rep's items regardless of database, unlike a sales
    identity which is scoped to its own access grants."""
    onboard_item = _make_followup_item(db_session, source_db="onboard")
    prospects_item = _make_followup_item(db_session, source_db="prospects")
    admin = make_user(db_session, role="admin")

    resp = client.get("/api/review-queue", headers=identity_headers(admin, access=[]))
    ids = [i["id"] for i in resp.json()["items"]]
    assert str(onboard_item.id) in ids
    assert str(prospects_item.id) in ids


def test_a_reps_item_is_visible_to_a_colleague_with_the_same_database_access(client, db_session):
    """Directly tests the visibility answer given to the client: an item
    from a conversation in one rep's inbox is NOT private to that rep -
    any other sales rep with access to the same database can see and act
    on it via the shared review queue."""
    item = _make_followup_item(db_session, source_db="onboard")
    rep_b = make_user(db_session, role="sales", name="Rep B")

    resp = client.get(
        "/api/review-queue", headers=identity_headers(rep_b, access=[("onboard", None)])
    )
    ids = [i["id"] for i in resp.json()["items"]]
    assert str(item.id) in ids, "a colleague with the same database access should see the item"
