"""One row per scheduled-job execution - when it started, how it ended,
how many review items it queued, and the error if it failed. Written by
scheduler.run_job (the single path every run goes through, cron tick or
"Run now") so the Scanners page can show real run history instead of just
whether a job is switched on.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import UUIDPk


class AutomationJobRun(Base, UUIDPk):
    __tablename__ = "automation_job_runs"

    job_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # "scheduled" (cron tick) | "manual" (Run now button)
    trigger: Mapped[str] = mapped_column(String(16), nullable=False, default="scheduled")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # "running" | "success" | "failed"
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    items_queued: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text)
