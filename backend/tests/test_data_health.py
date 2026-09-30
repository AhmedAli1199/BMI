"""Data Health page's backing endpoint (BMI Brain rebrand Phase 3):
record-completeness counts plus pending counts of the hygiene automations."""
import uuid

from app.models import Company, Contact, Email, Phone, ReviewQueueItem


def _make_contact(db_session, **overrides) -> Contact:
    defaults = dict(id=uuid.uuid4(), source_db="manual", source_act_id=str(uuid.uuid4()), first_name="A", last_name="B")
    defaults.update(overrides)
    contact = Contact(**defaults)
    db_session.add(contact)
    db_session.flush()
    return contact


def _make_company(db_session, **overrides) -> Company:
    defaults = dict(id=uuid.uuid4(), source_db="manual", source_act_id=str(uuid.uuid4()), name="Acme")
    defaults.update(overrides)
    company = Company(**defaults)
    db_session.add(company)
    db_session.flush()
    return company


def test_data_health_counts_missing_fields(client, db_session):
    with_email = _make_contact(db_session, first_name="Has", last_name="Email")
    db_session.add(Email(id=uuid.uuid4(), source_db="manual", source_act_id=str(uuid.uuid4()), contact_id=with_email.id, address="a@b.com"))
    without_email = _make_contact(db_session, first_name="No", last_name="Email")
    db_session.flush()

    resp = client.get("/api/dashboard/data-health")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    missing_email = next(m for m in body["metrics"] if m["key"] == "missing_email")
    assert missing_email["count"] >= 1
    assert without_email.id  # sanity: the fixture exists


def test_data_health_counts_unsubscribed(client, db_session):
    _make_contact(db_session, first_name="Bounced", is_unsubscribed=True)

    resp = client.get("/api/dashboard/data-health")
    assert resp.status_code == 200
    unsub = next(m for m in resp.json()["metrics"] if m["key"] == "unsubscribed")
    assert unsub["count"] >= 1


def test_data_health_includes_hygiene_automation_pending_counts(client, db_session):
    db_session.add(
        ReviewQueueItem(
            id=uuid.uuid4(),
            kind="duplicate_contact",
            source_db="manual",
            status="pending",
            payload={"summary": "Possible duplicate"},
        )
    )
    db_session.flush()

    resp = client.get("/api/dashboard/data-health")
    assert resp.status_code == 200
    dup = next(m for m in resp.json()["metrics"] if m["key"] == "duplicate_contact")
    assert dup["count"] >= 1
    assert dup["review_kind"] == "duplicate_contact"


def test_data_health_scopes_by_source_db(client, db_session):
    _make_contact(db_session, source_db="manual", first_name="InManual")
    _make_contact(db_session, source_db="onboard_hospitality", first_name="InHospitality")

    resp = client.get("/api/dashboard/data-health?source_db=onboard_hospitality")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_contacts"] == 1


def test_data_health_missing_industry_company(client, db_session):
    _make_company(db_session, name="No Industry", industry=None)
    _make_company(db_session, name="Has Industry", industry="Travel")

    resp = client.get("/api/dashboard/data-health")
    assert resp.status_code == 200
    missing = next(m for m in resp.json()["metrics"] if m["key"] == "missing_industry")
    assert missing["count"] >= 1
