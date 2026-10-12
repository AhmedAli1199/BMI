"""SALES-022: a client's "no" becomes a drafted reply with a rule-based alternative, for the salesperson to send."""
import uuid
from datetime import date, datetime, timedelta, timezone

from tests.conftest import identity_headers, make_user

import app.automations.save_the_sale as sts
from app.automations.email_summary import decline_reason
from app.models import Company, Contact, Email, EmailSignal, Note, ReviewQueueItem, SalesEdition, SalesOrder, SalesRate, SalesRep, SalesTitle
from app.models.messaging import MailTemplate
from app.sales.reference import ensure_reference_data


class _NoClose:
    def __init__(self, s):
        self._s = s

    def __getattr__(self, k):
        return getattr(self._s, k)

    def close(self):
        pass


def _world(db, reason="budget", said="Sorry, no budget for print this year."):
    ensure_reference_data(db)
    title = db.query(SalesTitle).filter_by(slug="obh").one()
    rep = db.query(SalesRep).filter_by(code="SW").one()
    today = date.today()
    co = Company(id=uuid.uuid4(), name="Gate Gourmet", source_db="onboard", source_act_id=str(uuid.uuid4()))
    db.add(co)
    db.flush()
    c = Contact(id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()), first_name="Ana", last_name="Lee",
                full_name="Ana Lee", company_id=co.id)
    db.add(c)
    db.flush()
    db.add(Email(id=uuid.uuid4(), contact_id=c.id, address="ana@gate.example", source_db="onboard", source_act_id=str(uuid.uuid4())))
    old = SalesEdition(id=uuid.uuid4(), title_id=title.id, year=today.year, name="105", edition_date=today - timedelta(days=60))
    nxt = SalesEdition(id=uuid.uuid4(), title_id=title.id, year=today.year, name="108", edition_date=today + timedelta(days=50),
                       ad_deadline=today + timedelta(days=30))
    db.add_all([old, nxt])
    db.flush()
    db.add(SalesOrder(id=uuid.uuid4(), edition_id=old.id, client_name="Gate Gourmet", company_id=co.id, value_gbp=2990, rep_id=rep.id,
                      size="FP", status="booked"))
    for prod, price in (("Full page", 2990), ("Half page", 1600), ("Quarter page", 950)):
        db.add(SalesRate(id=uuid.uuid4(), title_id=title.id, year=today.year, section="print", product=prod, price_gbp=price))
    sig = EmailSignal(id=uuid.uuid4(), contact_id=c.id, signal_type="decline", summary=said, reason=reason,
                      source_thread_id=str(uuid.uuid4()), source_message_id=str(uuid.uuid4()), source_snippet=said, confidence=0.9,
                      created_at=datetime.now(timezone.utc))
    db.add(sig)
    db.flush()
    return {"contact": c, "company": co, "signal": sig, "next": nxt, "rep": rep}


def test_reason_rules():
    assert decline_reason(None, "we simply can't afford it this year") == "budget"
    assert decline_reason(None, "We've gone with another magazine") == "competitor"
    assert decline_reason("timing", "x") == "timing" and decline_reason("nonsense", "hello") == "other"


def test_no_budget_offers_a_cheaper_size_from_the_rate_card(db_session, monkeypatch):
    monkeypatch.setattr(sts, "SessionLocal", lambda: _NoClose(db_session))
    monkeypatch.setattr(sts, "is_configured", lambda: False)
    w = _world(db_session)
    sts.scan_declines()
    sts.scan_declines()   # once per signal
    items = db_session.query(ReviewQueueItem).filter_by(kind="save_the_sale").all()
    assert len(items) == 1
    p = items[0].payload
    assert p["alternatives"][0]["label"] == "Half page (£1,600)" and "Quarter page" in p["alternatives"][1]["label"]
    assert "half page in OnBoard Hospitality (OBH) is £1,600" in p["original_text"] and p["original_text"].startswith("Subject:")
    assert "Hi Ana" in p["original_text"] and p["suggested_to"] == "ana@gate.example"
    hrefs = {d["key"]: d.get("href") for d in p["details"]}
    assert hrefs["contact"] == f"/contacts/{w['contact'].id}" and hrefs["company"] == f"/companies/{w['company'].id}"
    assert hrefs["last"].startswith("/sales/orders/") and p["facets"]["reason"] == "No budget"
    assert db_session.query(MailTemplate).filter_by(kind="save_sale").count() == 5   # defaults loaded for BMI to edit
    # Regenerate moves to the next option
    new = sts._redraft(db_session, items[0], "")
    assert "quarter page" in new.lower()


def test_timing_offers_the_next_issue_and_let_go_records_it(client, db_session, monkeypatch):
    monkeypatch.setattr(sts, "SessionLocal", lambda: _NoClose(db_session))
    monkeypatch.setattr(sts, "is_configured", lambda: False)
    w = _world(db_session, reason="timing", said="The timing doesn't work for us this issue.")
    sts.scan_declines()
    item = db_session.query(ReviewQueueItem).filter_by(kind="save_the_sale").one()
    assert item.payload["alternatives"][0]["href"] == f"/sales/editions/{w['next'].id}" and "108" in item.payload["original_text"]
    h = identity_headers(make_user(db_session, role="admin"))
    db_session.commit()
    r = client.post(f"/api/review-queue/{item.id}/actions/let_go", headers=h, json={"note": "Spending moved to events"})
    assert r.status_code == 200, r.text
    db_session.expire_all()
    note = db_session.query(Note).filter_by(entity_id=w["contact"].id, note_type="Declined").one()
    assert "Timing doesn't work" in note.body and "events" in note.body
    assert db_session.get(EmailSignal, w["signal"].id).status == "dismissed"


def test_competitor_offers_nothing_and_ai_cannot_add_figures(db_session, monkeypatch):
    monkeypatch.setattr(sts, "SessionLocal", lambda: _NoClose(db_session))
    monkeypatch.setattr(sts, "is_configured", lambda: True)
    monkeypatch.setattr(sts, "draft_text", lambda *a, **k: "Subject: Re: OBH\n\nHi Ana, how about 20% off at £999?")
    _world(db_session, reason="competitor", said="We've gone with another magazine this year.")
    sts.scan_declines()
    p = db_session.query(ReviewQueueItem).filter_by(kind="save_the_sale").one().payload
    assert p["alternatives"] == [] and "999" not in p["original_text"] and "tipped the balance" in p["original_text"]
