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


def _metric(body, key):
    return next(m for m in body["metrics"] if m["key"] == key)


def test_unsubscribed_or_bounced_counts_each_contact_once_against_contacts_with_email(client, db_session):
    both = _make_contact(db_session, first_name="Both", is_unsubscribed=True, has_bounced=True)
    bounced = _make_contact(db_session, first_name="Bounced", has_bounced=True)
    fine = _make_contact(db_session, first_name="Fine")
    _make_contact(db_session, first_name="NoEmail")
    for c in (both, bounced, fine):
        db_session.add(Email(id=uuid.uuid4(), source_db="manual", source_act_id=str(uuid.uuid4()), contact_id=c.id,
                             address=f"{c.first_name}@x.com"))
    db_session.flush()

    body = client.get("/api/dashboard/data-health").json()
    m = _metric(body, "unsubscribed")
    assert m["count"] == 2                       # bounced counts too; the one with both counts once
    assert m["total"] == 3                       # measured against contacts with an email address
    assert m["total_label"] == "contacts with an email address"
    assert m["fix_href"].startswith("/contacts?conds=") and "match=any" in m["fix_href"]
    assert _metric(body, "missing_email")["total"] == body["total_contacts"]


def test_fix_links_open_the_filtered_lists_and_backlogs_have_no_percentage(client, db_session):
    body = client.get("/api/dashboard/data-health").json()
    assert "is_empty" in _metric(body, "missing_email")["fix_href"]
    assert _metric(body, "missing_industry")["fix_href"] == "/companies?missing=industry"
    dup = _metric(body, "duplicate_contact")
    assert dup["total"] == 0 and dup["fix_href"] == "/automations/review?kind=duplicate_contact"


def test_contact_fix_links_match_the_counts_on_the_contacts_list(client, db_session):
    from urllib.parse import parse_qs, urlparse

    with_phone = _make_contact(db_session, first_name="Has", last_name="Phone")
    db_session.add(Phone(id=uuid.uuid4(), source_db="manual", source_act_id=str(uuid.uuid4()), contact_id=with_phone.id, number="0123"))
    _make_contact(db_session, first_name="Zed", last_name="Nophone", is_unsubscribed=True)
    db_session.flush()
    body = client.get("/api/dashboard/data-health").json()
    for key in ("missing_phone", "missing_email", "unsubscribed"):
        qs = parse_qs(urlparse(_metric(body, key)["fix_href"]).query)
        resp = client.get("/api/contacts", params={"conds": qs["conds"][0], "match": qs.get("match", [""])[0]})
        assert resp.status_code == 200, resp.text
        assert resp.json()["total"] == _metric(body, key)["count"], key


def test_companies_list_can_show_only_those_without_an_industry(client, db_session):
    _make_company(db_session, name="Blank Co", industry="")
    _make_company(db_session, name="None Co", industry=None)
    _make_company(db_session, name="Full Co", industry="Airline")
    names = {c["name"] for c in client.get("/api/companies", params={"missing": "industry", "page_size": 200}).json()["items"]}
    assert {"Blank Co", "None Co"} <= names and "Full Co" not in names
