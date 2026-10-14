"""Writing profiles (how each salesperson writes), learning from their edits, and the proposal requests report."""
import io
import uuid
from datetime import datetime, timedelta, timezone

import docx

from app.automations import llm
from app.automations import proposal_requests as pr
from app.models import ReviewQueueItem, SalesDeal, SalesRate, WritingProfile
from app.proposals import style
from tests.conftest import identity_headers, make_user
from tests.test_proposal_requests import _msg, tbtm  # noqa: F401 - fixture

KIRSTY = {
    "summary": "Warm and chatty, lots of examples, ends by offering a Teams call.",
    "tone": "warm", "length": "long", "greeting": "Hello {first_name},", "sign_off": "Warmest\n{my_first_name}",
    "output": "email", "uses_tables": False, "never": ["send a price without examples"],
    "prices": {"direct_discount_pct": 0.14},
    "situations": {"general": {"include": ["prices", "examples", "call_offer"], "opening": "Thanks for your email{for_client}, would be great to work with you.",
                               "closing": "Let me know if you want a Teams call."},
                   "full_proposal": {"include": ["stats", "examples"]}},
}


def test_profile_from_examples_shapes_replies(client, db_session, tbtm, monkeypatch):
    h = tbtm["h"]
    assert client.get("/api/proposal-style", headers=h).json()["status"] == "draft"
    # a Word file and a pasted email to learn from
    d = docx.Document()
    d.add_paragraph("Hi Tom, great to see you at the summit. Sponsored content is £3,250 for a single page. " * 3)
    buf = io.BytesIO()
    d.save(buf)
    r = client.post("/api/proposal-style/samples?name=tech_client.docx", content=buf.getvalue(), headers=h)
    assert r.status_code == 200, r.text
    r = client.post("/api/proposal-style/samples/paste", json={"name": "Agency reply", "text": "Hello Marta, thanks for your email. " * 10}, headers=h)
    assert len(r.json()["samples"]) == 2
    client.put("/api/proposal-style/notes", json={"notes": "Direct clients get my introductory rates."}, headers=h)

    seen = {}
    def fake(system, user, **kw):
        seen["user"] = user
        return {**KIRSTY, "situations": {**KIRSTY["situations"], "pr_pitch": {"include": ["prices"], "opening": "We charge £3,250 for that."}}}
    monkeypatch.setattr(llm, "is_configured", lambda: True)
    monkeypatch.setattr(llm, "extract_json", fake)
    built = client.post("/api/proposal-style/build", headers=h).json()
    assert "introductory rates" in seen["user"] and "great to see you at the summit" in seen["user"]
    prof = built["profile"]
    assert prof["prices"]["direct_discount_pct"] == 0.14 and prof["greeting"] == "Hello {first_name},"
    assert "£" not in prof["situations"]["pr_pitch"]["opening"]          # figures from someone's deal are never kept
    assert built["status"] == "draft"                                    # not used until saved
    assert client.put("/api/proposal-style", json={"profile": prof}, headers=h).json()["status"] == "ready"

    # a direct client's reply: her structure, voice and introductory prices
    monkeypatch.setattr(llm, "is_configured", lambda: False)
    info = {"request_type": "general", "wants": "a display advert", "agency": False, "contact_name": "Ana Lopes", "sector": "airline"}
    rates = pr.pick_rates(db_session, tbtm["title"], info["wants"])
    draft, _ = pr.compose(db_session, info, tbtm["title"], tbtm["user"], "Hi", rates, "Rates?")
    assert draft.splitlines()[2] == "Hello Ana," and "Thanks for your email, would be great to work with you." in draft
    assert "introductory rates" in draft and "£2,450" in draft and "£2,850" not in draft     # 14% off, to the nearest £50
    assert "**Examples of our work**" in draft and "Coming issues" not in draft
    assert draft.endswith("Warmest\nKirsty") and "Teams call" in draft
    # an agency gets the rate card
    draft, _ = pr.compose(db_session, {**info, "agency": True, "client_company": "Global"}, tbtm["title"], tbtm["user"], "Hi", rates, "Rates?")
    assert "£2,850" in draft and "introductory" not in draft


def test_the_brain_learns_what_you_take_out(client, db_session, tbtm):
    h = tbtm["h"]
    drafted = "Hi\n\n**Coming issues**\n- Spring\n\n**Examples of our work**\n- x\n\nKind regards,\nKirsty"
    sent = "Hi\n\n**Examples of our work**\n- x\n\nThanks so much\nKirsty x"
    for _ in range(2):
        style.record_edit(db_session, tbtm["user"].id, kind="reply", situation="general", drafted=drafted, sent=sent)
    assert not db_session.query(WritingProfile).filter_by(user_id=tbtm["user"].id).one().learned     # twice isn't a habit yet
    style.record_edit(db_session, tbtm["user"].id, kind="reply", situation="general", drafted=drafted, sent=sent)
    db_session.commit()
    learned = {x["key"]: x for x in client.get("/api/proposal-style", headers=h).json()["learned"]}
    assert learned["omit:issues"]["active"] and learned["sign_off"]["value"] == "Thanks so much\nKirsty x"
    prof = style.effective(db_session, tbtm["user"].id)
    assert "issues" not in prof["situations"]["agency_brief"]["include"] and prof["sign_off"] == "Thanks so much\nKirsty x"
    client.put("/api/proposal-style/learned/omit:issues", json={"active": False}, headers=h)
    db_session.expire_all()
    assert "issues" in style.effective(db_session, tbtm["user"].id)["situations"]["agency_brief"]["include"]


def test_new_proposals_follow_the_profile_and_learn(client, db_session, tbtm, monkeypatch):
    h = tbtm["h"]
    client.put("/api/proposal-style", json={"profile": KIRSTY}, headers=h)
    rate = db_session.query(SalesRate).filter_by(title_id=tbtm["title"].id, product="Full page").one()
    p = client.post("/api/proposals", json={"company_id": str(tbtm["company"].id), "title_id": str(tbtm["title"].id), "use_ai": False,
                                            "lines": [{"product": "Full page", "rate_id": str(rate.id), "source": "rate_card"}]}, headers=h).json()
    assert p["output"] == "email"
    assert [s["block"]["kind"] for s in p["sections"] if s.get("block")] == ["stats", "examples"]
    keep = [s for s in p["sections"] if (s.get("block") or {}).get("kind") != "stats"]
    client.patch(f"/api/proposals/{p['id']}", json={"sections": keep}, headers=h)
    client.post(f"/api/proposals/{p['id']}/finish", json={"via": "other"}, headers=h)
    wp = db_session.query(WritingProfile).filter_by(user_id=tbtm["user"].id).one()
    db_session.refresh(wp)
    assert wp.edits[-1]["kind"] == "proposal" and wp.edits[-1]["removed"] == ["stats"]


def test_report_counts_replies_speed_and_bookings(client, db_session, tbtm, monkeypatch):
    monkeypatch.setattr(llm, "is_configured", lambda: False)
    info = {"request_type": "agency_brief", "agency": True, "client_company": "Radisson Hotels", "contact_email": "a@radisson.test"}
    a = pr.queue(db_session, "kirsty.hicks@bmipublishing.co.uk", tbtm["user"], _msg(), info)
    b = pr.queue(db_session, "kirsty.hicks@bmipublishing.co.uk", tbtm["user"], _msg(), {**info, "request_type": "pr_pitch"})
    pr.queue(db_session, "kirsty.hicks@bmipublishing.co.uk", tbtm["user"], _msg(), info)
    db_session.flush()
    now = datetime.now(timezone.utc)
    a.created_at = now - timedelta(hours=5)
    a.status, a.resolved_action, a.reviewed_at, a.entity_type, a.entity_id = "approved", "send", now - timedelta(hours=3), "company", tbtm["company"].id
    b.status, b.resolved_action, b.reviewed_at = "rejected", "not_request", now
    db_session.add(SalesDeal(id=uuid.uuid4(), number=9001, status="confirmed", client_name="Radisson Hotels", company_id=tbtm["company"].id,
                             booked_on=now.date(), lines=[], split=[], total_gbp=9500))
    db_session.commit()
    rep = client.get("/api/proposal-report?days=30", headers=tbtm["h"]).json()
    row = rep["rows"][0]
    assert row["name"] == "Kirsty Hicks" and row["received"] == 3 and row["replied"] == 1 and row["not_requests"] == 1 and row["waiting"] == 1
    assert row["median_hours"] == 2.0 and row["bookings"] == 1 and row["booked_gbp"] == 9500
    assert rep["by_type"]["Agency brief"] == 2 and not rep["staff"]
    other = identity_headers(make_user(db_session, role="sales"))
    assert client.get("/api/proposal-report?days=30", headers=other).json()["rows"] == []
