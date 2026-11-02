"""SALES-030: replies to a mail merge asking to unsubscribe, or pointing to a colleague."""
import uuid
from datetime import datetime, timedelta, timezone

from tests.conftest import identity_headers, make_user
from tests.test_news_and_followups import _company
from tests.test_sales_orders import _NoCloseSession

from app import graph_client
from app.automations import campaign_replies as cr
from app.automations import llm
from app.automations.mail_parsing import ParsedMessage
from app.models import Contact, Email, Note, ReviewQueueItem
from app.models.messaging import MailMerge, MailMergeRecipient

NOW = datetime.now(timezone.utc)
FOOTER = "\n\nOn Mon, 2 Nov 2026 Sally Parker wrote:\n> Space in May is going fast.\n> To unsubscribe, just reply."


def _msg(body, sender, name="Jo", subject="Re: Our May issue", to=None, hours_ago=1):
    return ParsedMessage(message_id=uuid.uuid4().hex, internet_message_id=None, from_address=sender, from_name=name, subject=subject,
                         received_at=NOW - timedelta(hours=hours_ago), body_text=body, to_addresses=to or ["sally@bmi.example"])


def test_own_words_and_classify():
    assert cr.own_words("Please remove me." + FOOTER) == "Please remove me."
    assert cr.classify(_msg("Thanks, sounds good. Call me Tuesday." + FOOTER, "a@x.example")) is None    # footer's "unsubscribe" ignored
    assert cr.classify(_msg("Please take me off your mailing list." + FOOTER, "a@x.example")) == cr.UNSUB
    assert cr.classify(_msg("I'd rather not. Stop emailing me.", "a@x.example")) == cr.UNSUB
    assert cr.classify(_msg("Unsubscribe", "a@x.example", subject="Unsubscribe")) == cr.UNSUB
    assert cr.classify(_msg("Hi Sally, the best person to speak to is Tom Reed (tom@visitmalta.example), our marketing manager." + FOOTER,
                            "a@x.example")) == cr.REFERRAL
    assert cr.classify(_msg("I've copied in my colleague who handles this.", "a@x.example")) == cr.REFERRAL
    ooo = _msg("I am out of the office until Monday with limited access to email.", "a@x.example", subject="Automatic reply: Our May issue")
    assert cr.classify(ooo) is None


def _setup(db):
    sally = make_user(db, role="sales", name="Sally")
    jo_co, jo = _company(db, "Visit Malta", person="Jo", email="jo@visitmalta.example")
    _, amy = _company(db, "Amy Travel", person="Amy", email="amy@amytravel.example")
    _, bob = _company(db, "Bob Tours", person="Bob", email="bob@bobtours.example")
    m = MailMerge(id=uuid.uuid4(), created_by_user_id=sally.id, output="email", source_label="Group: Agents", subject="Our May issue",
                  body="Space in May is going fast.", from_email="sally@bmi.example", status="done", total=3, sent=3,
                  created_at=NOW - timedelta(days=2), finished_at=NOW - timedelta(days=2))
    db.add(m)
    db.flush()
    for c in (jo, amy, bob):
        db.add(MailMergeRecipient(id=uuid.uuid4(), merge_id=m.id, contact_id=c.id, email=c.full_name.lower() + "@" +
                                  {"Jo": "visitmalta", "Amy": "amytravel", "Bob": "bobtours"}[c.full_name] + ".example",
                                  status="sent", sent_at=m.created_at))
    db.commit()
    return sally, m, jo, amy, bob, jo_co


def test_scan_makes_cards_for_the_sender_and_buttons_work(client, db_session, monkeypatch):
    sally, m, jo, amy, bob, jo_co = _setup(db_session)
    inbox = [
        _msg("Hi Sally, the best person to speak to is Tom Reed, our marketing manager: tom.reed@visitmalta.example" + FOOTER,
             "jo@visitmalta.example"),
        _msg("Please remove me from your list." + FOOTER, "amy@amytravel.example", name="Amy"),
        _msg("Sounds interesting, send me the rates." + FOOTER, "bob@bobtours.example", name="Bob"),
        _msg("Please unsubscribe me.", "stranger@else.example"),                     # not someone the merge reached
        _msg("Please unsubscribe me.", "bob@bobtours.example", hours_ago=24 * 5),    # before the merge went out
    ]
    monkeypatch.setattr(cr, "SessionLocal", lambda: _NoCloseSession(db_session))
    monkeypatch.setattr(cr, "parse_message", lambda r: r)
    monkeypatch.setattr(graph_client, "list_messages_since", lambda box, since, **kw: inbox)
    monkeypatch.setattr(llm, "extract_json", lambda *a, **k: {"name": "Tom Reed", "role": "Marketing manager",
                                                                "email": "tom.reed@visitmalta.example"})
    cr.scan()
    cr.scan()   # nothing twice
    unsub = db_session.query(ReviewQueueItem).filter_by(kind=cr.UNSUB).one()
    ref = db_session.query(ReviewQueueItem).filter_by(kind=cr.REFERRAL).one()
    assert unsub.payload["summary"] == "Amy asked to be taken off your emails"
    assert unsub.payload["original_text"] == "Please remove me from your list."
    assert ref.payload["summary"] == "Jo says to contact Tom Reed instead"
    assert ref.payload["field_defaults"] == {"full_name": "Tom Reed", "email": "tom.reed@visitmalta.example", "job_title": "Marketing manager"}
    hrefs = {d.get("href") for d in ref.payload["details"]}
    assert {f"/contacts/{jo.id}", f"/companies/{jo_co.id}", f"/mail-merge/{m.id}"} <= hrefs

    # only Sally sees them
    other = make_user(db_session, role="sales")
    see = lambda u: {i["id"] for i in client.get("/api/review-queue?status=pending", headers=identity_headers(u, access=[("sellingtravel", None)])).json()["items"]}
    assert {str(unsub.id), str(ref.id)} <= see(sally) and not ({str(unsub.id), str(ref.id)} & see(other))

    h = identity_headers(sally, access=[("sellingtravel", None)])
    r = client.post(f"/api/review-queue/{unsub.id}/actions/unsubscribe", json={}, headers=h)
    assert r.status_code == 200, r.text
    db_session.expire_all()
    assert db_session.get(Contact, amy.id).is_unsubscribed
    assert any(d["label"] == "Brevo" and "by hand" in d["value"] for d in r.json()["payload"]["details"])

    r = client.post(f"/api/review-queue/{ref.id}/actions/add_contact",
                    json={"fields": {"full_name": "Tom Reed", "email": "tom.reed@visitmalta.example", "job_title": "Marketing manager"}}, headers=h)
    assert r.status_code == 200, r.text
    tom = db_session.query(Contact).filter_by(full_name="Tom Reed").one()
    assert tom.company_id == jo.company_id and tom.job_title == "Marketing manager"
    assert db_session.query(Email).filter_by(contact_id=tom.id).one().address == "tom.reed@visitmalta.example"
    assert db_session.query(Note).filter_by(entity_id=jo.id, note_type="Mail merge reply").count() == 1


def test_referral_without_the_brain_uses_the_address_in_the_reply(db_session):
    msg = _msg("Please contact my colleague anna@visitmalta.example about this.", "jo@visitmalta.example",
               to=["sally@bmi.example", "ops@visitmalta.example"])
    who = cr.referred(msg, {"bmi.example"}, use_brain=False)
    assert who["email"] == "anna@visitmalta.example" and who["name"] is None and not who["ai"]
    copied = cr.referred(_msg("I've copied in my colleague.", "jo@visitmalta.example", to=["sally@bmi.example", "ops@visitmalta.example"]),
                         {"bmi.example"}, use_brain=False)
    assert copied["email"] == "ops@visitmalta.example"
