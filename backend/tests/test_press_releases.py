"""Press releases editors forward, who to contact, and the media kit introduction (app/automations/press_releases.py)."""
import uuid
from datetime import datetime, timezone

from tests.conftest import identity_headers, make_user

from app.automations import press_releases as pr
from app.automations.mail_parsing import ParsedMessage
from app.models import Company, Contact, Email, Note, ReviewQueueItem

BOX = "commercial@bmipublishing.co.uk"
DOMAINS = {"bmipublishing.co.uk"}
RELEASE = ("Worth a call? - Bev\n\n---------- Forwarded message ---------\nFrom: Sun Air press office\n\n"
           "PRESS RELEASE - for immediate release\nSun Air launches daily flights from Manchester to Malaga.\n\n"
           "Notes to editors\nMedia contact: Pat Reed, PR Manager, pat@sunair-pr.example\n"
           "Trade enquiries: Lou King, Head of Trade Marketing, lou.king@sunair.example")
INFO = {"is_release": True, "company": "Sun Air", "headline": "Sun Air launches daily Manchester to Malaga flights",
        "story": "A new daily route from Manchester.", "magazine": None, "editor_note": "Worth a call? - Bev",
        "contacts": [{"name": "Pat Reed", "role": "PR Manager", "email": "pat@sunair-pr.example", "kind": "press"},
                     {"name": "Lou King", "role": "Head of Trade Marketing", "email": "lou.king@sunair.example", "kind": "marketing"}]}


def _msg(body=RELEASE, subject="FW: Sun Air press release", sender="bev@bmipublishing.co.uk"):
    return ParsedMessage(message_id=uuid.uuid4().hex, internet_message_id=None, from_address=sender, from_name="Bev Editor",
                         subject=subject, received_at=datetime(2026, 10, 28, 9, tzinfo=timezone.utc), body_text=body)


def test_which_emails_are_read_and_without_the_brain():
    assert pr.candidate(_msg(), BOX)
    assert not pr.candidate(_msg(body="Lunch on Friday?", subject="Lunch"), BOX)
    assert not pr.candidate(_msg(sender="noreply@wire.example"), BOX)
    info = pr.classify(None, _msg(), DOMAINS)   # no Brain configured: the addresses in it, not checked
    assert info["unchecked"] and {c["email"] for c in info["contacts"]} == {"pat@sunair-pr.example", "lou.king@sunair.example"}


def test_card_finds_who_to_contact_and_sends_the_introduction(client, db_session):
    owner = make_user(db_session, role="sales")
    co = Company(id=uuid.uuid4(), source_db="prospects", source_act_id=uuid.uuid4().hex, name="Sun Air", owner_user_id=owner.id)
    db_session.add(co)
    db_session.flush()
    item = pr.queue(db_session, BOX, _msg(), INFO, DOMAINS)
    db_session.commit()
    p = item.payload
    # the marketing contact leads, ahead of the press office; the company is linked and the card is the owner's
    assert p["suggested_to"] == "lou.king@sunair.example" and [x["kind"] for x in p["people"]] == ["marketing", "press"]
    assert any(d.get("href") == f"/companies/{co.id}" for d in p["details"]) and p["open_href"] == f"/companies/{co.id}"
    assert p["owner_user_id"] == str(owner.id)
    assert p["facets"] == {"magazine": "Not sure", "contact": "New contact", "company": "In the CRM", "salesperson": owner.name}
    assert any(d["label"] == "Editor's note" for d in p["details"]) and any(d["label"] == "Forwarded by" for d in p["details"])
    # the introduction: their story, the media pack (none saved here, so a placeholder), an invitation
    assert "Sun Air" in p["original_text"].split("\n", 1)[0] and pr.NO_LINK in p["original_text"]
    assert any("No media pack link" in d["value"] for d in p["details"])

    # only the owner (and admins) see it
    other = make_user(db_session, role="sales")
    ids = lambda u: [i["id"] for i in client.get("/api/review-queue?kind=press_release", headers=identity_headers(u, access=[("prospects", None)])).json()["items"]]
    assert str(item.id) in ids(owner) and str(item.id) not in ids(other)

    h = identity_headers(owner, access=[("prospects", None)])
    r = client.post(f"/api/review-queue/{item.id}/actions/send", json={"note": p["original_text"]}, headers=h)
    assert r.status_code == 400 and "media pack link" in r.json()["detail"]
    fixed = p["original_text"].replace(pr.NO_LINK, "https://media.example/pack")
    r = client.post(f"/api/review-queue/{item.id}/actions/send", json={"note": fixed}, headers=h)
    assert r.status_code == 400 and "Connect your Outlook" in r.json()["detail"]

    # sent another way: the contact is added to the company with their job title, and the email is noted on them
    r = client.post(f"/api/review-queue/{item.id}/actions/logged", json={"note": fixed}, headers=h)
    assert r.status_code == 200, r.text
    lou = db_session.query(Contact).join(Email, Email.contact_id == Contact.id).filter(Email.address == "lou.king@sunair.example").one()
    assert lou.full_name == "Lou King" and lou.company_id == co.id and lou.job_title == "Head of Trade Marketing"
    assert db_session.query(Note).filter_by(entity_id=lou.id, note_type="Media kit introduction").count() == 1


def test_just_add_the_contact_and_a_new_company(client, db_session):
    h = identity_headers(make_user(db_session, role="admin"))
    info = {**INFO, "company": "Wave Hotels", "contacts": []}
    item = pr.queue(db_session, BOX, _msg(), info, DOMAINS)
    db_session.commit()
    assert item.payload["facets"]["contact"] == "No contact found" and item.payload["suggested_to"] == ""
    r = client.post(f"/api/review-queue/{item.id}/actions/add_contact", json={"fields": {"email": "bad"}}, headers=h)
    assert r.status_code == 400 and "email address" in r.json()["detail"]
    r = client.post(f"/api/review-queue/{item.id}/actions/add_contact", json={"fields": {
        "name": "Kim Ode", "email": "kim@wave.example", "job_title": "Marketing Director", "company_name": "Wave Hotels"}}, headers=h)
    assert r.status_code == 200, r.text
    kim = db_session.query(Contact).filter_by(full_name="Kim Ode").one()
    assert db_session.get(Company, kim.company_id).name == "Wave Hotels" and kim.job_title == "Marketing Director"
    db_session.refresh(item)
    assert item.status == "approved" and any(d.get("href") == f"/contacts/{kim.id}" for d in item.payload["details"])
    assert db_session.query(ReviewQueueItem).filter_by(kind="press_release").count() == 1
