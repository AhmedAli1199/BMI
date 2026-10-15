"""Keeps the assistant's search index up to date (app/brain/search.py): every 15 minutes it picks up notes,
history, activities, call notes and opportunities that are new or changed, and drops ones that were deleted.
ON by default: it only reads, and only adds to the assistant's own index."""
from __future__ import annotations

import logging

from app.automations.scheduler import ScheduledJob, register_job
from app.db.session import SessionLocal

logger = logging.getLogger("app.automations.brain_jobs")


def _run() -> None:
    from app.brain.search import index_pending
    db = SessionLocal()
    try:
        total = {"indexed": 0, "removed": 0, "embedded": 0}
        for _ in range(20):   # up to 20 batches a run (a first fill of a big database takes a few runs)
            out = index_pending(db)
            for k in total:
                total[k] += out[k]
            if not out["indexed"] and not out["embedded"]:
                break
        logger.info("brain_index: %s", total)
    finally:
        db.close()


register_job(ScheduledJob(
    id="brain_index", label="Assistant search index",
    description="Every 15 minutes: adds new and changed notes, history, activities and call notes to what the Ask AI assistant can search.",
    cron="*/15 * * * *", func=_run, enabled_flag="automations_brain_index_enabled",
))
