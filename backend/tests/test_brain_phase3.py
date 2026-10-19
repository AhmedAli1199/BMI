"""Ask AI phase 3: automations, the Review Queue, settings, the editorial plan and the rest of the CRM - read-only,
and only what each person can open themselves (their role plus Settings > Sections)."""
import uuid
from datetime import date, timedelta

import pytest
from tests.conftest import make_user
from tests.test_brain_data import Ctx, _Shared
from tests.test_orders import w  # noqa: F401 - fixture

from app import ui_sections
from app.automations.status import schedule_words
from app.brain import access, registry, runner, tools  # noqa: F401 (registers the tools)
from app.core.identity import Identity
from app.models import Feedback, ReviewQueueItem

NO = "You don't have permission to view that."


@pytest.fixture
def run(w, monkeypatch):
    db = w["db"]
    monkeypatch.setattr(registry, "session_factory", lambda: _Shared(db))

    def call(tool, user, **kw):
        return registry.TOOLS[tool].adk_fn(tool_context=Ctx(Identity(user_id=str(user.id), role=user.role)), **kw)
    return call


@pytest.fixture
def people(w):
    db = w["db"]
    admin = make_user(db, role="admin", name="Ahmed")
    sally = make_user(db, role="sales", name="Sally Parker")
    db.flush()
    return {"admin": admin, "sales": sally, "db": db}


def test_schedules_in_plain_words():
    summer, winter = date(2026, 7, 1), date(2026, 1, 15)
    assert schedule_words("*/15 * * * *") == "every 15 minutes"
    # jobs run on UTC times; people see UK clock time (BST in summer, GMT in winter)
    assert schedule_words("0 7 * * 1-5", summer) == "at 08:00 UK time, Monday to Friday"
    assert schedule_words("0 7 * * 1-5", winter) == "at 07:00 UK time, Monday to Friday"
    assert schedule_words("30 6 * * *", summer) == "every day at 07:30 UK time"


def test_every_scheduled_job_has_a_plain_schedule():
    """No job's schedule comes back as a raw cron code or says UTC."""
    from app.automations.scheduler import all_jobs

    for j in all_jobs():
        for on in (date(2026, 7, 1), date(2026, 1, 15)):
            words = schedule_words(j.cron, on)
            assert "*" not in words and "UTC" not in words and words != "on a custom schedule", (j.id, j.cron, words)
    assert schedule_words("15 7 * * 1-5", date(2026, 7, 1)) == "at 08:15 UK time, Monday to Friday"
    assert schedule_words("30 6 * * 1", date(2026, 1, 15)) == "at 06:30 UK time, every Monday"
    assert schedule_words("0 7-18 * * 1-5", date(2026, 7, 1)) == "every hour from 08:00 to 19:00 UK time, Monday to Friday"
    assert schedule_words("20 * * * *") == "every hour at 20 minutes past"
    assert schedule_words("0 3 * * 0", date(2026, 7, 1)) == "at 04:00 UK time, every Sunday"


def test_automations_are_for_people_who_can_open_the_hub(run, people):
    out = run("automations_overview", people["admin"])
    assert "automations are switched on" in out["summary"] and len(out["automations"]) > 10
    names = {a["name"] for a in out["automations"]}
    assert "Shared calendar" in names and all(a["schedule"] for a in out["automations"])
    d = run("automation_detail", people["admin"], name="Uninvoiced Bookings")
    assert d["cards"][0]["card"] == "Uninvoiced Bookings" and "Record invoice" in d["cards"][0]["buttons"]
    assert d["settings"] and all("value" in s and "default" in s for s in d["settings"])
    # a salesperson can't open the Automations Hub, so the assistant won't tell them either
    assert run("automations_overview", people["sales"])["error"].startswith(NO)
    assert run("automation_detail", people["sales"], name="renewal")["error"].startswith(NO)


def test_switched_off_sections_are_off_in_answers_too(run, people):
    db = people["db"]
    ui_sections.save(db, {"sales": ["editorial", "review_queue"]})
    assert run("editorial_upcoming", people["sales"])["error"].startswith(NO)
    assert run("review_queue_status", people["sales"])["error"].startswith(NO)
    assert run("help_read_guide", people["sales"], guide="editorial/editorial-plan")["error"].startswith(NO)
    labels = access.blocked_labels(db, Identity(user_id=str(people["sales"].id), role="sales"))
    assert "Editorial plan" in labels and "Automations Hub" in labels
    ctx = runner.context_block(people["sales"], Identity(user_id=str(people["sales"].id), role="sales"), {"cannot_open": labels})
    assert "can't open" in ctx and "Editorial plan" in ctx
    # admins always see everything
    assert "issues" in run("editorial_upcoming", people["admin"])


def test_review_queue_counts_are_scoped_like_the_queue(run, people):
    db = people["db"]
    for kind in ("duplicate_contact", "duplicate_contact", "followup_due"):
        db.add(ReviewQueueItem(id=uuid.uuid4(), kind=kind, status="pending", payload={"summary": f"A {kind}",
                                                                                       "owner_user_id": str(people["sales"].id)}))
    db.flush()
    mine = run("review_queue_status", people["admin"])
    assert {r["kind"]: r["waiting"] for r in mine["by_card"]}["duplicate_contact"] == 2
    theirs = run("review_queue_status", people["sales"])
    assert all(r["kind"] != "duplicate_contact" for r in theirs["by_card"])       # data hygiene isn't for sales
    items = run("review_items", people["admin"], card="duplicate_contact")
    assert len(items["items"]) == 2 and items["link"].startswith("/automations/review?kind=")


def test_settings_mine_and_others(run, people):
    me = run("my_settings", people["sales"])
    assert me["name"] == "Sally Parker" and me["role"] == "Sales" and any(p["setting"] == "Email me notifications" for p in me["preferences"])
    assert run("person_settings", people["sales"], person="Ahmed")["error"].startswith(NO)   # only administrators
    assert run("person_settings", people["admin"], person="Sally Parker")["name"] == "Sally Parker"
    found = run("settings_lookup", people["admin"], query="renewal emails")
    assert any("Automations" in r["area"] for r in found["results"])
    sales_view = run("settings_lookup", people["sales"], query="production email")
    assert "automation settings" not in sales_view["searched"] and "connections" not in sales_view["searched"]
    assert any(r["area"] == "Booking confirmations" for r in sales_view["results"])


def test_editorial_plan(run, people, w):
    ed = w["ed"]("selling-travel", "JunJul2027", date.today() + timedelta(days=40))
    ed.ad_deadline = date.today() + timedelta(days=10)
    ed.theme = "Cruise special"
    w["db"].flush()
    up = run("editorial_upcoming", people["admin"], brand="Selling Travel")
    hit = next(i for i in up["issues"] if "JunJul2027" in i["issue"])
    assert hit["theme"] == "Cruise special" and hit["link"] == f"/editorial/issues/{ed.id}"
    dl = run("editorial_deadlines", people["admin"], days=20)
    assert any(d["what"] == "Advertising deadline" and "JunJul2027" in d["issue"] for d in dl["deadlines"])
    one = run("editorial_issue", people["admin"], issue=str(ed.id))
    assert one["theme"] == "Cruise special" and one["deadlines"]["advertising"]


def test_rest_of_the_crm(run, people):
    db = people["db"]
    db.add(Feedback(id=uuid.uuid4(), user_name="Sally", kind="confusing", message="Where is the invoice button?", page_path="/sales/deals",
                    status="new", me_too=[], comments=[], elements=[], context={}))
    db.flush()
    assert run("feedback_open", people["sales"])["open"][0]["said"].startswith("Where is")
    assert "see_all" in run("data_health", people["admin"])
    assert run("data_health", people["sales"])["error"].startswith(NO)
    assert "groups" in run("crm_groups", people["admin"])
    assert "people" in run("team_activity", people["admin"])
    assert "calls" in run("calls_recent", people["sales"])
