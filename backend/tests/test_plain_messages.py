"""People never see internal errors, codes or system names (19 Oct review):

- "Run now" names the job in words, says when it was already running, and a failure is a plain sentence,
- run history shows a plain sentence (the technical error stays for the log and an admin tooltip),
- bulk review problems are counted by plain reason, never card ids,
- job descriptions and notes carry no requirement codes,
- the shared-inbox question uses the titles' names,
- a mail merge send that fails says why in plain words.
"""
import dataclasses
import re
import uuid
from datetime import datetime, timezone

import httpx
from tests.conftest import identity_headers, make_user

from app.api.routes import automations as automations_routes
from app.automations import registry
from app.automations.scheduler import all_jobs, plain_run_error
from app.models import AutomationJobRun, Contact, ReviewQueueItem
from app.services.mail_merge import plain_send_error

CODE = re.compile(r"\b[A-Z]{2,6}-\d{3}\b")


def _admin(db):
    user = make_user(db, role="admin", name="Ahmed")
    db.flush()
    return identity_headers(user)


# ---- Run now ------------------------------------------------------------------------------------------------------

def test_run_now_names_the_job_and_says_when_it_is_already_running(client, db_session, monkeypatch):
    h = _admin(db_session)
    job = all_jobs()[0]
    monkeypatch.setattr(automations_routes, "run_job", lambda j, trigger: False)
    r = client.post(f"/api/automations/jobs/{job.id}/run", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["skipped"] is True and body["label"] == job.label and "already running" in body["message"]
    assert job.id not in body["message"]


def test_run_now_failure_is_a_plain_sentence(client, db_session, monkeypatch):
    h = _admin(db_session)
    job = all_jobs()[0]

    def boom(j, trigger):
        raise RuntimeError("psycopg.OperationalError: connection to server at 10.0.0.5 failed")

    monkeypatch.setattr(automations_routes, "run_job", boom)
    r = client.post(f"/api/automations/jobs/{job.id}/run", headers=h)
    assert r.status_code == 500
    detail = r.json()["detail"]
    assert detail.startswith(job.label) and "psycopg" not in detail and "10.0.0.5" not in detail and job.id not in detail


def test_unknown_job_is_plain(client, db_session):
    r = client.post("/api/automations/jobs/no_such_job/run", headers=_admin(db_session))
    assert r.status_code == 404 and "no_such_job" not in r.json()["detail"]


# ---- run history --------------------------------------------------------------------------------------------------

def test_plain_run_error_maps_common_problems():
    assert plain_run_error(None) is None
    assert "couldn't read or save" in plain_run_error("OperationalError: (psycopg.OperationalError) server closed")
    assert "didn't answer in time" in plain_run_error("ReadTimeout: timed out")
    assert "signing in again" in plain_run_error("GraphRequestError: 401 Unauthorized")
    assert plain_run_error("KeyError: 'x'") == "It stopped with a problem before it finished. The full details are in the log."


def test_run_history_shows_a_plain_sentence(client, db_session):
    h = _admin(db_session)
    job = all_jobs()[0]
    raw = "TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'"
    db_session.add(AutomationJobRun(id=uuid.uuid4(), job_id=job.id, trigger="scheduled", status="failed",
                                    started_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
                                    finished_at=datetime(2030, 1, 1, 0, 1, tzinfo=timezone.utc), items_queued=0, error=raw))
    db_session.flush()
    runs = client.get("/api/automations/job-runs?per_job=1", headers=h).json()[job.id]
    assert runs[0]["error"] == plain_run_error(raw) and "TypeError" not in runs[0]["error"]
    assert runs[0]["error_detail"] == raw   # kept for an administrator's tooltip


# ---- bulk review --------------------------------------------------------------------------------------------------

def test_bulk_review_problems_are_counted_by_reason_without_ids(client, db_session, monkeypatch):
    kind = registry.get_kind("followup_due") or next(k for k in registry.all_kinds() if k.actions)
    action = next(a for a in kind.actions if not (a.requires_contact_picker or a.requires_related_entity_choice
                                                   or a.requires_note or any(f.required for f in a.extra_fields if f.field_type != "bool")))

    def refuse(db, item, action_id, input_data):
        raise ValueError("This card is out of date.")

    monkeypatch.setitem(registry._REGISTRY, kind.kind, dataclasses.replace(kind, handler=refuse))
    ids = []
    for _ in range(3):
        item = ReviewQueueItem(id=uuid.uuid4(), kind=kind.kind, source_db="onboard", status="pending", payload={"summary": "x"})
        db_session.add(item)
        ids.append(str(item.id))
    db_session.commit()
    r = client.post(f"/api/review-queue/bulk-actions/{action.id}", params={"kind": kind.kind}, json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["failed"] >= 3 and body["errors"][0].endswith("cards: This card is out of date.")
    assert not any(i in e for e in body["errors"] for i in ids)


# ---- codes and names ----------------------------------------------------------------------------------------------

def test_job_descriptions_have_no_requirement_codes():
    for j in all_jobs():
        assert not CODE.search(j.description) and not CODE.search(j.label), j.id


def test_shared_inbox_lead_accepts_the_titles_name(client, db_session):
    item = ReviewQueueItem(id=uuid.uuid4(), kind="inbound_contact_unmatched", source_db=None, status="pending",
                           payload={"summary": "x", "source_db": "*", "sender_email": "jo@newco.example", "original_text": "Hi"})
    db_session.add(item)
    db_session.commit()
    r = client.post(f"/api/review-queue/{item.id}/actions/create_contact", json={"fields": {"name": "Jo Bloggs"}})
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert "sellingtravel" not in detail and "Selling Travel" in detail
    r = client.post(f"/api/review-queue/{item.id}/actions/create_contact",
                    json={"fields": {"name": "Jo Bloggs", "source_db": "Selling Travel"}})
    assert r.status_code == 200, r.text
    assert db_session.get(Contact, uuid.UUID(r.json()["entity_id"])).source_db == "sellingtravel"
    shared = next(f for a in registry.get_kind("inbound_contact_unmatched").actions for f in a.extra_fields if f.key == "source_db")
    assert "sellingtravel" not in shared.placeholder and "Selling Travel" in shared.placeholder


# ---- mail merge ---------------------------------------------------------------------------------------------------

def test_mail_merge_send_problems_are_plain():
    assert plain_send_error(RuntimeError("Outlook refused the message (400): ErrorInvalidRecipients")) == "The address was refused."
    assert "slow down" in plain_send_error(RuntimeError("Outlook refused the message (429): throttled"))
    assert "didn't answer" in plain_send_error(httpx.ReadTimeout("timed out"))
    assert plain_send_error(RuntimeError("Outlook refused the message (418): teapot")) == "Outlook couldn't send this one."
