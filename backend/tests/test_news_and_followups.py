"""SALES-031 news campaigns and SALES-032 mail merge follow-ups."""
import uuid
from datetime import date, datetime, timedelta, timezone

from tests.conftest import identity_headers, make_user
from tests.test_sales_orders import _NoCloseSession

from app.automations import llm, merge_followups as mf, news_campaigns as nc
from app.models import Address, Company, Contact, Email, Note, ReviewQueueItem, SalesOrder
from app.models.messaging import MailMerge, MailMergeRecipient

NOW = datetime.now(timezone.utc)
ATOM = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Travel Advice Summary</title>
<entry><id>https://www.gov.uk/foreign-travel-advice/greece#1</id><updated>{NOW.isoformat()}</updated>
<link rel="alternate" type="text/html" href="https://www.gov.uk/foreign-travel-advice/greece"/><title>Greece</title>
<summary type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml"><p>The FCDO no longer advises against travel to the islands.</p></div></summary></entry>
<entry><id>https://www.gov.uk/foreign-travel-advice/spain#2</id><updated>{NOW.isoformat()}</updated>
<link rel="alternate" href="https://www.gov.uk/foreign-travel-advice/spain"/><title>Spain</title>
<summary>New information following a rail collision.</summary></entry>
</feed>""".encode()
RSS = b"""<rss><channel><item><title>Airline resumes Gatwick to Crete flights</title><link>https://news.example/1</link>
<guid>n-1</guid><description>&lt;p&gt;Flights restart in May.&lt;/p&gt;</description><pubDate>Tue, 27 Oct 2026 09:00:00 GMT</pubDate></item></channel></rss>"""
MOMENT = {"selling_moment": True, "why": "Greece is open again.", "headline": "Greece reopens to UK visitors",
          "destinations": ["Greece"], "search_terms": ["Greece", "Greek", "Crete"], "sectors": ["tourist board", "airline"],
          "magazine": "Selling Travel", "angle": "Agents can sell Greece again."}


def _company(db, name, *, person="Ana", title=None, email=None, industry=None, country=None, unsub=False):
    co = Company(id=uuid.uuid4(), source_db="sellingtravel", source_act_id=uuid.uuid4().hex, name=name, industry=industry)
    db.add(co)
    db.flush()
    c = Contact(id=uuid.uuid4(), source_db="sellingtravel", source_act_id=uuid.uuid4().hex, full_name=person, first_name=person,
                job_title=title, company_id=co.id, is_unsubscribed=unsub, custom_fields={})
    db.add(c)
    db.flush()
    db.add(Email(id=uuid.uuid4(), source_db="sellingtravel", source_act_id=uuid.uuid4().hex, contact_id=c.id,
                 address=email or f"{person.lower()}@{uuid.uuid4().hex[:6]}.example", is_primary=True))
    if country:
        db.add(Address(id=uuid.uuid4(), source_db="sellingtravel", source_act_id=uuid.uuid4().hex, company_id=co.id, country=country))
    db.flush()
    return co, c


# ---- SALES-031 ------------------------------------------------------------------------------------------

def test_reading_feeds_and_the_word_check():
    items = nc.parse_feed(ATOM)
    assert [i["title"] for i in items] == ["Greece", "Spain"]
    assert items[0]["link"] == "https://www.gov.uk/foreign-travel-advice/greece" and "no longer advises" in items[0]["summary"]
    assert nc.worth_a_look(items[0]) and not nc.worth_a_look(items[1])     # a warning isn't a moment
    rss = nc.parse_feed(RSS)
    assert rss[0]["summary"] == "Flights restart in May." and rss[0]["published"].year == 2026
    assert nc.parse_feed(b'<!DOCTYPE x [<!ENTITY a "b">]><rss/>') == [] and nc.parse_feed(b"not xml") == []
    assert nc.feed_name("https://www.gov.uk/foreign-travel-advice.atom") == "GOV.UK travel advice"


def test_news_becomes_a_campaign_with_the_right_companies(client, db_session, monkeypatch):
    board, ana = _company(db_session, "Greek National Tourism Organisation", person="Ana", title="PR Officer", industry="Tourist board")
    _, mia = _company(db_session, "Greek National Tourism Organisation UK", person="Mia", title="Trade Marketing Manager")
    db_session.query(Contact).filter_by(id=mia.id).update({"company_id": board.id})   # two people at one company: marketing wins
    _company(db_session, "Aegean Sun Airways", person="Leo", country="Greece", industry="Airline")
    _company(db_session, "Hellas Tours", person="Zoe", unsub=True)                  # nobody emailable
    _company(db_session, "Iceland Escapes", person="Kai")                         # not linked to the news
    db_session.commit()

    monkeypatch.setattr(nc, "SessionLocal", lambda: _NoCloseSession(db_session))
    monkeypatch.setattr(nc, "fetch", lambda url: nc.parse_feed(ATOM))
    monkeypatch.setattr(llm, "is_configured", lambda: True)
    asked = []
    monkeypatch.setattr(llm, "extract_json", lambda *a, **k: asked.append(a[1]) or MOMENT)
    monkeypatch.setattr(llm, "draft_text", lambda *a, **k: "Greece has 40 new routes this year.")   # a figure: dropped
    nc.scan()
    nc.scan()   # the same news isn't looked at twice
    assert len(asked) == 1 and "Greece" in asked[0]                               # only the good news reached the Brain
    item = db_session.query(ReviewQueueItem).filter_by(kind="news_campaign").one()
    p = item.payload
    leo = db_session.query(Contact).filter_by(full_name="Leo").one()
    assert set(p["merge"]["contact_ids"]) == {str(mia.id), str(leo.id)}   # one per company; nobody unsubscribed or unrelated
    assert str(ana.id) not in p["merge"]["contact_ids"]
    assert p["facets"]["source"] == "GOV.UK travel advice" and p["facets"]["companies"] == "Companies found"
    assert any(d.get("href") == f"/companies/{board.id}" for d in p["details"])
    assert any(d.get("href") == "https://www.gov.uk/foreign-travel-advice/greece" for d in p["details"])
    assert "40" not in p["original_text"] and "{{salutation|colleague}}" in p["merge"]["body"]

    h = identity_headers(make_user(db_session, role="sales"), access=[("sellingtravel", None)])
    r = client.post(f"/api/review-queue/{item.id}/actions/open_merge", json={}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["payload"]["open_href"] == f"/mail-merge?review={item.id}"


def test_no_brain_no_campaign_and_no_companies_no_button(db_session, monkeypatch):
    monkeypatch.setattr(llm, "is_configured", lambda: False)
    assert nc.judge({"title": "Greece", "summary": "reopens", "source": "x"}) is None
    item = nc.queue(db_session, {"id": "n", "title": "Ruritania reopens", "summary": "", "link": None, "published": NOW, "source": "x"},
                    {**MOMENT, "destinations": ["Ruritania"], "search_terms": ["Ruritania"]}, 60)
    assert item.payload["hidden_actions"] == ["open_merge"] and item.payload["facets"]["companies"] == "None found"


# ---- SALES-032 ------------------------------------------------------------------------------------------

def _merge(db, sender, people, *, days_ago=12, label="Group: Agents", sent=None):
    m = MailMerge(id=uuid.uuid4(), created_by_user_id=sender.id, output="email", source_label=label, subject="Our May issue",
                  body="Dear {{first_name}},\n\nSpace in May is going fast.", from_email="sally@bmi.example", status="done",
                  total=len(people), sent=sent if sent is not None else len(people),
                  created_at=NOW - timedelta(days=days_ago), finished_at=NOW - timedelta(days=days_ago))
    db.add(m)
    db.flush()
    for c, email in people:
        db.add(MailMergeRecipient(id=uuid.uuid4(), merge_id=m.id, contact_id=c.id, email=email, status="sent", sent_at=m.created_at))
    db.flush()
    return m


def test_followups_leave_out_who_answered_and_go_to_the_sender(client, db_session, monkeypatch):
    sally = make_user(db_session, role="sales", name="Sally")
    people = {}
    for name in ("Quiet", "Replied", "Booked", "Bounced", "Noted", "Quiet2", "Gone"):
        co, c = _company(db_session, f"{name} Ltd", person=name, email=f"{name.lower()}@x.example")
        people[name] = (co, c)
    people["Gone"][1].is_unsubscribed = True
    from app.models import SalesEdition, SalesTitle
    from app.sales.reference import ensure_reference_data
    ensure_reference_data(db_session)
    title = db_session.query(SalesTitle).filter_by(slug="selling-travel").one()
    ed = SalesEdition(id=uuid.uuid4(), title_id=title.id, year=date.today().year, name="T1", edition_date=date.today())
    db_session.add(ed)
    db_session.flush()
    db_session.add(SalesOrder(id=uuid.uuid4(), edition_id=ed.id, company_id=people["Booked"][0].id, client_name="Booked Ltd", booked_on=date.today()))
    db_session.add(Note(id=uuid.uuid4(), source_db="manual", source_act_id=uuid.uuid4().hex, entity_type="contact",
                        entity_id=people["Noted"][1].id, note_type="Call", body="Rang her", act_created_at=NOW - timedelta(days=2)))
    m = _merge(db_session, sally, [(c, f"{n.lower()}@x.example") for n, (_, c) in people.items()])
    _merge(db_session, sally, [(people["Quiet"][1], "quiet@x.example")] * 5, label=mf.FOLLOW_UP_LABEL + "Agents")   # a follow-up itself
    _merge(db_session, sally, [(people["Quiet"][1], "quiet@x.example")] * 5, days_ago=3)                          # too soon
    db_session.commit()

    monkeypatch.setattr(mf, "SessionLocal", lambda: _NoCloseSession(db_session))
    monkeypatch.setattr(mf, "replied_addresses", lambda box, since: ({"replied@x.example"}, {"bounced@x.example"}))
    mf.scan()
    mf.scan()   # one card per mail merge
    item = db_session.query(ReviewQueueItem).filter_by(kind="merge_followup").one()
    p = item.payload
    left = {db_session.get(Contact, uuid.UUID(i)).full_name for i in p["merge"]["contact_ids"]}
    assert left == {"Quiet", "Quiet2"}
    assert any(d["label"] == "Left out" and "1 replied" in d["value"] and "1 booked" in d["value"] and "2 bounced or unsubscribed" in d["value"]
               and "1 talked to since" in d["value"] for d in p["details"])
    assert p["merge"]["label"].startswith(mf.FOLLOW_UP_LABEL) and p["merge"]["subject"] == "Re: Our May issue"
    assert "Space in May is going fast." in p["merge"]["body"] and any(d.get("href") == f"/mail-merge/{m.id}" for d in p["details"])
    assert p["facets"]["replies"] == "Replies checked" and p["owner_user_id"] == str(sally.id)

    # only the person who sent it sees it
    other = make_user(db_session, role="sales")
    ids = lambda u: [i["id"] for i in client.get("/api/review-queue?kind=merge_followup",
                                                  headers=identity_headers(u, access=[("sellingtravel", None)])).json()["items"]]
    assert str(item.id) in ids(sally) and str(item.id) not in ids(other)
    r = client.post(f"/api/review-queue/{item.id}/actions/open_merge", json={}, headers=identity_headers(sally, access=[("sellingtravel", None)]))
    assert r.status_code == 200 and r.json()["payload"]["open_href"] == f"/mail-merge?review={item.id}"


def test_followups_when_the_inbox_cant_be_read(db_session, monkeypatch):
    from app.graph_client import GraphRequestError
    sally = make_user(db_session, role="sales", name="Sally")
    people = [_company(db_session, f"Co {i}", person=f"P{i}", email=f"p{i}@x.example")[1] for i in range(5)]
    _merge(db_session, sally, [(c, f"p{i}@x.example") for i, c in enumerate(people)])
    db_session.commit()
    monkeypatch.setattr(mf, "SessionLocal", lambda: _NoCloseSession(db_session))

    def fail(box, since):
        raise GraphRequestError(503, "down")
    monkeypatch.setattr(mf, "replied_addresses", fail)
    for _ in range(mf.MAX_TRIES - 1):
        mf.scan()
        assert db_session.query(ReviewQueueItem).filter_by(kind="merge_followup").count() == 0   # tries again tomorrow
    mf.scan()
    item = db_session.query(ReviewQueueItem).filter_by(kind="merge_followup").one()
    assert item.payload["facets"]["replies"] == "Replies not checked"
    assert any("couldn't be checked for replies" in d["value"] for d in item.payload["details"])
