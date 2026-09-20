from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.schemas import AutomationSettingOut, AutomationSettingUpdate, ScheduledJobOut
from app.automations import runtime_settings
from app.automations.business_card import process_business_card_photo
from app.automations.returned_copy import process_returned_copy_photo
from app.automations.scheduler import all_jobs, is_enabled
from app.automations.settings_registry import AUTOMATION_SETTING_DEFS, get_def
from app.core.config import settings
from app.db.session import get_db
from app.models import Contact, EmailSignal

logger = logging.getLogger("app.api.automations")

router = APIRouter(prefix="/automations", tags=["automations"])


@router.get("/jobs", response_model=list[ScheduledJobOut])
def list_jobs() -> list[ScheduledJobOut]:
    """Status of every registered producer job (see
    app/automations/scheduler.py). Reflects the *effective* enabled state -
    a stored override from the Settings tab below if there is one, else
    the env var default - and a toggle made there takes effect on the
    job's next scheduled tick with no restart needed."""
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


@router.post("/jobs/{job_id}/run")
def run_job_now(job_id: str) -> dict:
    """Fires one registered producer job immediately, out of band from its
    cron schedule - for testing a scan without waiting for it (or without
    temporarily hacking the cron string + restarting). Runs synchronously
    and inline: every job body is a fast, bounded scan (a handful of
    mailbox/DB reads), not a long-running task, so there's no need for a
    background queue here.

    Deliberately ignores the job's enabled_flag - "run this once, right
    now, so I can see what it finds" is exactly the point when you're
    testing a scan you haven't flipped on for real yet. It does NOT change
    whether the job runs on its own schedule; that's still the env-var
    toggle. Every job function already fails soft internally (catches its
    own errors so a bad mailbox message can't lose the rest of a batch),
    so a raised exception here means something genuinely broke, not "0
    found" - which is why it's surfaced as a 500 with the real message
    rather than swallowed.
    """
    job = next((j for j in all_jobs() if j.id == job_id), None)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No registered job with id {job_id!r}")

    logger.info("manual run requested for automation job: %s", job.id)
    try:
        job.func()
    except Exception as exc:
        logger.exception("manual run failed for automation job: %s", job.id)
        raise HTTPException(status_code=500, detail=f"{job.id} failed: {exc}") from exc

    logger.info("manual run finished for automation job: %s", job.id)
    return {"ok": True, "job_id": job.id, "message": "Ran to completion - check the review queue and logs for what it found."}


@router.post("/business-cards/upload")
async def upload_business_card(
    file: UploadFile = File(...),
    source_db: str = Form(...),
    show_context: str | None = Form(None),
    db: Session = Depends(get_db),
) -> dict:
    """SALES-001/002 intake - a rep uploads a photo (possibly several cards
    in one shot) from a trade show; see business_card.py for the full
    read -> match -> queue flow. Synchronous (the vision call happens
    inline, not queued) since a single-image OpenAI round trip is fast
    enough not to need a background job for this - matches how the rest
    of this codebase avoids infrastructure it doesn't need yet."""
    image_bytes = await file.read()
    result = process_business_card_photo(
        db, image_bytes, file.content_type or "image/jpeg",
        source_db=source_db, show_context=show_context,
    )
    return result


@router.post("/returned-copies/upload")
async def upload_returned_copy(
    file: UploadFile = File(...),
    source_db: str = Form(...),
    db: Session = Depends(get_db),
) -> dict:
    """CS-005 intake - a rep uploads a photo of a returned-mail label; see
    returned_copy.py for the full read -> match -> queue flow."""
    image_bytes = await file.read()
    result = process_returned_copy_photo(db, image_bytes, file.content_type or "image/jpeg", source_db=source_db)
    return result


@router.get("/settings", response_model=list[AutomationSettingOut])
def list_automation_settings(db: Session = Depends(get_db)) -> list[AutomationSettingOut]:
    """Every editable automation tunable, with its current effective value
    and whether that's a stored override or just the env var default - the
    Automations Settings UI renders entirely from this, so a new setting
    (settings_registry.py) shows up with zero frontend changes."""
    out = []
    for d in AUTOMATION_SETTING_DEFS:
        value = runtime_settings.effective_value(db, d.key)
        default = getattr(settings, d.key)
        out.append(AutomationSettingOut(
            key=d.key, label=d.label, description=d.description, group=d.group, type=d.type,
            value=value, default=default, is_overridden=(value != default),
            min=d.min, max=d.max,
        ))
    return out


@router.put("/settings/{key}", response_model=AutomationSettingOut)
def update_automation_setting(key: str, payload: AutomationSettingUpdate, db: Session = Depends(get_db)) -> AutomationSettingOut:
    """Sets (or replaces) a runtime override - takes effect on that
    setting's next read, which for a scan job means its next scheduled
    tick or "Run now" click, never requiring a restart."""
    d = get_def(key)
    if not d:
        raise HTTPException(status_code=404, detail=f"No editable automation setting {key!r}")
    try:
        runtime_settings.set_override(db, key, payload.value)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    value = runtime_settings.effective_value(db, key)
    default = getattr(settings, key)
    return AutomationSettingOut(
        key=d.key, label=d.label, description=d.description, group=d.group, type=d.type,
        value=value, default=default, is_overridden=(value != default), min=d.min, max=d.max,
    )


@router.delete("/settings/{key}", response_model=AutomationSettingOut)
def reset_automation_setting(key: str, db: Session = Depends(get_db)) -> AutomationSettingOut:
    """Removes a stored override, reverting the setting to its env var
    default - the "reset to default" action in the UI."""
    d = get_def(key)
    if not d:
        raise HTTPException(status_code=404, detail=f"No editable automation setting {key!r}")
    runtime_settings.clear_override(db, key)
    db.commit()
    value = runtime_settings.effective_value(db, key)
    return AutomationSettingOut(
        key=d.key, label=d.label, description=d.description, group=d.group, type=d.type,
        value=value, default=value, is_overridden=False, min=d.min, max=d.max,
    )


@router.get("/email-signals")
def list_email_signals(db: Session = Depends(get_db)) -> list[dict]:
    """THROWAWAY - a quick read-only visibility view into what
    email_summary.py's scan has actually extracted, so it can be judged on
    real output before SALES-012/013 get built on top of it. Not meant to
    survive as a real feature; delete once that decision's made."""
    rows = (
        db.query(EmailSignal, Contact)
        .join(Contact, Contact.id == EmailSignal.contact_id)
        .order_by(EmailSignal.created_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": str(signal.id),
            "contact_id": str(contact.id),
            "contact_name": contact.full_name or "(no name)",
            "signal_type": signal.signal_type,
            "due_date": signal.due_date.isoformat() if signal.due_date else None,
            "summary": signal.summary,
            "confidence": signal.confidence,
            "status": signal.status,
            "created_at": signal.created_at.isoformat(),
            "updated_at": signal.updated_at.isoformat(),
        }
        for signal, contact in rows
    ]
