"""Review-queue fixes (17 Oct review):

- reopening a closed card never repeats what its button already did,
- "remind me later" buttons close a card as snoozed, not rejected,
- "Keep as separate contacts" and a dismissed follow-up stay dismissed on later sweeps,
- inbound leads are created in the mailbox's own database,
- returned post never copies the failed address back onto the record,
- a confirmed departure marks the person as having left.
"""
import uuid
from datetime import date, datetime, timedelta, timezone

from tests.conftest import identity_headers, make_user
from tests.test_invoicing_flow import _booking
from tests.test_orders import w  # noqa: F401 - fixture

from app.automations import dedupe, followup_queue
from app.automations.state import set_state
from app.models import Activity, Address, Contact, Email, Note, Phone, ReviewQueueItem


class _NoCloseSession:
    """Lets a scanner (which opens and closes its own SessionLocal) run inside the test's rolled-back transaction."""
    def __init__(self, s):
        self._s = s

    def __getattr__(self, name):
        return getattr(self._s, name)

    def close(self):
        pass


def _contact(db, name="Neil Hicks", source_db="onboard", **kw) -> Contact:
    first, _, last = name.partition(" ")
    c = Contact(id=kw.pop("id", uuid.uuid4()), source_db=source_db, source_act_id=str(uuid.uuid4()),
                first_name=first, last_name=last or None, full_name=name, **kw)
    db.add(c)
    db.flush()
    return c


def _item(db, kind, *, status="pending", action=None, payload=None, entity=None) -> ReviewQueueItem:
    it = ReviewQueueItem(id=uuid.uuid4(), kind=kind, source_db="onboard", status=status, resolved_action=action,
                         entity_type="contact" if entity else None, entity_id=entity.id if entity else None,
                         payload={"summary": f"{kind} card", **(payload or {})})
    db.add(it)
    db.commit()  # a 400 from the route rolls back anything not committed yet
    return it


# ---- 1. reopen ---------------------------------------------------------------------------------------------------

def test_reopen_only_for_buttons_that_changed_nothing(client, db_session):
    nothing_done = _item(db_session, "duplicate_contact", status="rejected", action="not_duplicate")
    wrote_a_note = _item(db_session, "sor_invoice_missing", status="rejected", action="no_invoice_needed")
    told_salesperson = _item(db_session, "order_check", status="rejected", action="fix")
    closed_by_system = _item(db_session, "order_check", status="rejected", action="withdrawn")
    snoozed = _item(db_session, "invoice_due", status="snoozed", action="week")

    assert client.post(f"/api/review-queue/{nothing_done.id}/reopen").json()["status"] == "pending"
    for it in (wrote_a_note, told_salesperson, closed_by_system, snoozed):
        r = client.post(f"/api/review-queue/{it.id}/reopen")
        assert r.status_code == 400, it.resolved_action
        assert "can't be reopened" in r.json()["detail"]
        db_session.refresh(it)
        assert it.status != "pending"


def test_kinds_say_which_buttons_can_be_reopened(client):
    kinds = {k["kind"]: {a["id"]: a for a in k["actions"]} for k in client.get("/api/review-queue/kinds").json()}
    assert kinds["duplicate_contact"]["not_duplicate"]["reopenable"] is True
    assert kinds["invoice_due"]["no_invoice"]["reopenable"] is False
    assert kinds["order_check"]["fix"]["reopenable"] is False
    assert kinds["duplicate_contact"]["merge"]["reopenable"] is False


# ---- 2. snoozed, not rejected ------------------------------------------------------------------------------------

def test_remind_me_later_is_snoozed_and_not_counted_as_rejected(w, client):  # noqa: F811
    db = w["db"]
    sam = make_user(db, role="sales", name="Samantha Elmer")
    sam.can_approve_bookings = True
    sally = make_user(db, role="sales", name="Sally Parker")
    w["reps"]["SP"].user_id = sally.id
    db.commit()
    src = w["titles"]["selling-travel"].crm_source_db
    sam_h, sally_h = identity_headers(sam, access=[(src, None)]), identity_headers(sally, access=[(src, None)])

    body, _ = _booking(w, date.today() + timedelta(days=1))
    assert client.post("/api/sales/deals", json=body, headers=sally_h).status_code < 300
    card = db.query(ReviewQueueItem).filter_by(kind="invoice_due", status="pending").one()
    db.commit()
    r = client.post(f"/api/review-queue/{card.id}/actions/week", json={}, headers=sam_h)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "snoozed"

    stats = client.get("/api/automations/workstreams/revenue/stats").json()
    row = next(a for a in stats["automations"] if a["kind"] == "invoice_due")
    assert row["rejected"] == 0 and row["approved"] == 0 and row["resolved"] == 1

    counts = next(c for c in client.get("/api/review-queue/counts").json() if c["kind"] == "invoice_due")
    assert counts["snoozed"] == 1 and counts["rejected"] == 0
    # and it can't be reopened: the new date is already set
    assert client.post(f"/api/review-queue/{card.id}/reopen").status_code == 400


# ---- 3. "Keep as separate contacts" is remembered ---------------------------------------------------------------

def test_kept_separate_pair_does_not_come_back(db_session, monkeypatch):
    monkeypatch.setattr(dedupe, "SessionLocal", lambda: _NoCloseSession(db_session))
    tail = uuid.uuid4().hex[:10]
    a = _contact(db_session, "Zebulon Quackenbush", id=uuid.UUID(f"ffffffff-ffff-ffff-ffff-ff{tail}"))
    b = _contact(db_session, "Zebulon Quackenbush", id=uuid.UUID(f"ffffffff-ffff-ffff-ffff-ff{tail[:-1]}{'0' if tail[-1] != '0' else '1'}"))
    for c in (a, b):
        db_session.add(Email(id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()), contact_id=c.id,
                             address="zeb@quack.example", is_primary=True))
    db_session.flush()

    def sweep():
        set_state(db_session, "dedupe_scan_cursor", {"last_contact_id": "ffffffff-ffff-ffff-ffff-ff0000000000"})
        dedupe.scan_for_duplicates()

    def cards():
        return [i for i in db_session.query(ReviewQueueItem).filter_by(kind="duplicate_contact")
                if {e["id"] for e in i.payload.get("related_entities", [])} == {str(a.id), str(b.id)}]

    sweep()
    assert len(cards()) == 1
    card = cards()[0]
    card.status, card.resolved_action = "rejected", "not_duplicate"
    db_session.flush()

    sweep()
    assert len(cards()) == 1  # not suggested again


# ---- 4 & 5. dismissed follow-ups stay dismissed; their link goes somewhere real -----------------------------------

def test_dismissed_followup_is_not_requeued_until_its_date_changes(client, db_session, monkeypatch):
    monkeypatch.setattr(followup_queue, "SessionLocal", lambda: _NoCloseSession(db_session))
    contact = _contact(db_session)
    activity = Activity(id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()), contact_id=contact.id,
                        subject="Call about renewal", start_at=datetime.now(timezone.utc) - timedelta(days=1), is_cleared=False)
    db_session.add(activity)
    db_session.flush()

    def pending():
        return db_session.query(ReviewQueueItem).filter_by(kind="followup_due", entity_id=activity.id, status="pending").all()

    followup_queue.scan_for_due_followups()
    [card] = pending()
    # the card points at the contact the activity is for (there's no page for an activity itself)
    assert card.entity_type == "activity" and card.payload["related_entities"][0] == {
        "type": "contact", "id": str(contact.id), "label": "Neil Hicks"}

    assert client.post(f"/api/review-queue/{card.id}/actions/dismiss", json={}).status_code == 200
    followup_queue.scan_for_due_followups()
    assert pending() == []

    activity.start_at = datetime.now(timezone.utc) + timedelta(hours=2)   # rescheduled: a fresh follow-up
    db_session.flush()
    followup_queue.scan_for_due_followups()
    assert len(pending()) == 1


# ---- 6. inbound leads go into the mailbox's database -------------------------------------------------------------

def _inbound(db, source_db):
    return _item(db, "inbound_contact_unmatched", payload={"source_db": source_db, "sender_email": "jo@newco.example",
                                                           "original_text": "Hello, please send a media pack."})


def test_inbound_lead_is_created_in_the_mailbox_database(client, db_session):
    item = _inbound(db_session, "sellingtravel")
    r = client.post(f"/api/review-queue/{item.id}/actions/create_contact",
                    json={"fields": {"name": "Jo Bloggs", "phone": "0123", "company_name": "NewCo"}})
    assert r.status_code == 200, r.text
    contact = db_session.get(Contact, uuid.UUID(r.json()["entity_id"]))
    assert contact.source_db == "sellingtravel"
    assert {e.source_db for e in db_session.query(Email).filter_by(contact_id=contact.id)} == {"sellingtravel"}
    assert {p.source_db for p in db_session.query(Phone).filter_by(contact_id=contact.id)} == {"sellingtravel"}
    assert {n.source_db for n in db_session.query(Note).filter_by(entity_id=contact.id)} == {"sellingtravel"}


def test_shared_inbox_lead_uses_the_database_the_reviewer_picks(client, db_session):
    item = _inbound(db_session, "*")
    r = client.post(f"/api/review-queue/{item.id}/actions/create_contact", json={"fields": {"name": "Jo Bloggs"}})
    assert r.status_code == 400
    r = client.post(f"/api/review-queue/{item.id}/actions/create_contact",
                    json={"fields": {"name": "Jo Bloggs", "source_db": "prospects"}})
    assert r.status_code == 200, r.text
    assert db_session.get(Contact, uuid.UUID(r.json()["entity_id"])).source_db == "prospects"


# ---- 7. returned post --------------------------------------------------------------------------------------------

LABEL = {"name": "Neil Hicks", "address_line1": "1 Old Road", "city": "Oldtown", "postal_code": "OL1 1OL"}


def test_update_address_uses_the_typed_address_not_the_returned_one(client, db_session):
    contact = _contact(db_session)
    addr = Address(id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()), contact_id=contact.id,
                   is_primary=True, line1="1 Old Road", line3="Old estate", city="Oldtown", postal_code="OL1 1OL", country="UK")
    db_session.add(addr)
    item = _item(db_session, "returned_copy", entity=contact, payload={
        "label": LABEL, "matched_entity_type": "contact", "matched_entity_id": str(contact.id)})

    r = client.post(f"/api/review-queue/{item.id}/actions/correct_address", json={"fields": {}})
    assert r.status_code == 400 and "New street address" in r.json()["detail"]

    r = client.post(f"/api/review-queue/{item.id}/actions/correct_address",
                    json={"fields": {"new_line1": "5 New Street", "new_city": "Newtown", "new_postal_code": "NE5 5NE"}})
    assert r.status_code == 200, r.text
    db_session.refresh(addr)
    assert (addr.line1, addr.line3, addr.city, addr.postal_code, addr.country) == ("5 New Street", None, "Newtown", "NE5 5NE", "UK")


def test_unmatched_label_lets_the_reviewer_pick_the_contact(client, db_session):
    contact = _contact(db_session)
    item = _item(db_session, "returned_copy", payload={"label": LABEL, "matched_entity_type": None, "matched_entity_id": None,
                                                       "pick_contact_for": ["correct_address", "retire"]})
    r = client.post(f"/api/review-queue/{item.id}/actions/correct_address", json={"fields": {"new_line1": "5 New Street"}})
    assert r.status_code == 400 and "Pick the contact" in r.json()["detail"]

    r = client.post(f"/api/review-queue/{item.id}/actions/correct_address",
                    json={"fields": {"new_line1": "5 New Street"}, "contact_id": str(contact.id)})
    assert r.status_code == 200, r.text
    [addr] = db_session.query(Address).filter_by(contact_id=contact.id).all()
    assert addr.line1 == "5 New Street" and addr.city is None
    db_session.refresh(item)
    assert item.entity_id == contact.id and item.payload["matched_entity_id"] == str(contact.id)


# ---- 8. departures -----------------------------------------------------------------------------------------------

def test_confirmed_successor_marks_the_person_as_left(client, db_session):
    left = _contact(db_session, "Paul Dowdy")
    other_record = _contact(db_session, "Paul Dowdy", source_db="prospects")
    successor = _contact(db_session, "Bhavisha Hartley")
    item = _item(db_session, "departure_unconfirmed", entity=left, payload={
        "related_entities": [{"type": "contact", "id": str(left.id), "label": "Paul"},
                             {"type": "contact", "id": str(other_record.id), "label": "Paul"}],
        "candidate": {"contact_id": str(successor.id), "label": "Bhavisha", "source": "named in their departure notice"}})

    kinds = {k["kind"]: k for k in client.get("/api/review-queue/kinds").json()}
    confirm = next(a for a in kinds["departure_unconfirmed"]["actions"] if a["id"] == "confirm_successor")
    assert "Left the company" in confirm["confirm_message"] and "across all" not in confirm["confirm_message"]

    assert client.post(f"/api/review-queue/{item.id}/actions/confirm_successor", json={}).status_code == 200
    for c in (left, other_record, successor):
        db_session.refresh(c)
    assert left.has_left and other_record.has_left and not successor.has_left


def test_departure_without_candidate_points_to_the_real_button(client, db_session):
    left = _contact(db_session, "Paul Dowdy")
    item = _item(db_session, "departure_unconfirmed", entity=left, payload={"candidate": None})
    r = client.post(f"/api/review-queue/{item.id}/actions/confirm_successor", json={})
    assert r.status_code == 400 and "Assign different contact" in r.json()["detail"]


def test_mark_as_departed_marks_the_contact(client, db_session):
    left = _contact(db_session, "Paul Dowdy")
    successor = _contact(db_session, "Bhavisha Hartley")
    assert client.post(f"/api/contacts/{left.id}/reassign/{successor.id}").status_code == 204
    db_session.refresh(left)
    db_session.refresh(successor)
    assert left.has_left and not successor.has_left
    assert client.get(f"/api/contacts/{left.id}").json()["has_left"] is True
