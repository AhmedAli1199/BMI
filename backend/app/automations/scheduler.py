"""In-process cron scheduler for automation *producer* jobs - the pollers
that scan mailboxes and write new review_queue rows (as opposed to
registry.py, which handles a human resolving those rows).

Deliberately NOT a platform cron feature (Render Cron Jobs, a Dokploy
Schedule, a k8s CronJob...). The whole point is that this repo's deploy
target can change - Render today, Dokploy next - without any scheduling
config living outside the codebase. APScheduler runs inside the same
always-on backend process/container that already serves the API, so
"add a cron job" is just: write the function, register it with a cron
expression below, and it runs anywhere this container runs. Nothing to
click through in a platform dashboard, nothing to remember to recreate
on the next migration.

Every job defaults OFF (see Settings.automations_* flags in
app/core/config.py). Flip one on either via its env var (needs a restart)
or from the Automations Settings UI (app/automations/runtime_settings.py) -
every job is always registered into APScheduler at startup, and
is_enabled() is checked fresh at *fire time* inside _run_guarded, not just
once at boot, so a UI toggle takes effect on the job's very next scheduled
tick with no restart needed.
"""
from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("app.automations.scheduler")


@dataclass(frozen=True)
class ScheduledJob:
    id: str
    label: str
    description: str
    cron: str  # standard 5-field crontab expression, evaluated in UTC
    func: Callable[[], None]
    # Name of the boolean attribute on app.core.config.Settings that gates
    # this job - e.g. "automations_bounce_scan_enabled". Looked up by name
    # (rather than passing the bool directly) so toggling the env var and
    # restarting is enough; nothing needs re-importing.
    enabled_flag: str
    # Prefix of this job's AutomationState cursor key(s), if it has one -
    # e.g. "bounce_scan:" (one row per mailbox) or "dedupe_scan_cursor"
    # (a single row). Lets the UI offer "reset & rescan" without each job
    # needing its own reset endpoint - see automations.py's
    # /jobs/{id}/reset-cursor route. None for a job with no cursor to reset
    # (nothing to gain from resetting followup_engine_scan, which windows
    # off dates, not a remembered position).
    cursor_prefix: str | None = None


_JOBS: list[ScheduledJob] = []


def register_job(job: ScheduledJob) -> None:
    if any(j.id == job.id for j in _JOBS):
        raise ValueError(f"Scheduled job {job.id!r} is already registered")
    _JOBS.append(job)


def all_jobs() -> list[ScheduledJob]:
    return list(_JOBS)


def is_enabled(job: ScheduledJob) -> bool:
    """Effective enabled state - a stored override (set via the
    Automations Settings UI) if there is one, else the env var default.
    Opens its own short-lived session rather than taking one as an
    argument, since this is called from both a request (which has a db
    session already) and the scheduler thread (which doesn't)."""
    from app.automations.runtime_settings import get_bool
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        return get_bool(db, job.enabled_flag)
    finally:
        db.close()


_scheduler: BackgroundScheduler | None = None

# Guards against the SAME job running twice concurrently - the scheduled
# cron tick (background thread) and a manual "Run now" click (a request
# thread) are two independent code paths with no shared coordination
# otherwise, and they *have* overlapped in production: both sessions saw
# no cursor row yet for the same mailbox, both tried to insert one, and
# the second hit a UniqueViolation on automation_state_pkey. That specific
# crash is now impossible either way (state.py's set_state is a real
# upsert), but two overlapping runs of the same scan is still wasted work
# - duplicate Graph API calls, duplicate LLM calls, duplicate everything -
# worth preventing outright, not just surviving.
_running_job_ids: set[str] = set()
_running_lock = threading.Lock()


def _start_run_record(job: ScheduledJob, trigger: str):
    """Best-effort run-history row (see models/job_run.py). Uses its own
    short-lived session so a job's own transaction can never roll it back,
    and a failure to write history never stops the job itself from
    running."""
    from app.db.session import SessionLocal
    from app.models import AutomationJobRun

    db = SessionLocal()
    try:
        run = AutomationJobRun(id=uuid.uuid4(), job_id=job.id, trigger=trigger, status="running",
                               started_at=datetime.now(timezone.utc))
        db.add(run)
        db.commit()
        return run.id, run.started_at
    except Exception:
        logger.exception("couldn't record run start for %s", job.id)
        db.rollback()
        return None, datetime.now(timezone.utc)
    finally:
        db.close()


def _finish_run_record(job: ScheduledJob, run_id, started_at: datetime, error: BaseException | None) -> None:
    """Closes the run row, counting the review items this job's kinds
    gained while it ran (created_at inside the run window) - jobs don't
    return a count themselves, and this is the one number the Scanners
    page most needs ("did it find anything?")."""
    if run_id is None:
        return
    from sqlalchemy import func, select

    from app.automations.workstreams import kinds_for_job
    from app.db.session import SessionLocal
    from app.models import AutomationJobRun, ReviewQueueItem

    db = SessionLocal()
    try:
        finished_at = datetime.now(timezone.utc)
        kinds = kinds_for_job(job.id)
        queued = 0
        if kinds:
            queued = db.scalar(
                select(func.count()).select_from(ReviewQueueItem).where(
                    ReviewQueueItem.kind.in_(kinds),
                    ReviewQueueItem.created_at >= started_at,
                    ReviewQueueItem.created_at <= finished_at,
                )
            ) or 0
        run = db.get(AutomationJobRun, run_id)
        if run:
            run.finished_at = finished_at
            run.status = "failed" if error else "success"
            run.items_queued = queued
            run.error = f"{type(error).__name__}: {error}"[:2000] if error else None
            db.commit()
    except Exception:
        logger.exception("couldn't record run finish for %s", job.id)
        db.rollback()
    finally:
        db.close()


def run_job(job: ScheduledJob, trigger: str = "scheduled") -> bool:
    """The one place a job's func() actually gets called from - both the
    scheduler's cron tick and the manual "Run now" API route go through
    this, so the concurrency guard applies to either trigger source
    equally. Raises whatever job.func() raises (callers decide how to
    surface it - _run_guarded below logs and swallows it for the
    scheduler thread, the API route turns it into an HTTP error). Returns
    False (and does nothing else) if this exact job is already running -
    True means it actually ran."""
    with _running_lock:
        if job.id in _running_job_ids:
            logger.info("automation job skipped (already running): %s", job.id)
            return False
        _running_job_ids.add(job.id)
    run_id, started_at = _start_run_record(job, trigger)
    error: BaseException | None = None
    try:
        job.func()
    except BaseException as e:
        error = e
        raise
    finally:
        _finish_run_record(job, run_id, started_at, error)
        with _running_lock:
            _running_job_ids.discard(job.id)
    return True


def _run_guarded(job: ScheduledJob) -> None:
    """Wraps every job body so one automation's bug can't crash the
    scheduler thread (or take every other job down with it). Also the
    runtime enabled-check: every job is always scheduled into APScheduler
    (see start_scheduler), so a UI toggle to "off" takes effect here, on
    the very next tick, without needing to touch or restart the scheduler
    itself."""
    if not is_enabled(job):
        logger.info("automation job skipped (disabled): %s", job.id)
        return
    logger.info("automation job starting: %s", job.id)
    try:
        run_job(job)
    except Exception:
        logger.exception("automation job failed: %s", job.id)
    else:
        logger.info("automation job finished: %s", job.id)


def start_scheduler() -> BackgroundScheduler:
    """Called once at app startup. Every registered job is scheduled
    unconditionally - enabled/disabled is checked at fire time (see
    _run_guarded), not here, so flipping a job on or off from the
    Automations Settings UI takes effect on its next tick without a
    restart."""
    global _scheduler
    scheduler = BackgroundScheduler(timezone="UTC")
    for job in _JOBS:
        scheduler.add_job(
            _run_guarded,
            CronTrigger.from_crontab(job.cron, timezone="UTC"),
            args=[job],
            id=job.id,
            replace_existing=True,
        )
        logger.info("automation job scheduled: %s (%s) - currently %s",
                     job.id, job.cron, "ON" if is_enabled(job) else "OFF")
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
