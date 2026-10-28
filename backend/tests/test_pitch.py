"""SALES-023 - meeting notes to a pitch (app/proposals/pitch.py)."""
import uuid
from datetime import date, datetime, timezone

from app.automations import llm
from app.models import CallRecording, Contact, Proposal, ReviewQueueItem
from app.proposals import pitch
from tests.conftest import identity_headers
from tests.test_proposals import world  # noqa: F401 - fixture

NOTES = ("Sarah at Delta wants to reach UK corporate travel buyers before their new Heathrow lounge opens in spring. "
         "Liked the idea of a sponsored feature on premium lounges and a newsletter. Budget about £8,000, decides in November. "
         "Mentioned her divorce is going through - not for the pitch.")

BRIEF = {"enough": True, "situation": "Delta is opening a new Heathrow lounge in spring and wants UK buyers to know before it opens.",
         "angle": "Get the lounge in front of decision makers ahead of opening.",
         "resonant_points": ["sponsored feature on premium lounges", "newsletter"], "client_quotes": ["we want buyers to see it first"],
         "budget_signals": ["about £8,000", "decides in November"], "magazine": "OBH", "wants": "sponsored feature and newsletter", "left_out": 1}


def _fake_llm(monkeypatch, seen):
    monkeypatch.setattr(llm, "is_configured", lambda: True)

    def fake(system, user, **kw):
        if kw.get("purpose") == "pitch_brief":
            return BRIEF
        if kw.get("purpose") == "proposal_revise":
            seen["instruction"] = user
            return {"summary": "Tailored.", "sections": [
                {"kind": "intro", "heading": "Your new Heathrow lounge", "body": "Get it in front of UK buyers before it opens."},
                {"kind": "proposal", "heading": "Our idea", "body": "A sponsored feature on premium lounges, plus the newsletter."},
                {"kind": "investment", "heading": "Investment", "body": "All prices are before VAT."},
                {"kind": "next_steps", "heading": "Next steps", "body": "- Agree the issue before November"}]}
        return None
    monkeypatch.setattr(llm, "extract_json", fake)


def test_pitch_from_pasted_notes_answers_the_meeting_and_keeps_figures_out(client, world, monkeypatch, db_session):
    seen = {}
    _fake_llm(monkeypatch, seen)
    # a pitch we sent before that matches the brief
    past = Proposal(id=uuid.uuid4(), company_id=world["company"].id, title_id=world["title"].id, template="obh", campaign_name="Lounge launch 2025",
                    status="sent", sent_at=datetime(2025, 3, 1, tzinfo=timezone.utc), lines=[], total_gbp=0, context={}, flags=[],
                    sections=[{"id": "a", "kind": "proposal", "heading": "Premium lounges", "body": "A sponsored feature on premium lounges reaching 12,000 buyers for £3,900."}])
    db_session.add(past)
    db_session.flush()
    r = client.post("/api/proposals/from-notes", json={"company_id": str(world["company"].id), "notes": NOTES}, headers=world["h"])
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["sections"][0]["heading"] == "Your new Heathrow lounge" and out["status"] == "draft"
    assert out["context"]["pitch"]["source_proposal_ids"] == [str(past.id)]
    assert any(f.startswith("Made from your meeting notes") for f in out["flags"])
    assert any("Left out 1 remark" in f for f in out["flags"])
    # the budget from the call and the old pitch's figures never reach the Brain
    assert "8,000" not in seen["instruction"] and "3,900" not in seen["instruction"] and "12,000" not in seen["instruction"]
    assert "premium lounges" in seen["instruction"]


def test_thin_notes_and_no_brain_are_refused_plainly(client, world, monkeypatch):
    r = client.post("/api/proposals/from-notes", json={"company_id": str(world["company"].id), "notes": "Good chat."}, headers=world["h"])
    assert r.status_code == 422 and "too short" in r.json()["detail"]
    monkeypatch.setattr(llm, "is_configured", lambda: False)
    r = client.post("/api/proposals/from-notes", json={"company_id": str(world["company"].id), "notes": NOTES}, headers=world["h"])
    assert r.status_code == 422 and "isn't switched on" in r.json()["detail"]
    monkeypatch.setattr(llm, "is_configured", lambda: True)
    monkeypatch.setattr(llm, "extract_json", lambda *a, **k: {**BRIEF, "enough": False})
    r = client.post("/api/proposals/from-notes", json={"company_id": str(world["company"].id), "notes": NOTES}, headers=world["h"])
    assert r.status_code == 422 and "don't say enough" in r.json()["detail"]


def test_pitch_from_a_call_and_from_its_card(client, world, monkeypatch, db_session):
    from app.automations import call_notes
    seen = {}
    _fake_llm(monkeypatch, seen)
    me = world["user"]
    ct = Contact(id=uuid.uuid4(), source_db="onboardhospitality", source_act_id=str(uuid.uuid4()), full_name="Sarah Jones",
                 company_id=world["company"].id)
    db_session.add(ct)
    call = CallRecording(id=uuid.uuid4(), user_id=me.id, meeting_url="https://meet.google.com/abc-defg-hij", title="Lounge chat",
                         status="completed", ended_at=datetime(2026, 10, 14, 15, 0, tzinfo=timezone.utc),
                         contact_id=ct.id, notes={"summary": NOTES, "key_points": ["Wants buyers to see the lounge first"]})
    db_session.add(call)
    db_session.flush()
    r = client.post(f"/api/calls/{call.id}/pitch", headers=identity_headers(me))
    assert r.status_code == 200, r.text
    pid = r.json()["proposal_id"]
    prop = db_session.get(Proposal, uuid.UUID(pid))
    assert prop.context["pitch"]["call_id"] == str(call.id) and prop.notes.startswith("Pitch from the call on 14 Oct 2026")
    assert client.get(f"/api/calls/{call.id}", headers=identity_headers(me)).json()["pitch_proposal_id"] == pid

    # the Review Queue card: Save and make a pitch saves the notes to history too
    call2 = CallRecording(id=uuid.uuid4(), user_id=me.id, meeting_url="https://meet.google.com/xyz", title="Second chat", status="completed",
                          company_id=world["company"].id, contact_id=ct.id, notes={"summary": NOTES})
    db_session.add(call2)
    db_session.flush()
    call_notes.queue_for_review(db_session, call2)
    db_session.flush()
    card = db_session.query(ReviewQueueItem).filter(ReviewQueueItem.kind == "call_notes",
                                                    ReviewQueueItem.payload["call_id"].astext == str(call2.id)).one()
    r = client.post(f"/api/review-queue/{card.id}/actions/pitch", json={}, headers=identity_headers(me))
    assert r.status_code == 200, r.text
    db_session.refresh(card)
    db_session.refresh(call2)
    assert card.payload["open_href"].startswith("/sales/proposals/") and call2.saved_to_history_at is not None


def test_strip_figures_and_similarity():
    assert pitch.strip_figures("£8,000 by 1 Nov, 15% off") == "[figure] by [figure] Nov, [figure] off"
    assert date.today()   # keeps the import used
