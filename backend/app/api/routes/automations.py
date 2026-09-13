from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import ScheduledJobOut
from app.automations.scheduler import all_jobs, is_enabled

router = APIRouter(prefix="/automations", tags=["automations"])


@router.get("/jobs", response_model=list[ScheduledJobOut])
def list_jobs() -> list[ScheduledJobOut]:
    """Status of every registered producer job (see
    app/automations/scheduler.py) - purely informational, so the overview
    screen can show "what's live vs. still switched off" without exposing
    any way to flip it from here. Toggling stays an env-var + restart
    decision, deliberately outside the app's own reach."""
    return [
        ScheduledJobOut(
            id=j.id,
            label=j.label,
            description=j.description,
            cron=j.cron,
            enabled=is_enabled(j),
        )
        for j in all_jobs()
    ]
