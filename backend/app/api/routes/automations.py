from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.orm import Session

from app.api.schemas import (
    AutomationSettingOut,
    AutomationSettingUpdate,
    LlmUsageBucket,
    LlmUsageByPurpose,
    LlmUsageSummary,
    ScheduledJobOut,
)
from app.automations import runtime_settings
from app.automations.business_card import process_business_card_photo, resolve_batch
from app.automations.metrics import get_rep_metrics
from app.automations.morning_queue import build_today_queue
from app.automations.returned_copy import process_returned_copy_photo
from app.automations.scheduler import all_jobs, is_enabled, run_job
from app.automations.settings_registry import AUTOMATION_SETTING_DEFS, get_def
from app.core.config import settings
from app.db.session import get_db
from app.models import AutomationState, Contact, EmailSignal, LlmUsageEvent, ReviewQueueItem

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
            has_cursor=j.cursor_prefix is not None,
        )
        for j in all_jobs()
    ]


@router.get("/today")
def get_today_queue(owner_user_id: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    """SALES-013's read side - see app/automations/morning_queue.py's
    docstring for why this is aggregation, not a new producer. Every
    still-pending signal_trigger/followup_due item, tagged with who it
    belongs to. Pass owner_user_id for one rep's own list; omit it for a
    manager's cross-team view grouped by rep."""
    return build_today_queue(db, owner_user_id=owner_user_id)


@router.get("/metrics")
def get_metrics(days: int = Query(14, ge=1, le=90, description="How many days back to break down 'actioned' by day."), db: Session = Depends(get_db)) -> dict:
    """SALES-013's "metrics store" read side - see
    app/automations/metrics.py's docstring for why this is aggregation
    over the existing review queue, not a new table. Per-rep outstanding
    count (as of now) plus a daily actioned breakdown over the window."""
    return get_rep_metrics(db, days=days)


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
        ran = run_job(job)
    except Exception as exc:
        # The full logs.exception() call below still carries the complete
        # traceback (and, for a SQLAlchemy error, the compiled SQL +
        # every bound parameter) - exactly what you want when debugging
        # from the logs. None of that belongs in an HTTP response a
        # frontend toast renders verbatim: str(exc) on a SQLAlchemy error
        # is a multi-line dump, easily thousands of characters, so only
        # its first line (the actual driver error message) and a hard
        # length cap ever reach the client.
        logger.exception("manual run failed for automation job: %s", job.id)
        short_reason = str(exc).splitlines()[0][:300] if str(exc) else exc.__class__.__name__
        raise HTTPException(status_code=500, detail=f"{job.id} failed: {short_reason} (see backend logs for the full error)") from exc

    if not ran:
        logger.info("manual run skipped for automation job (already running): %s", job.id)
        return {"ok": True, "job_id": job.id, "skipped": True, "message": "Already running (e.g. its scheduled tick just started) - this click didn't queue a second run. Check back shortly."}

    logger.info("manual run finished for automation job: %s", job.id)
    return {"ok": True, "job_id": job.id, "skipped": False, "message": "Ran to completion - check the review queue and logs for what it found."}


@router.post("/jobs/{job_id}/reset-cursor")
def reset_job_cursor(job_id: str, db: Session = Depends(get_db)) -> dict:
    """Deletes a job's remembered "since last run" position (see
    app/automations/state.py), so its next run treats every mailbox it
    scans as brand new - bounded only by that job's own initial-lookback
    setting, not by whatever it already processed. For pulling in a bigger
    sample to judge extraction quality against, without waiting for the
    cursor to naturally sweep back that far (or, for the mailbox scans,
    ever - a cursor only moves forward). Does not touch anything it
    already wrote (existing review-queue items, email_signals rows) -
    only the pointer for what counts as "new" next time."""
    job = next((j for j in all_jobs() if j.id == job_id), None)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No registered job with id {job_id!r}")
    if not job.cursor_prefix:
        raise HTTPException(status_code=400, detail=f"{job.id} has no cursor to reset.")

    deleted = (
        db.query(AutomationState)
        .filter(AutomationState.key.like(f"{job.cursor_prefix}%"))
        .delete(synchronize_session=False)
    )
    db.commit()
    logger.info("cursor reset for automation job: %s (%d state row(s) cleared)", job.id, deleted)
    return {"ok": True, "job_id": job.id, "cleared": deleted}


@router.post("/reset")
def reset_automation_data(
    confirm: bool = Query(False, description="Must be true - a safety catch against an accidental call."),
    reset_cursors: bool = Query(True, description="Also clear every scan job's remembered mailbox/scan position, so the next run re-reads from its configured lookback instead of picking up where it left off."),
    reset_signals: bool = Query(False, description="Also delete every EmailSignal row (SALES-010-lite's extracted budget/renewal/callback/touchpoint facts), not just the review queue built on top of them - forces a full re-extraction from scratch on the next email scan, not just re-triggering off what's already there."),
    db: Session = Depends(get_db),
) -> dict:
    """Wipes every ReviewQueueItem (every kind, every status) so the whole
    review queue starts empty. Deliberately does NOT touch the durable
    side effects an approved item already made - a merged/retired
    contact, an actioned EmailSignal, a resolved Activity, a written Note
    - none of that is undone, so re-running the scans afterward will not
    resurrect anything you already approved. The one real gap: a
    dedupe "Not relevant" verdict (duplicate_contact, rejected) has no
    memory anywhere except the row this deletes, so those specific pairs
    WILL be re-proposed on the next dedupe scan - there is nothing to
    preserve that decision by, short of not deleting that row.

    reset_signals=true goes further and clears email_summary.py's own
    output too, so both layers restart from nothing - use this only if
    you actually want signals re-extracted, not just re-surfaced.
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="Pass confirm=true to actually wipe automation data - this is destructive and not undoable from here.")

    deleted_items = db.query(ReviewQueueItem).delete(synchronize_session=False)

    deleted_cursors = 0
    if reset_cursors:
        cursor_prefixes = [j.cursor_prefix for j in all_jobs() if j.cursor_prefix]
        for prefix in cursor_prefixes:
            deleted_cursors += db.query(AutomationState).filter(AutomationState.key.like(f"{prefix}%")).delete(synchronize_session=False)

    deleted_signals = 0
    if reset_signals:
        deleted_signals = db.query(EmailSignal).delete(synchronize_session=False)

    db.commit()
    logger.warning(
        "automation data reset: %d review item(s), %d cursor row(s)%s deleted",
        deleted_items, deleted_cursors,
        f", {deleted_signals} email signal(s)" if reset_signals else "",
    )
    return {
        "ok": True,
        "deleted_review_items": deleted_items,
        "deleted_cursors": deleted_cursors,
        "deleted_signals": deleted_signals if reset_signals else None,
    }


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


@router.post("/business-cards/batches/{batch_id}/confirm")
def confirm_business_card_batch(batch_id: str, db: Session = Depends(get_db)) -> dict:
    """SALES-002's one-confirm batch write - resolves every still-pending
    review item from this upload's batch with its default action in one
    go, then posts an added/updated/skipped summary to Teams (if
    configured). See business_card.resolve_batch's own docstring for
    exactly what "default action" means per item."""
    try:
        return resolve_batch(db, batch_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


@router.get("/llm-usage", response_model=LlmUsageSummary)
def get_llm_usage(
    days: int = Query(30, ge=1, le=365, description="How many days back to summarize."),
    granularity: Literal["hour", "day"] = Query("day", description="Time-bucket width for the usage-over-time table."),
    db: Session = Depends(get_db),
) -> LlmUsageSummary:
    """Aggregated LLM cost/usage - deliberately its own out-of-the-way
    endpoint (only linked from Automations Settings, not any regularly
    used page) rather than a dashboard widget, since "how much are we
    spending on AI calls" is an occasional check-in, not something that
    needs to be in front of a reviewer every day. Every real Gemini/
    OpenAI call anywhere in the codebase logs one LlmUsageEvent row (see
    app/automations/llm.py) - this just aggregates them, it never
    computes cost itself.
    """
    range_end = datetime.now(timezone.utc)
    range_start = range_end - timedelta(days=days)

    is_failure = cast(LlmUsageEvent.success == False, Integer)  # noqa: E712 - explicit is-false, not "falsy"
    is_success = cast(LlmUsageEvent.success == True, Integer)  # noqa: E712

    totals_row = db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(is_failure), 0),
            func.coalesce(func.sum(LlmUsageEvent.estimated_cost_usd), 0.0),
            func.coalesce(func.sum(LlmUsageEvent.prompt_tokens), 0),
            func.coalesce(func.sum(LlmUsageEvent.completion_tokens), 0),
        ).where(LlmUsageEvent.created_at >= range_start)
    ).one()
    total_calls, total_failures, total_cost, total_prompt_tokens, total_completion_tokens = totals_row

    bucket_expr = func.date_trunc(granularity, LlmUsageEvent.created_at)
    bucket_rows = db.execute(
        select(
            bucket_expr.label("bucket_start"),
            func.count(),
            func.coalesce(func.sum(is_success), 0),
            func.coalesce(func.sum(is_failure), 0),
            func.coalesce(func.sum(LlmUsageEvent.prompt_tokens), 0),
            func.coalesce(func.sum(LlmUsageEvent.completion_tokens), 0),
            func.coalesce(func.sum(LlmUsageEvent.estimated_cost_usd), 0.0),
        )
        .where(LlmUsageEvent.created_at >= range_start)
        .group_by(bucket_expr)
        .order_by(bucket_expr)
    ).all()

    by_purpose_rows = db.execute(
        select(
            LlmUsageEvent.purpose,
            LlmUsageEvent.provider,
            func.count(),
            func.coalesce(func.sum(is_failure), 0),
            func.coalesce(func.sum(LlmUsageEvent.estimated_cost_usd), 0.0),
        )
        .where(LlmUsageEvent.created_at >= range_start)
        .group_by(LlmUsageEvent.purpose, LlmUsageEvent.provider)
        .order_by(func.sum(LlmUsageEvent.estimated_cost_usd).desc())
    ).all()

    return LlmUsageSummary(
        range_start=range_start, range_end=range_end,
        total_calls=total_calls, total_failures=total_failures, total_cost_usd=total_cost,
        total_prompt_tokens=total_prompt_tokens, total_completion_tokens=total_completion_tokens,
        buckets=[
            LlmUsageBucket(
                bucket_start=b.bucket_start, call_count=b[1], success_count=b[2], failure_count=b[3],
                prompt_tokens=b[4], completion_tokens=b[5], cost_usd=b[6],
            )
            for b in bucket_rows
        ],
        by_purpose=[
            LlmUsageByPurpose(purpose=p[0], provider=p[1], call_count=p[2], failure_count=p[3], cost_usd=p[4])
            for p in by_purpose_rows
        ],
    )
