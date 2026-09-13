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
app/core/config.py). Flip one on by setting its env var to true and
restarting the container - no code change and no redeploy needed for
that switch, only for adding or editing a job itself. This is the
"easily switch on later" mechanism: the schedule and the job body are
code (reviewed, versioned, identical across environments); only the
on/off bit is environment-specific config, exactly like API_KEY or
DATABASE_URL already are.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings

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


_JOBS: list[ScheduledJob] = []


def register_job(job: ScheduledJob) -> None:
    if any(j.id == job.id for j in _JOBS):
        raise ValueError(f"Scheduled job {job.id!r} is already registered")
    _JOBS.append(job)


def all_jobs() -> list[ScheduledJob]:
    return list(_JOBS)


def is_enabled(job: ScheduledJob) -> bool:
    return bool(getattr(settings, job.enabled_flag))


_scheduler: BackgroundScheduler | None = None


def _run_guarded(job: ScheduledJob) -> None:
    """Wraps every job body so one automation's bug can't crash the
    scheduler thread (or take every other job down with it)."""
    logger.info("automation job starting: %s", job.id)
    try:
        job.func()
    except Exception:
        logger.exception("automation job failed: %s", job.id)
    else:
        logger.info("automation job finished: %s", job.id)


def start_scheduler() -> BackgroundScheduler:
    """Called once at app startup. Builds the scheduler fresh from
    whatever is currently registered + currently enabled, so the running
    set always matches the current env vars at boot."""
    global _scheduler
    scheduler = BackgroundScheduler(timezone="UTC")
    for job in _JOBS:
        if not is_enabled(job):
            logger.info(
                "automation job registered but OFF: %s (set %s=true to enable)",
                job.id,
                job.enabled_flag.upper(),
            )
            continue
        scheduler.add_job(
            _run_guarded,
            CronTrigger.from_crontab(job.cron, timezone="UTC"),
            args=[job],
            id=job.id,
            replace_existing=True,
        )
        logger.info("automation job scheduled: %s (%s)", job.id, job.cron)
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
