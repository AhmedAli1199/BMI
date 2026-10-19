"""Filters (facets), date sorting and record links for the review kinds that didn't have them,
the Queue Insights group being respected by bulk actions, bulk actions on very large selections,
and soft bounces offering "Keep - it was temporary" as the main button."""
import uuid
from datetime import date, datetime, timezone

import pytest

from tests.conftest import identity_headers, make_user

from app.api.routes import review_queue as rq
from app.automations import review_facets as rf
from app.automations.bounce_handling import _handle_candidate_bounce
from app.automations.mail_parsing import ParsedMessage
from app.automations.registry import get_kind
from app.models import Activity, Company, Contact, Email, ReviewQueueItem

KINDS = [
    "bounce_uncertain", "bounce_unmatched", "ooo_ambiguous", "departure_unconfirmed", "duplicate_contact",
    "business_card_new", "business_card_existing", "returned_copy", "inbound_contact_unmatched", "followup_due",
    "signal_trigger", "personal_touchpoint_due", "renewal_due",
]
NO_DATE = {"duplicate_contact"}  # two contacts that look alike have no date worth sorting by


def _company(db, name="Chubb Travel"):
    c = Company(id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()), name=name)
    db.add(c)
    db.flush()
    return c


def _contact(db, company=None, name="Neil Hicks", email=None, owner=None):
    first, last = name.split(" ", 1)
    c = Contact(id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()), first_name=first, last_name=last,
                full_name=name, company_id=company.id if company else None, owner_user_id=owner.id if owner else None)
    db.add(c)
    db.flush()
    if email:
        db.add(Email(id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()), contact_id=c.id, address=email, is_primary=True))
        db.flush()
    return c


def _sample(db, kind: str) -> ReviewQueueItem:
    """A card shaped like the one each kind's scan queues."""
    owner = make_user(db, name="Sally Parker")
    company = _company(db)
    contact = _contact(db, company, owner=owner)
    other = _contact(db, company, name="Neil Hickes")
    received = "2026-10-12T09:30:00+00:00"
    entity = ("contact", contact.id)
    payload: dict = {"summary": f"A {kind} card", "details": []}
    if kind in ("bounce_uncertain", "bounce_unmatched"):
        payload |= {"severity": "soft", "mailbox": "sales@bmi.example", "received_at": received,
                    "details": [{"key": "address", "label": "Failed address", "value": "neil@chubb.example"}]}
        if kind == "bounce_unmatched":
            entity = (None, None)
    elif kind == "ooo_ambiguous":
        payload |= {"mailbox": "sales@bmi.example", "received_at": received, "return_date": "2026-10-20",
                    "replacements": [{"name": "Neil Hickes", "email": None, "role": None}],
                    "suggested_contact": {"id": str(other.id), "label": "Neil Hickes"}}
    elif kind == "departure_unconfirmed":
        payload |= {"mailbox": "sales@bmi.example", "received_at": received,
                    "candidate": {"contact_id": str(other.id), "label": "Neil Hickes"}}
    elif kind == "duplicate_contact":
        payload |= {"details": [{"key": "same_email", "label": "Same email", "value": "Unknown - no data"},
                                {"key": "same_company", "label": "Same company", "value": "Yes"}],
                    "related_entities": [{"type": "contact", "id": str(contact.id), "label": "Neil Hicks"},
                                         {"type": "contact", "id": str(other.id), "label": "Neil Hickes"}]}
    elif kind == "business_card_new":
        payload |= {"card": {"first_name": "Jane", "last_name": "Smith", "company": "Chubb Travel"}, "source_db": "onboard",
                    "show_context": "WTM London", "company_match_id": str(company.id)}
        entity = (None, None)
    elif kind == "business_card_existing":
        payload |= {"card": {"first_name": "Neil"}, "source_db": "onboard", "show_context": None,
                    "changed_fields": [{"label": "Job title", "old": "A", "new": "B"}]}
    elif kind == "returned_copy":
        payload |= {"label": {"name": "Neil Hicks", "return_reason": "Gone away"}, "matched_entity_type": "contact",
                    "matched_entity_id": str(contact.id), "source_db": "onboard"}
    elif kind == "inbound_contact_unmatched":
        payload |= {"mailbox": "enquiries@bmi.example", "received_at": received, "is_high_intent": True, "source_db": "onboard",
                    "company_id": str(company.id), "details": [{"key": "suggested_company", "label": "Suggested company", "value": company.name}]}
        entity = (None, None)
    elif kind == "followup_due":
        activity = Activity(id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()), contact_id=contact.id,
                            subject="Renewal", activity_type="Call", priority="high", organized_by_name="Sally Parker",
                            start_at=datetime(2026, 10, 14, tzinfo=timezone.utc), is_cleared=False)
        db.add(activity)
        db.flush()
        entity = ("activity", activity.id)
        payload |= {"due_at": activity.start_at.isoformat(),
                    "related_entities": [{"type": "contact", "id": str(contact.id), "label": "Neil Hicks"}]}
    elif kind in ("signal_trigger", "personal_touchpoint_due"):
        payload |= {"signal_type": "budget_window", "due_date": "2026-11-01"}
    elif kind == "renewal_due":
        entity = ("company", company.id)
        payload |= {"owner_name": "Sally Parker", "title_name": "OnBoard Hospitality", "suggested_to": "", "due_date": "2026-11-05",
                    "details": [{"key": "price", "label": "This year's price", "value": "Not on the 2026 rate card - add it"}]}
    item = ReviewQueueItem(id=uuid.uuid4(), kind=kind, source_db=None if kind == "bounce_unmatched" else "onboard",
                           entity_type=entity[0], entity_id=entity[1], payload=payload)
    return item


@pytest.mark.parametrize("kind", KINDS)
def test_each_kind_declares_filters_and_its_cards_carry_the_values(db_session, kind):
    kind_def = get_kind(kind)
    assert kind_def.facets, f"{kind} has no filters"
    assert kind_def.derive_facets is not None
    assert bool(kind_def.date_sort_label) == (kind not in NO_DATE)

    item = rf.stamp(db_session, _sample(db_session, kind))
    facets = item.payload["facets"]
    assert set(facets) == {key for key, _ in kind_def.facets}
    assert all(isinstance(v, str) and v for v in facets.values()), facets
    if kind not in NO_DATE:
        assert item.payload["sort_date"], f"{kind} card has no date to sort by"
        date.fromisoformat(item.payload["sort_date"])


def test_sample_values_read_plainly(db_session):
    def facets(kind):
        return rf.stamp(db_session, _sample(db_session, kind)).payload["facets"]

    assert facets("bounce_uncertain") == {"severity": "Soft bounce", "mailbox": "sales@bmi.example", "database": "Onboard Hospitality"}
    assert facets("duplicate_contact")["same_email"] == "No data"
    assert facets("followup_due") == {"type": "Call", "priority": "High", "organiser": "Sally Parker", "database": "Onboard Hospitality"}
    assert facets("signal_trigger")["owner"] == "Sally Parker"
    assert facets("renewal_due") == {"salesperson": "Sally Parker", "title": "OnBoard Hospitality",
                                     "price": "Not on the rate card", "recipient": "No email address yet"}


def test_cards_link_the_company_and_other_records_they_mention(db_session):
    item = rf.stamp(db_session, _sample(db_session, "ooo_ambiguous"))
    hrefs = {d["key"]: d["href"] for d in item.payload["details"] if d.get("href")}
    assert hrefs["company_link"].startswith("/companies/")
    assert hrefs["replacement_link"].startswith("/contacts/")
    unmatched = rf.stamp(db_session, _sample(db_session, "bounce_unmatched"))
    assert any(d.get("href", "").startswith("/contacts?q=") for d in unmatched.payload["details"])
    # stamping twice doesn't add the links twice
    again = rf.stamp(db_session, item)
    assert [d["key"] for d in again.payload["details"]].count("company_link") == 1


def test_older_cards_show_as_not_set_until_the_next_scan_fills_them_in(client, db_session):
    old = ReviewQueueItem(id=uuid.uuid4(), kind="bounce_uncertain", source_db="onboard",
                          payload={"summary": "An old bounce", "severity": "hard"})
    db_session.add(old)
    db_session.flush()
    facets = {f["key"]: {o["value"]: o["count"] for o in f["options"]}
              for f in client.get("/api/review-queue/facets?kind=bounce_uncertain").json()}
    assert facets["severity"] == {"Not set": 1}
    assert client.get("/api/review-queue?kind=bounce_uncertain&facet=severity:Not set").json()["total"] == 1

    assert rf.backfill(db_session, ["bounce_uncertain"]) == 1
    db_session.flush()
    facets = {f["key"]: {o["value"]: o["count"] for o in f["options"]}
              for f in client.get("/api/review-queue/facets?kind=bounce_uncertain").json()}
    assert facets["severity"] == {"Hard bounce": 1}
    assert old.payload["hidden_actions"] == ["keep_temporary"]
    assert rf.backfill(db_session, ["bounce_uncertain"]) == 0  # nothing left to fill in


def _bounce(db, severity):
    item = rf.stamp(db, ReviewQueueItem(id=uuid.uuid4(), kind="bounce_uncertain", source_db="onboard",
                                        payload={"summary": f"{severity} bounce", "severity": severity}))
    db.add(item)
    db.flush()
    return item


def test_bulk_action_only_touches_the_chosen_queue_insights_group(client, db_session):
    soft = [_bounce(db_session, "soft") for _ in range(3)]
    hard = [_bounce(db_session, "hard") for _ in range(2)]
    admin = make_user(db_session, role="admin")
    db_session.commit()
    r = client.post("/api/review-queue/bulk-actions/keep_temporary?kind=bounce_uncertain&bucket=soft",
                    headers=identity_headers(admin), json={})
    assert r.status_code == 200
    assert r.json() | {"errors": []} == {"matched": 3, "succeeded": 3, "failed": 0, "errors": [], "remaining": 0}
    db_session.expire_all()
    assert {i.status for i in soft} == {"rejected"} and {i.resolved_action for i in soft} == {"keep_temporary"}
    assert {i.status for i in hard} == {"pending"}


def test_bulk_action_with_an_unknown_group_says_so_plainly(client, db_session):
    admin = make_user(db_session, role="admin")
    db_session.commit()
    r = client.post("/api/review-queue/bulk-actions/keep_temporary?kind=bounce_uncertain&bucket=nonsense",
                    headers=identity_headers(admin), json={})
    assert r.status_code == 400 and "nonsense" not in r.json()["detail"]


def test_very_large_bulk_selections_are_done_in_rounds(client, db_session, monkeypatch):
    monkeypatch.setattr(rq, "BULK_MAX_PER_CALL", 2)
    monkeypatch.setattr(rq, "BULK_COMMIT_EVERY", 1)
    items = [_bounce(db_session, "soft") for _ in range(5)]
    admin = make_user(db_session, role="admin")
    db_session.commit()
    h = identity_headers(admin)
    url = "/api/review-queue/bulk-actions/not_a_bounce?kind=bounce_uncertain"
    first = client.post(url, headers=h, json={}).json()
    assert (first["matched"], first["succeeded"], first["remaining"]) == (5, 2, 3)
    second = client.post(url, headers=h, json={}).json()
    third = client.post(url, headers=h, json={}).json()
    assert (second["remaining"], third["succeeded"], third["remaining"]) == (1, 1, 0)
    db_session.expire_all()
    assert {i.status for i in items} == {"rejected"}


def _msg(subject="Undeliverable: hello"):
    return ParsedMessage(message_id=str(uuid.uuid4()), internet_message_id=None, from_address="postmaster@chubb.example",
                         from_name=None, subject=subject, received_at=datetime(2026, 10, 12, 9, 30, tzinfo=timezone.utc),
                         body_text="Mailbox full", failed_recipients=["neil@chubb.example"])


@pytest.mark.parametrize("severity", ["soft", "hard"])
def test_soft_bounces_lead_with_keep_and_hard_bounces_with_unsubscribe(db_session, monkeypatch, severity):
    from app.automations import bounce_handling as bh

    _contact(db_session, email="neil@chubb.example")
    monkeypatch.setattr(bh, "_classify_bounce_severity", lambda msg: (severity, 0.9))
    _handle_candidate_bounce(db_session, _msg(), "sales@bmi.example")
    db_session.flush()
    item = db_session.query(ReviewQueueItem).filter_by(kind="bounce_uncertain").one()
    assert item.payload["facets"]["mailbox"] == "sales@bmi.example"
    assert item.payload["sort_date"] == "2026-10-12"
    actions = {a.id for a in get_kind("bounce_uncertain").actions}
    assert {"confirm_hard_bounce", "keep_temporary", "not_a_bounce"} <= actions
    if severity == "soft":
        assert item.payload["primary_action"] == "keep_temporary"
        assert "keep_temporary" not in item.payload["hidden_actions"]
    else:
        assert item.payload["primary_action"] is None  # the kind's own main button: Confirm & unsubscribe
        assert item.payload["hidden_actions"] == ["keep_temporary"]


def test_keeping_a_soft_bounce_changes_nothing_on_the_contact(client, db_session):
    contact = _contact(db_session, email="neil@chubb.example")
    item = rf.stamp(db_session, ReviewQueueItem(id=uuid.uuid4(), kind="bounce_uncertain", source_db="onboard",
                                                entity_type="contact", entity_id=contact.id,
                                                payload={"summary": "Soft bounce for Neil Hicks", "severity": "soft"}))
    db_session.add(item)
    admin = make_user(db_session, role="admin")
    db_session.commit()
    r = client.post(f"/api/review-queue/{item.id}/actions/keep_temporary", headers=identity_headers(admin), json={})
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    db_session.refresh(contact)
    assert contact.is_unsubscribed is False
