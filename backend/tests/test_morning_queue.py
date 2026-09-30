"""Regression coverage for the Sept 23 demo /today crash: _resolve_owner
in morning_queue.py referenced Company without importing it, so any item
whose contact had no owner but *did* have a linked company (or any item
tied to a company entity directly) threw a bare NameError -> 500. See
backend/app/automations/morning_queue.py and the fix commit.

These hit build_today_queue directly (not just the /today route) so a
regression here fails fast and points straight at the aggregation logic,
independent of any route/identity-layer change."""
import uuid
from datetime import datetime, timezone

from app.automations.morning_queue import build_today_queue
from app.models import Company, Contact, ReviewQueueItem, User


def _signal_item(db_session, *, contact: Contact, source_db: str = "onboard") -> ReviewQueueItem:
    item = ReviewQueueItem(
        id=uuid.uuid4(), kind="signal_trigger", source_db=source_db,
        entity_type="contact", entity_id=contact.id,
        payload={"summary": "Renewal due", "confidence": 0.8, "details": [{"key": "due_date", "value": "2026-10-05"}]},
        status="pending",
    )
    db_session.add(item)
    db_session.flush()
    return item


def test_owner_resolved_directly_from_contact(client, db_session):
    owner = User(id=uuid.uuid4(), email="owner@example.test", name="Direct Owner", hashed_password="x", role="sales")
    db_session.add(owner)
    db_session.flush()
    contact = Contact(
        id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()),
        first_name="Neil", last_name="Hicks", owner_user_id=owner.id,
    )
    db_session.add(contact)
    db_session.flush()
    _signal_item(db_session, contact=contact)

    results = build_today_queue(db_session)
    assert any(r["owner_name"] == "Direct Owner" for r in results)


def test_owner_falls_back_to_the_contacts_company_without_crashing(client, db_session):
    """The exact path that crashed: a contact with no owner of its own but
    a linked Company that DOES have one."""
    company_owner = User(id=uuid.uuid4(), email="companyowner@example.test", name="Company Owner", hashed_password="x", role="sales")
    db_session.add(company_owner)
    db_session.flush()
    company = Company(
        id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()),
        name="Acme Ltd", owner_user_id=company_owner.id,
    )
    db_session.add(company)
    db_session.flush()
    contact = Contact(
        id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()),
        first_name="Neil", last_name="Hicks", owner_user_id=None, company_id=company.id,
    )
    db_session.add(contact)
    db_session.flush()
    _signal_item(db_session, contact=contact)

    results = build_today_queue(db_session)  # must not raise NameError
    assert any(r["owner_name"] == "Company Owner" for r in results)


def test_company_entity_item_resolves_without_crashing(db_session):
    """The other new path: a review item whose entity_type is 'company'
    directly, not routed through a contact at all."""
    company_owner = User(id=uuid.uuid4(), email="ownerdirect@example.test", name="Direct Company Owner", hashed_password="x", role="sales")
    db_session.add(company_owner)
    db_session.flush()
    company = Company(
        id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()),
        name="Acme Ltd", owner_user_id=company_owner.id,
    )
    db_session.add(company)
    db_session.flush()
    item = ReviewQueueItem(
        id=uuid.uuid4(), kind="signal_trigger", source_db="onboard",
        entity_type="company", entity_id=company.id,
        payload={"summary": "Renewal due", "confidence": 0.8},
        status="pending",
    )
    db_session.add(item)
    db_session.flush()

    results = build_today_queue(db_session)  # must not raise NameError
    assert any(r["owner_name"] == "Direct Company Owner" for r in results)


def test_no_owner_anywhere_is_labeled_unassigned_not_dropped(db_session):
    contact = Contact(
        id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()),
        first_name="Nobody", last_name="Owns", owner_user_id=None, company_id=None,
    )
    db_session.add(contact)
    db_session.flush()
    _signal_item(db_session, contact=contact)

    results = build_today_queue(db_session)
    assert any(r["owner_name"] == "Unassigned" for r in results)


def test_today_route_returns_200_end_to_end(client, db_session):
    """Full HTTP round trip through /api/automations/today - the exact
    request that returned a 500 during the demo."""
    company_owner = User(id=uuid.uuid4(), email="e2e-owner@example.test", name="E2E Owner", hashed_password="x", role="sales")
    db_session.add(company_owner)
    db_session.flush()
    company = Company(
        id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()),
        name="Acme Ltd", owner_user_id=company_owner.id,
    )
    db_session.add(company)
    db_session.flush()
    contact = Contact(
        id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()),
        first_name="Neil", last_name="Hicks", owner_user_id=None, company_id=company.id,
    )
    db_session.add(contact)
    db_session.flush()
    _signal_item(db_session, contact=contact)

    resp = client.get("/api/automations/today")
    assert resp.status_code == 200
    assert any(item["owner_name"] == "E2E Owner" for item in resp.json())
