"""The shared calendar job (see app/services/calendar_sync.py). ON by default: it only acts on calendars
people chose to connect, and each person controls their own recording preference."""
from __future__ import annotations

import logging

from app.automations.scheduler import ScheduledJob, register_job
from app.db.session import SessionLocal

logger = logging.getLogger("app.automations.calendar_jobs")


def _run() -> None:
    from app.services.calendar_sync import run
    db = SessionLocal()
    try:
        logger.info("calendar_sync: %s", run(db))
    finally:
        db.close()


register_job(ScheduledJob(
    id="calendar_sync", label="Shared calendar",
    description="Every 3 minutes: reads connected Google and Outlook calendars into the shared calendar, and books or calls off BMI Notetaker for meetings starting soon.",
    cron="*/3 * * * *", func=_run, enabled_flag="automations_calendar_sync_enabled",
))
