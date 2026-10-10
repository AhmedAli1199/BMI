"""Email templates: Clare's ACT! templates, brand facts and issue details as merge fields, and a one-off email."""
import uuid
from datetime import date

from tests.conftest import identity_headers, make_user
from tests.test_crm_messaging import _contact

from app.models import EditionFeature, HistoryEntry, SalesEdition, SalesTitle
from app.models.messaging import MailAccount, MailTemplate
from app.sales.reference import ensure_reference_data
from app.services import outlook


def _issue(db):
    ensure_reference_data(db)
    t = db.query(SalesTitle).filter_by(slug="selling-travel").one()
    e = SalesEdition(id=uuid.uuid4(), title_id=t.id, year=2027, name="JulAug2027", edition_date=date(2027, 7, 1),
                     ad_deadline=date(2027, 6, 4), kind="issue")
    db.add(e)
    db.flush()
    db.add(EditionFeature(id=uuid.uuid4(), edition_id=e.id, title="Japan", status="planned", sort_order=0))
    db.flush()
    return e


def test_load_act_templates_once_with_brand_facts(client, db_session):
    admin = make_user(db_session, role="admin")
    h = identity_headers(admin)
    assert client.post("/api/mail/templates/load-act", headers=h).json() == {"added": 7}
    assert client.post("/api/mail/templates/load-act", headers=h).json() == {"added": 0}
    rows = client.get("/api/mail/templates", headers=h).json()
    assert len(rows) == 7 and all(r["needs_check"] and r["brand"] == "stm" and r["source"] == "act" for r in rows)
    pitch = next(r for r in rows if r["name"] == "Feature pitch: first email")
    assert pitch["kind"] == "pitch" and pitch["uses_issue"] and "<Salutation>" not in pitch["body"] and "{{print_run}}" in pitch["body"]
    s = client.get("/api/editorial/brands/stm/settings", headers=h).json()
    assert s["facts"]["print_run"] == "12,808"
    # saving a template marks it checked
    r = client.put(f"/api/mail/templates/{pitch['id']}", headers=h, json={**{k: pitch[k] for k in ("name", "subject", "body", "brand", "kind")}})
    assert r.json()["needs_check"] is False
    assert client.post("/api/mail/templates/load-act", headers=identity_headers(make_user(db_session, role="sales"))).status_code == 403


def test_compose_fills_issue_brand_and_contact_then_sends_and_logs(client, db_session, monkeypatch):
    e = _issue(db_session)
    me = make_user(db_session, role="admin")
    h = identity_headers(me, access=[("manual", None)])
    client.post("/api/mail/templates/load-act", headers=h)
    tpl = db_session.query(MailTemplate).filter_by(name="Feature pitch: first email").one()
    amy = _contact(db_session, "Amy", "Zed", email="amy@zeta.com", salutation="Amy")
    r = client.post("/api/mail/compose", headers=h, json={"template_id": str(tpl.id), "contact_id": str(amy.id), "edition_id": str(e.id)}).json()
    assert r["to"] == ["amy@zeta.com"] and r["subject"] == "Japan in the JulAug2027 of Selling Travel"
    assert r["body"].startswith("Hi Amy,") and "12,808 in print" in r["body"] and "Thursday 1 July 2027" in r["body"] and not r["missing"]
    # without an issue the fallbacks are used, nothing is left as {{...}}
    r2 = client.post("/api/mail/compose", headers=h, json={"template_id": str(tpl.id), "contact_id": str(amy.id)}).json()
    assert "{{" not in r2["body"] and "next issue" in r2["body"]
    assert client.post("/api/mail/compose/send", headers=h, json={"to": ["amy@zeta.com"], "subject": "x", "body": "y"}).status_code == 409
    db_session.add(MailAccount(id=uuid.uuid4(), user_id=me.id, email="me@bmi.test", refresh_token_enc=outlook.encrypt("rt")))
    db_session.flush()
    sent = []
    monkeypatch.setattr(outlook, "send_mail", lambda db, acct, **kw: sent.append(kw))
    bad = client.post("/api/mail/compose/send", headers=h, json={"to": ["amy@zeta.com"], "subject": "Hi", "body": "About {{issue}}"})
    assert bad.status_code == 422
    ok = client.post("/api/mail/compose/send", headers=h, json={"to": ["amy@zeta.com"], "subject": r["subject"], "body": r["body"],
                                                                   "contact_id": str(amy.id), "template_id": str(tpl.id)})
    assert ok.status_code == 200 and sent[0]["to"] == ["amy@zeta.com"]
    assert db_session.query(HistoryEntry).filter_by(entity_id=amy.id, history_type="E-mail Sent").one().subject == r["subject"]
    db_session.refresh(tpl)
    assert tpl.use_count == 1


def test_mail_merge_needs_the_issue_when_the_email_uses_it(client, db_session):
    e = _issue(db_session)
    me = make_user(db_session)
    h = identity_headers(me, access=[("manual", None)])
    amy = _contact(db_session, "Amy", "Zed", email="amy@zeta.com")
    db_session.add(MailAccount(id=uuid.uuid4(), user_id=me.id, email="me@bmi.test", refresh_token_enc=outlook.encrypt("rt")))
    db_session.flush()
    body = {"output": "email", "contact_ids": [str(amy.id)], "subject": "{{feature}} in {{issue}}", "body": "Hi {{first_name}}, out {{issue_date}}"}
    r = client.post("/api/mail-merge", headers=h, json=body)
    assert r.status_code == 400 and "aren't filled in" in r.json()["detail"]
    m = client.post("/api/mail-merge", headers=h, json={**body, "edition_id": str(e.id)}).json()
    assert m["subject"] == "Japan in JulAug2027"
    p = client.post("/api/mail-merge/preview", headers=h, json={"subject": body["subject"], "body": body["body"], "contact_id": str(amy.id),
                                                               "edition_id": str(e.id)}).json()
    assert p["body"] == "Hi Amy, out Thursday 1 July 2027"
