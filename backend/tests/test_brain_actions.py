"""Phase 4: the Brain's actions. Each tool only makes a card; it runs on Confirm, as the person, checked again."""
import uuid

import pytest
from tests.conftest import make_user
from tests.test_brain_data import Ctx, _Shared
from tests.test_orders import w  # noqa: F401 - fixture

from app.brain import actions, registry, tools  # noqa: F401 (registers the tools)
from app.core.identity import Identity
from app.models import BrainAction, Contact, HistoryEntry, Note, ReviewQueueItem


def ident(user, access=None):
    return Identity(user_id=str(user.id), role=user.role, access=access or [])


@pytest.fixture
def run(w, monkeypatch):
    db = w["db"]
    monkeypatch.setattr(registry, "session_factory", lambda: _Shared(db))

    def call(tool, user, access=None, **kw):
        return registry.TOOLS[tool].adk_fn(tool_context=Ctx(ident(user, access)), **kw)
    return call


@pytest.fixture
def people(w):
    db = w["db"]
    admin, sally = make_user(db, role="admin", name="Ahmed"), make_user(db, role="sales", name="Sally Parker")
    daniel = Contact(id=uuid.uuid4(), source_db="onboardhospitality", source_act_id="d1", first_name="Daniel", last_name="Weber",
                     full_name="Daniel Weber", custom_fields={})
    other = Contact(id=uuid.uuid4(), source_db="sellingtravel", source_act_id="o1", first_name="Olga", last_name="Weber",
                    full_name="Olga Weber", custom_fields={})
    db.add_all([daniel, other])
    db.flush()
    return {"db": db, "admin": admin, "sales": sally, "daniel": daniel, "other": other}


def last_card(db) -> BrainAction:
    return db.query(BrainAction).filter_by(status="pending").order_by(BrainAction.created_at.desc()).first()


def test_a_note_and_a_call_are_saved_only_on_confirm(run, people):
    db, sally, daniel = people["db"], people["sales"], people["daniel"]
    mine = [("onboardhospitality", None)]
    out = run("propose_log", sally, access=mine, client="Daniel Weber", text="Wants the spring issue")
    assert out["card"] == "Add a note" and db.query(Note).filter_by(entity_id=daniel.id).count() == 0
    a = actions.decide(db, ident(sally, mine), sally, str(last_card(db).id), True)
    assert a.status == "done" and a.result["links"][0]["href"] == f"/contacts/{daniel.id}"
    note = db.query(Note).filter_by(entity_id=daniel.id).one()
    assert note.body == "Wants the spring issue" and note.created_by_user_id == sally.id

    run("propose_log", sally, access=mine, client="Daniel Weber", text="Back on Friday", what="call", outcome="left message")
    a = actions.decide(db, ident(sally, mine), sally, str(last_card(db).id), True)
    assert a.status == "done", a.result
    assert db.query(HistoryEntry).filter_by(entity_id=daniel.id).one().history_type == "Call Left Message"


def test_only_records_the_person_can_see_and_ambiguous_names_ask(run, people):
    sally = people["sales"]
    mine = [("onboardhospitality", None)]
    assert "No contact or company matches" in run("propose_log", sally, access=mine, client="Olga Weber", text="x")["error"]
    out = run("propose_log", people["admin"], client="Weber", text="x")
    assert "More than one match" in out["error"] and "Daniel Weber" in out["error"] and "Olga Weber" in out["error"]


def test_email_needs_outlook_and_cancel_changes_nothing(run, people):
    db, sally = people["db"], people["sales"]
    mine = [("onboardhospitality", None)]
    out = run("propose_email", sally, access=mine, person="Daniel Weber", subject="Spring", body="Hello")
    assert "Outlook isn't connected" in out["error"]
    run("propose_reminder", sally, access=mine, when="2099-01-05", note="Chase Daniel", client="Daniel Weber")
    card = last_card(db)
    assert card.preview["lines"][0] == ["When", "Mon 5 Jan 2099, 09:00"]
    a = actions.decide(db, ident(sally, mine), sally, str(card.id), False)
    assert a.status == "cancelled"
    from app.models import Reminder
    assert db.query(Reminder).count() == 0
    assert "already passed" in run("propose_reminder", sally, when="2001-01-01", note="x")["error"]


def test_review_card_decision_and_automation_switch(run, people):
    db, admin, sally = people["db"], people["admin"], people["sales"]
    item = ReviewQueueItem(id=uuid.uuid4(), kind="duplicate_contact", status="pending", entity_type="contact", entity_id=people["daniel"].id,
                           payload={"summary": "Two Webers", "candidate": {"contact_id": str(people["other"].id)}})
    db.add(item)
    db.flush()
    assert "needs choices only the card" in run("propose_review_decision", admin, card_id=str(item.id), button="Merge records")["error"]
    run("propose_review_decision", admin, card_id=str(item.id), button="Keep as separate contacts")
    assert db.get(ReviewQueueItem, item.id).status == "pending"
    a = actions.decide(db, ident(admin), admin, str(last_card(db).id), True)
    assert a.status == "done", a.result
    assert db.get(ReviewQueueItem, item.id).resolved_action == "not_duplicate"

    assert "Only administrators" in run("propose_automation_switch", sally, automation="Reminders fire", on=False)["error"]
    run("propose_automation_switch", admin, automation="Reminders fire", on=False)
    card = last_card(db)
    # someone else can't confirm it, and it's checked again when confirmed
    with pytest.raises(actions.ActionError):
        actions.decide(db, ident(sally), sally, str(card.id), True)
    a = actions.decide(db, ident(admin), admin, str(card.id), True)
    from app.automations import runtime_settings
    assert a.status == "done" and runtime_settings.effective_value(db, "automations_reminders_scan_enabled") is False
