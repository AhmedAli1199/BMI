"""SALES-028: behind-last-cycle alerts and the weekly management summary."""
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from tests.conftest import identity_headers, make_user

import app.automations.management_reports as mr
from app.automations import runtime_settings
from app.models import ManagementAlert, Notification, WeeklySummary
from tests.test_sales_dashboard import TODAY, order, world  # noqa: F401 - fixture + helper reuse


def seed_behind(db, world):
    early = world["last_pub"] - timedelta(days=60)
    for i in range(4):
        order(db, world["last"], f"C{i}", 1000, booked_on=early)
    order(db, world["this"], "Now", 1000, booked_on=TODAY - timedelta(days=2))


def test_alert_fires_once_then_cooldown(db_session, world):
    admin = make_user(db_session, role="admin")
    make_user(db_session, role="sales")
    seed_behind(db_session, world)
    fired = mr.run_alerts(db_session, TODAY)
    assert len(fired) == 1
    a = fired[0]
    assert a.subject_id == world["this"].id and float(a.gap) == -3000 and a.gap_pct == pytest.approx(-0.75)
    assert "£1,000" in a.message and "£4,000" in a.message and "75%" in a.message
    assert [r["id"] for r in a.records_ref] == [str(world["this"].id), str(world["last"].id)]
    notes = db_session.query(Notification).filter_by(kind="management_alert").all()
    assert [n.user_id for n in notes] == [admin.id]  # admins only, not the sales rep
    assert mr.run_alerts(db_session, TODAY) == []  # cooldown: not again


def test_alert_not_fired_when_thin_or_ahead(db_session, world):
    make_user(db_session, role="admin")
    order(db_session, world["last"], "Only", 5000, booked_on=world["last_pub"] - timedelta(days=60))  # one booking: not judged
    order(db_session, world["this"], "Now", 100, booked_on=TODAY)
    assert mr.run_alerts(db_session, TODAY) == []


def test_recipients_setting_overrides_admins(db_session):
    make_user(db_session, role="admin", email="boss@example.com")
    lead = make_user(db_session, role="sales", email="lead@example.com")
    runtime_settings.set_override(db_session, "management_recipients", "lead@example.com")
    assert [u.id for u in mr.recipients(db_session)] == [lead.id]


def test_weekly_summary_template_has_every_section_and_is_idempotent(db_session, world, monkeypatch):
    monkeypatch.setattr(mr, "is_configured", lambda: False)
    make_user(db_session, role="admin")
    seed_behind(db_session, world)
    row, created = mr.generate_weekly_summary(db_session, TODAY)
    assert created and row.source == "template" and row.week_of == TODAY - timedelta(days=TODAY.weekday())
    assert [s["key"] for s in row.sections] == ["headline", "revenue", "activity", "editions", "alerts", "delivery", "decisions"]
    assert "behind last cycle" in row.sections[0]["paragraphs"][0]
    assert "## Sold-work delivery" in row.brief_markdown and "## Needs a decision" in row.brief_markdown
    assert any("behind" in b["text"] for b in row.sections[3]["bullets"])
    assert db_session.query(Notification).filter_by(kind="weekly_summary").count() == 1
    row2, created2 = mr.generate_weekly_summary(db_session, TODAY)  # manual re-run
    assert row2.id == row.id and not created2
    assert db_session.query(Notification).filter_by(kind="weekly_summary").count() == 1  # not re-sent
    assert db_session.query(WeeklySummary).count() == 1


def test_model_headline_used_only_if_numbers_match(db_session, world, monkeypatch):
    make_user(db_session, role="admin")
    seed_behind(db_session, world)
    monkeypatch.setattr(mr, "is_configured", lambda: True)
    monkeypatch.setattr(mr, "draft_text", lambda *a, **k: "Bookings are £1,000 so far and one edition needs attention.")
    row, _ = mr.generate_weekly_summary(db_session, TODAY, notify=False)
    assert row.source == "ai" and row.sections[0]["paragraphs"][0].startswith("Bookings are £1,000")
    db_session.query(WeeklySummary).delete()
    monkeypatch.setattr(mr, "draft_text", lambda *a, **k: "Bookings are up 400% to £987,654.")  # invented figures
    row, _ = mr.generate_weekly_summary(db_session, TODAY, notify=False)
    assert row.source == "template" and "987,654" not in row.brief_markdown
    db_session.query(WeeklySummary).delete()
    monkeypatch.setattr(mr, "draft_text", lambda *a, **k: None)  # model failure
    row, _ = mr.generate_weekly_summary(db_session, TODAY, notify=False)
    assert row.source == "template"


def test_management_api_is_staff_only(client, db_session, world, monkeypatch):
    monkeypatch.setattr(mr, "is_configured", lambda: False)
    seed_behind(db_session, world)
    mr.run_alerts(db_session, TODAY, notify=False)
    row, _ = mr.generate_weekly_summary(db_session, TODAY, notify=False)
    admin, rep = make_user(db_session, role="admin"), make_user(db_session, role="sales")
    ok = identity_headers(admin)
    assert client.get("/api/management/summaries", headers=identity_headers(rep)).status_code == 403
    listing = client.get("/api/management/summaries", headers=ok).json()
    assert [s["id"] for s in listing] == [str(row.id)] and listing[0]["headline"]
    detail = client.get(f"/api/management/summaries/{row.id}", headers=ok).json()
    assert detail["sections"][0]["key"] == "headline" and detail["brief_markdown"].startswith("# Weekly sales summary")
    alerts = client.get("/api/management/alerts", headers=ok).json()
    assert len(alerts) == 1 and alerts[0]["gap"] == -3000
    assert client.get(f"/api/management/summaries/{uuid.uuid4()}", headers=ok).status_code == 404


def test_jobs_registered_and_default_off():
    from app.automations.scheduler import all_jobs

    jobs = {j.id: j for j in all_jobs()}
    assert jobs["management_alerts_scan"].enabled_flag == "automations_management_alerts_enabled"
    assert jobs["weekly_management_summary"].enabled_flag == "automations_weekly_summary_enabled"
