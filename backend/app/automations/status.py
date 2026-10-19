"""Every automation's live state in one place: on or off (and which setting does that), the schedule in plain
words, when it last ran and how that went, when it runs next, the review cards it makes and how many are waiting,
and its settings with their current values. The assistant reads this (app/brain/tools/automations.py); the
Automations Hub shows the same facts from the same tables.

Never returns the raw error text of a failed run (that's for the logs) - only that it had a problem.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.automations.registry import all_kinds
from app.automations.scheduler import ScheduledJob, all_jobs
from app.automations.settings_registry import AUTOMATION_SETTING_DEFS
from app.automations.workstreams import KIND_JOB, WORKSTREAMS
from app.models import AutomationJobRun, ReviewQueueItem

_DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


_UK = ZoneInfo("Europe/London")
_DAY_NUMBER = {str(i): i for i in range(7)} | {"7": 0}


def _uk_time(hour: int, minute: int, on: date) -> tuple[str, int]:
    """A UTC time of day as UK clock time on that date (GMT or BST), and how many days it moved (-1, 0 or 1)."""
    uk = datetime(on.year, on.month, on.day, hour, minute, tzinfo=timezone.utc).astimezone(_UK)
    return f"{uk.hour:02d}:{uk.minute:02d}", (uk.date() - on).days


def _days_words(dow: str, shift: int) -> str | None:
    """'1-5' -> 'Monday to Friday', '0' -> 'Sunday' (moved by `shift` days when the UK time crosses midnight)."""
    def name(d: str) -> str:
        return _DAYS[(_DAY_NUMBER[d] + shift) % 7]
    try:
        if "-" in dow:
            first, last = dow.split("-")
            return f"{name(first)} to {name(last)}"
        names = [name(d) for d in dow.split(",")]
        return f"every {names[0]}" if len(names) == 1 else "on " + ", ".join(names)
    except KeyError:
        return None


def schedule_words(cron: str, on: date | None = None) -> str:
    """A job's schedule in plain words, in UK time. Jobs run on UTC cron times; this converts them to the UK clock
    (GMT in winter, BST in summer) for the date `on` (today by default).
    '*/15 * * * *' -> 'every 15 minutes'; '0 7 * * 1-5' -> 'at 08:00 UK time, Monday to Friday' (in summer)."""
    on = on or datetime.now(timezone.utc).date()
    try:
        minute, hour, dom, month, dow = cron.split()
    except ValueError:
        return "on a custom schedule"
    if month != "*":
        return "on a custom schedule"
    if minute == "*" and hour == dom == dow == "*":
        return "every minute"
    if minute.startswith("*/") and minute[2:].isdigit() and hour == dom == dow == "*":
        return "every minute" if minute[2:] == "1" else f"every {minute[2:]} minutes"
    if minute.isdigit() and hour == "*" and dom == dow == "*":
        return "every hour, on the hour" if int(minute) == 0 else f"every hour at {int(minute)} minutes past"
    if minute.isdigit() and hour.startswith("*/") and hour[2:].isdigit() and dom == dow == "*":
        return f"every {hour[2:]} hours"
    m = int(minute) if minute.isdigit() else None
    if m is None:
        return "on a custom schedule"
    shift = 0
    if hour.isdigit() or (hour.replace(",", "").isdigit() and "," in hour):
        parts = [_uk_time(int(h), m, on) for h in hour.split(",")]
        shift = parts[0][1]
        when = "at " + ", ".join(t for t, _ in parts) + " UK time"
    elif "-" in hour and all(x.isdigit() for x in hour.split("-", 1)):
        first, last = (int(x) for x in hour.split("-", 1))
        (start, shift), (end, _) = _uk_time(first, m, on), _uk_time(last, m, on)
        when = f"every hour from {start} to {end} UK time"
    else:
        return "on a custom schedule"
    if dow != "*":
        days = _days_words(dow, shift)
        if days is None:
            return "on a custom schedule"
        return f"{when}, {days}"
    if dom != "*":
        return f"{when}, on day {dom} of the month"
    return f"every day {when}" if when.startswith("at ") else when


def _next(job: ScheduledJob, now: datetime) -> datetime | None:
    try:
        from apscheduler.triggers.cron import CronTrigger
        return CronTrigger.from_crontab(job.cron, timezone="UTC").get_next_fire_time(None, now)
    except Exception:
        return None


def _ago(t: datetime | None, now: datetime) -> str | None:
    if not t:
        return None
    mins = int((now - t).total_seconds() // 60)
    if mins < 1:
        return "just now"
    if mins < 120:
        return f"{mins} minutes ago"
    if mins < 2880:
        return f"{mins // 60} hours ago"
    return f"{mins // 1440} days ago"


def settings_link(group: str | None) -> str:
    """The Automation settings page opened on this area (same slug as the page's ?area=)."""
    if not group:
        return "/automations/settings"
    slug = "-".join(w for w in "".join(c if c.isalnum() else " " for c in group.lower()).split())
    return f"/automations/settings?area={slug}"


def setting_view(db: Session, d) -> dict:
    from app.core.config import settings
    value = runtime_settings.effective_value(db, d.key)
    default = getattr(settings, d.key, None)
    return {"key": d.key, "setting": d.label, "what_it_does": d.description, "value": value,
            "default": default, "changed_from_default": value != default, "group": d.group}


def _group_of(job: ScheduledJob) -> str | None:
    d = next((x for x in AUTOMATION_SETTING_DEFS if x.key == job.enabled_flag), None)
    return d.group if d else None


def _workstream_of(job_id: str) -> tuple[str, str] | None:
    kinds = {k for k, j in KIND_JOB.items() if j == job_id}
    for w in WORKSTREAMS:
        if kinds & set(w.kinds):
            return w.id, w.label
    return None


def overview(db: Session, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    jobs = all_jobs()
    latest = {r.job_id: r for r in db.scalars(
        select(AutomationJobRun).distinct(AutomationJobRun.job_id)
        .order_by(AutomationJobRun.job_id, AutomationJobRun.started_at.desc()))}
    week = now - timedelta(days=7)
    failed = dict(db.execute(select(AutomationJobRun.job_id, func.count()).where(
        AutomationJobRun.started_at >= week, AutomationJobRun.status == "failed").group_by(AutomationJobRun.job_id)).all())
    pending = dict(db.execute(select(ReviewQueueItem.kind, func.count()).where(ReviewQueueItem.status == "pending")
                              .group_by(ReviewQueueItem.kind)).all())
    labels = {k.kind: k.label for k in all_kinds()}
    out = []
    for j in jobs:
        run = latest.get(j.id)
        kinds = [k for k, job in KIND_JOB.items() if job == j.id]
        ws = _workstream_of(j.id)
        on = runtime_settings.get_bool(db, j.enabled_flag)   # same as is_enabled(j), without a new connection per job
        nxt = _next(j, now) if on else None
        out.append({
            "id": j.id, "name": j.label, "what_it_does": j.description, "on": on,
            "switched_by": next((d.label for d in AUTOMATION_SETTING_DEFS if d.key == j.enabled_flag), None),
            "schedule": schedule_words(j.cron),
            "last_run": None if not run else {
                "when": _ago(run.started_at, now), "at": run.started_at.isoformat(),
                "result": {"success": "finished fine", "failed": "stopped with a problem", "running": "still running"}.get(run.status, run.status),
                "cards_made": run.items_queued},
            "problems_this_week": failed.get(j.id, 0),
            "next_run": nxt.isoformat() if nxt else None,
            "cards": [{"kind": k, "card": labels.get(k, k), "waiting": pending.get(k, 0)} for k in kinds],
            "area": ws[1] if ws else (_group_of(j) or "Other"),
            "link": f"/automations/{ws[0]}" if ws else "/automations/engine",
        })
    # cards people make themselves (a photo upload, a booking check) have no schedule
    manual = [k for k, job in KIND_JOB.items() if job is None]
    if manual:
        out.append({"id": "made_by_people", "name": "Cards made by people (not on a schedule)", "on": True,
                    "what_it_does": "Business cards and photos people upload, booking checks, booking changes, online bookings and call notes.",
                    "schedule": "whenever someone does it", "last_run": None, "problems_this_week": 0, "next_run": None,
                    "cards": [{"kind": k, "card": labels.get(k, k), "waiting": pending.get(k, 0)} for k in manual],
                    "area": "Various", "link": "/automations/review"})
    return out


def detail(db: Session, job_id: str, now: datetime | None = None) -> dict | None:
    now = now or datetime.now(timezone.utc)
    job = next((j for j in all_jobs() if j.id == job_id), None)
    if not job:
        return None
    base = next(x for x in overview(db, now) if x["id"] == job_id)
    group = _group_of(job)
    runs = db.scalars(select(AutomationJobRun).where(AutomationJobRun.job_id == job_id)
                      .order_by(AutomationJobRun.started_at.desc()).limit(6)).all()
    month = now - timedelta(days=30)
    kinds = [c["kind"] for c in base["cards"]]
    handled = {}
    if kinds:
        for kind, status, n in db.execute(select(ReviewQueueItem.kind, ReviewQueueItem.status, func.count())
                                          .where(ReviewQueueItem.kind.in_(kinds), ReviewQueueItem.created_at >= month)
                                          .group_by(ReviewQueueItem.kind, ReviewQueueItem.status)).all():
            handled.setdefault(kind, {})[status] = n
    reg = {k.kind: k for k in all_kinds()}
    return {
        **base,
        "settings": [setting_view(db, d) for d in AUTOMATION_SETTING_DEFS if group and d.group == group],
        "recent_runs": [{"when": _ago(r.started_at, now), "result": "finished fine" if r.status == "success" else
                         "stopped with a problem" if r.status == "failed" else r.status, "cards_made": r.items_queued,
                         "how": "run by hand" if r.trigger == "manual" else "on schedule"} for r in runs],
        "cards": [{**c, "about": reg[c["kind"]].description if c["kind"] in reg else None,
                   "buttons": [a.label for a in reg[c["kind"]].actions] if c["kind"] in reg else [],
                   "last_30_days": handled.get(c["kind"], {})} for c in base["cards"]],
        "settings_link": settings_link(group),
        "problem_note": "Technical details of a failed run are on Automations > Scanners." if base["problems_this_week"] else None,
    }
