"""Workstream stats for the Automations Hub pages, plus scanner run
history recording. See app/api/routes/automation_stats.py."""
import uuid
from datetime import datetime, timedelta, timezone

from tests.conftest import identity_headers, make_user

from app.automations.workstreams import KIND_JOB, WORKSTREAMS
from app.automations import all_kinds
from app.models import AutomationJobRun, ReviewQueueItem


def _item(db_session, kind: str, *, status: str = "pending", created_ago: timedelta = timedelta(hours=1),
          resolved_ago: timedelta | None = None, action: str | None = None, reviewer=None) -> ReviewQueueItem:
    now = datetime.now(timezone.utc)
    item = ReviewQueueItem(
        id=uuid.uuid4(), kind=kind, source_db="onboard", payload={"summary": f"{kind} item"},
        status=status, resolved_action=action,
        reviewed_at=(now - resolved_ago) if resolved_ago is not None else None,
        reviewed_by_user_id=reviewer.id if reviewer else None,
    )
    db_session.add(item)
    db_session.flush()
    item.created_at = now - created_ago
    db_session.flush()
    return item


def test_every_registered_kind_belongs_to_exactly_one_workstream():
    """The workstream map is the single source of truth - a new automation
    that isn't added to it would silently vanish from every Hub page."""
    placed = [k for w in WORKSTREAMS for k in w.kinds]
    assert len(placed) == len(set(placed))
    assert set(placed) == {k.kind for k in all_kinds()}
    assert set(KIND_JOB) == set(placed)


def test_workstream_list_counts_pending_and_7d(client, db_session):
    _item(db_session, "duplicate_contact")
    _item(db_session, "duplicate_contact", status="rejected", created_ago=timedelta(days=2),
          resolved_ago=timedelta(days=1), action="not_duplicate")
    _item(db_session, "duplicate_contact", created_ago=timedelta(days=20))  # pending, but not new this week

    resp = client.get("/api/automations/workstreams")
    assert resp.status_code == 200
    hygiene = next(w for w in resp.json() if w["id"] == "hygiene")
    assert hygiene["pending"] == 2
    assert hygiene["new_7d"] == 2
    assert hygiene["resolved_7d"] == 1
    assert len(hygiene["daily_new_7d"]) == 7


def test_workstream_stats_totals_deltas_and_acted_on(client, db_session):
    _item(db_session, "ooo_ambiguous")
    _item(db_session, "ooo_ambiguous", status="approved", created_ago=timedelta(days=3),
          resolved_ago=timedelta(days=2), action="confirm_replacement")
    _item(db_session, "ooo_ambiguous", status="rejected", created_ago=timedelta(days=3),
          resolved_ago=timedelta(days=1), action="ignore")
    _item(db_session, "ooo_ambiguous", created_ago=timedelta(days=10))  # previous period

    resp = client.get("/api/automations/workstreams/hygiene/stats?range=7d")
    assert resp.status_code == 200
    body = resp.json()
    t = body["totals"]
    assert t["pending"] == 2
    assert t["new"] == 3
    assert t["new_prev"] == 1
    assert t["resolved"] == 2
    assert t["acted_on_rate"] == 0.5
    assert t["median_resolve_seconds"] is not None
    assert len(body["daily"]) == 7

    ooo = next(a for a in body["automations"] if a["kind"] == "ooo_ambiguous")
    assert ooo["pending"] == 2
    assert ooo["job"]["id"] == "cs001_cs002_bounce_ooo_scan"
    assert len(ooo["daily_new"]) == 7


def test_backlog_series_ends_at_current_pending(client, db_session):
    _item(db_session, "duplicate_contact", created_ago=timedelta(days=40))
    _item(db_session, "duplicate_contact", created_ago=timedelta(days=2))
    body = client.get("/api/automations/workstreams/hygiene/stats?range=7d").json()
    assert body["daily"][-1]["backlog"] == body["totals"]["pending"]


def test_all_time_range_has_no_deltas(client, db_session):
    _item(db_session, "duplicate_contact")
    body = client.get("/api/automations/workstreams/hygiene/stats?range=all").json()
    assert body["totals"]["new_prev"] is None
    assert body["chart_days"] == 90


def test_unknown_workstream_404s(client):
    assert client.get("/api/automations/workstreams/nope/stats").status_code == 404


def test_kind_detail_outcomes_and_reviewers(client, db_session):
    rep = make_user(db_session, role="admin", name="Jane Rep")
    _item(db_session, "duplicate_contact", status="rejected", created_ago=timedelta(days=2),
          resolved_ago=timedelta(days=1), action="not_duplicate", reviewer=rep)
    _item(db_session, "duplicate_contact", status="rejected", created_ago=timedelta(days=2),
          resolved_ago=timedelta(days=1), action="not_duplicate", reviewer=rep)

    body = client.get("/api/automations/kinds/duplicate_contact/detail?range=7d").json()
    assert body["outcomes"][0]["label"] == "Keep as separate contacts"
    assert body["outcomes"][0]["count"] == 2
    assert body["top_reviewers"] == [{"name": "Jane Rep", "count": 2}]
    assert body["ai_cost_usd"] is None  # dedupe makes no AI calls
    assert len(body["recent"]) == 2


def test_shared_ai_cost_is_labelled_as_shared(client, db_session):
    body = client.get("/api/automations/kinds/ooo_ambiguous/detail").json()
    assert body["ai_cost_usd"] == 0
    # bounce_uncertain, bounce_unmatched and departure_unconfirmed all come
    # from the same bounce/OOO scanner's AI calls.
    assert len(body["ai_cost_shared_with"]) == 3


def test_sales_identity_is_blocked(client, db_session):
    rep = make_user(db_session, role="sales")
    resp = client.get("/api/automations/workstreams", headers=identity_headers(rep, access=[("onboard", None)]))
    assert resp.status_code == 403


def test_job_runs_endpoint_returns_latest_per_job(client, db_session):
    now = datetime.now(timezone.utc)
    for i in range(3):
        db_session.add(AutomationJobRun(
            id=uuid.uuid4(), job_id="cs004_dedupe_scan", trigger="scheduled",
            started_at=now - timedelta(hours=i), finished_at=now - timedelta(hours=i) + timedelta(seconds=5),
            status="success", items_queued=i,
        ))
    db_session.flush()
    body = client.get("/api/automations/job-runs?per_job=2").json()
    runs = body["cs004_dedupe_scan"]
    assert len(runs) == 2
    assert runs[0]["items_queued"] == 0  # newest first
    assert "cs001_cs002_bounce_ooo_scan" in body


def test_run_job_records_success_and_failure(db_session):
    """run_job writes history through its own session (so a job's own
    rollback can't erase it) - checked here directly, then cleaned up
    because that session commits outside the test's savepoint."""
    from app.automations.scheduler import ScheduledJob, run_job
    from app.db.session import SessionLocal

    ok = ScheduledJob(id=f"test_ok_{uuid.uuid4().hex[:6]}", label="t", description="t", cron="0 0 * * *",
                      func=lambda: None, enabled_flag="automations_bounce_scan_enabled")

    def boom():
        raise RuntimeError("scanner exploded")

    bad = ScheduledJob(id=f"test_bad_{uuid.uuid4().hex[:6]}", label="t", description="t", cron="0 0 * * *",
                       func=boom, enabled_flag="automations_bounce_scan_enabled")

    assert run_job(ok, trigger="manual") is True
    try:
        run_job(bad)
    except RuntimeError:
        pass

    s = SessionLocal()
    try:
        ok_run = s.query(AutomationJobRun).filter_by(job_id=ok.id).one()
        bad_run = s.query(AutomationJobRun).filter_by(job_id=bad.id).one()
        assert ok_run.status == "success" and ok_run.trigger == "manual" and ok_run.finished_at
        assert bad_run.status == "failed" and "scanner exploded" in bad_run.error
    finally:
        s.query(AutomationJobRun).filter(AutomationJobRun.job_id.in_([ok.id, bad.id])).delete(synchronize_session=False)
        s.commit()
        s.close()
