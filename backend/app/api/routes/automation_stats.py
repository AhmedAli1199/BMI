"""Read-only stats for the Automations Hub's workstream pages - every
figure here is aggregation over review_queue (created_at = "new",
reviewed_at = "resolved"), automation_job_runs and llm_usage_events. No
new tracking beyond the job-run history.

Kept in its own module rather than growing automations.py further; same
/automations prefix and the same staff-only gate.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import Date, cast, extract, func, select, true
from sqlalchemy.orm import Session

from app.api.routes.automations import require_staff
from app.api.routes.review_queue import _apply_scope
from app.automations import get_kind
from app.automations.scheduler import all_jobs, is_enabled
from app.automations.workstreams import KIND_COST_PREFIX, KIND_JOB, WORKSTREAMS, get_workstream
from app.core.identity import Identity
from app.db.session import get_db
from app.models import AutomationJobRun, LlmUsageEvent, ReviewQueueItem, User

router = APIRouter(prefix="/automations", tags=["automation-stats"])

Range = Literal["7d", "30d", "all"]
# "All time" still needs a bounded chart - 90 daily bars is the most that
# stays readable; the summary numbers above it are genuinely all-time.
_ALL_TIME_CHART_DAYS = 90


# ---- Schemas ---------------------------------------------------------------

class JobRunOut(BaseModel):
    id: str
    job_id: str
    trigger: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str
    items_queued: int
    error: str | None = None


class JobSummary(BaseModel):
    id: str
    label: str
    cron: str
    enabled: bool
    last_run: JobRunOut | None = None


class DayPoint(BaseModel):
    date: date
    new: int
    resolved: int
    backlog: int


class Totals(BaseModel):
    pending: int
    oldest_pending_at: datetime | None = None
    new: int
    resolved: int
    approved: int
    rejected: int
    # Previous equal-length period, for the delta arrows. None for "all".
    new_prev: int | None = None
    resolved_prev: int | None = None
    acted_on_rate: float | None = None  # approved / (approved + rejected); None when nothing resolved
    median_resolve_seconds: float | None = None


class AutomationStats(Totals):
    kind: str
    label: str
    description: str
    job: JobSummary | None = None
    daily_new: list[int]


class WorkstreamStats(BaseModel):
    id: str
    label: str
    tagline: str
    range: str
    chart_days: int
    totals: Totals
    daily: list[DayPoint]
    automations: list[AutomationStats]


class WorkstreamSummary(BaseModel):
    id: str
    label: str
    tagline: str
    kinds: list[str]
    pending: int
    new_7d: int
    resolved_7d: int
    daily_new_7d: list[int]


class OutcomeCount(BaseModel):
    action_id: str
    label: str
    status: str
    count: int


class ReviewerCount(BaseModel):
    name: str
    count: int


class RecentItem(BaseModel):
    id: str
    summary: str
    status: str
    created_at: datetime


class KindDetail(BaseModel):
    kind: str
    outcomes: list[OutcomeCount]
    top_reviewers: list[ReviewerCount]
    ai_cost_usd: float | None = None
    ai_calls: int | None = None
    # Other kinds whose AI calls share this cost figure (same scanner
    # module) - the UI says "shared with ..." instead of pretending the
    # whole figure belongs to this one automation.
    ai_cost_shared_with: list[str] = []
    recent: list[RecentItem]


# ---- Helpers ---------------------------------------------------------------

def _window(range_: Range) -> tuple[datetime | None, datetime | None, int]:
    """(start, prev_start, chart_days). start None means all-time."""
    now = datetime.now(timezone.utc)
    if range_ == "all":
        return None, None, _ALL_TIME_CHART_DAYS
    days = 7 if range_ == "7d" else 30
    start = now - timedelta(days=days)
    return start, start - timedelta(days=days), days


def _job_lookup(db: Session) -> dict[str, JobSummary]:
    """Every registered job plus its latest run, in one query for the runs."""
    latest = {
        r.job_id: r
        for r in db.scalars(
            select(AutomationJobRun).distinct(AutomationJobRun.job_id)
            .order_by(AutomationJobRun.job_id, AutomationJobRun.started_at.desc())
        )
    }
    out: dict[str, JobSummary] = {}
    for j in all_jobs():
        run = latest.get(j.id)
        out[j.id] = JobSummary(
            id=j.id, label=j.label, cron=j.cron, enabled=is_enabled(j),
            last_run=_run_out(run) if run else None,
        )
    return out


def _run_out(r: AutomationJobRun) -> JobRunOut:
    return JobRunOut(
        id=str(r.id), job_id=r.job_id, trigger=r.trigger, started_at=r.started_at,
        finished_at=r.finished_at, status=r.status, items_queued=r.items_queued, error=r.error,
    )


def _per_kind_totals(db: Session, identity: Identity, kinds: list[str], start: datetime | None, prev_start: datetime | None) -> dict[str, dict]:
    """One grouped query for every number in the automations table."""
    rq = ReviewQueueItem
    in_range_created = rq.created_at >= start if start is not None else true()
    in_range_reviewed = rq.reviewed_at >= start if start else rq.reviewed_at.isnot(None)
    resolve_secs = extract("epoch", rq.reviewed_at - rq.created_at)

    cols = [
        rq.kind,
        func.count().filter(rq.status == "pending").label("pending"),
        func.min(rq.created_at).filter(rq.status == "pending").label("oldest_pending_at"),
        func.count().filter(in_range_created).label("new"),
        func.count().filter(in_range_reviewed, rq.status != "pending").label("resolved"),
        func.count().filter(in_range_reviewed, rq.status == "approved").label("approved"),
        func.count().filter(in_range_reviewed, rq.status == "rejected").label("rejected"),
        func.percentile_cont(0.5).within_group(resolve_secs).filter(in_range_reviewed, rq.status != "pending").label("median"),
    ]
    if start is not None and prev_start is not None:
        cols += [
            func.count().filter(rq.created_at >= prev_start, rq.created_at < start).label("new_prev"),
            func.count().filter(rq.reviewed_at >= prev_start, rq.reviewed_at < start, rq.status != "pending").label("resolved_prev"),
        ]
    stmt = _apply_scope(select(*cols).where(rq.kind.in_(kinds)).group_by(rq.kind), identity)
    return {row.kind: row._asdict() for row in db.execute(stmt)}


def _acted_on(approved: int, rejected: int) -> float | None:
    total = approved + rejected
    return round(approved / total, 4) if total else None


def _daily(db: Session, identity: Identity, kinds: list[str], days: int) -> tuple[list[DayPoint], dict[str, list[int]]]:
    """New vs resolved per UTC day for the last `days` days, the workstream
    backlog at the end of each day, and each kind's own daily-new series
    (the table's sparkline)."""
    rq = ReviewQueueItem
    today = datetime.now(timezone.utc).date()
    first_day = today - timedelta(days=days - 1)
    window_start = datetime.combine(first_day, datetime.min.time(), tzinfo=timezone.utc)
    day_list = [first_day + timedelta(days=i) for i in range(days)]

    created_day = cast(func.timezone("UTC", rq.created_at), Date)
    reviewed_day = cast(func.timezone("UTC", rq.reviewed_at), Date)

    new_rows = db.execute(_apply_scope(
        select(rq.kind, created_day.label("d"), func.count())
        .where(rq.kind.in_(kinds), rq.created_at >= window_start)
        .group_by(rq.kind, created_day), identity)).all()
    res_rows = db.execute(_apply_scope(
        select(reviewed_day.label("d"), func.count())
        .where(rq.kind.in_(kinds), rq.reviewed_at >= window_start, rq.status != "pending")
        .group_by(reviewed_day), identity)).all()

    # Backlog baseline: everything created before the window minus
    # everything resolved before it.
    created_before = db.scalar(_apply_scope(
        select(func.count()).select_from(rq).where(rq.kind.in_(kinds), rq.created_at < window_start), identity)) or 0
    resolved_before = db.scalar(_apply_scope(
        select(func.count()).select_from(rq).where(
            rq.kind.in_(kinds), rq.reviewed_at < window_start, rq.status != "pending"), identity)) or 0

    new_by_day: dict[date, int] = {}
    per_kind: dict[str, dict[date, int]] = {k: {} for k in kinds}
    for kind, d, c in new_rows:
        new_by_day[d] = new_by_day.get(d, 0) + c
        per_kind.setdefault(kind, {})[d] = c
    resolved_by_day = {d: c for d, c in res_rows}

    backlog = created_before - resolved_before
    points: list[DayPoint] = []
    for d in day_list:
        n, r = new_by_day.get(d, 0), resolved_by_day.get(d, 0)
        backlog += n - r
        points.append(DayPoint(date=d, new=n, resolved=r, backlog=max(backlog, 0)))
    series = {k: [per_kind.get(k, {}).get(d, 0) for d in day_list] for k in kinds}
    return points, series


# ---- Routes ----------------------------------------------------------------

@router.get("/workstreams", response_model=list[WorkstreamSummary])
def list_workstreams(db: Session = Depends(get_db), identity: Identity = Depends(require_staff)) -> list[WorkstreamSummary]:
    """Sidebar counts and the Overview table - one row per workstream."""
    all_kinds = [k for w in WORKSTREAMS for k in w.kinds]
    start, _, _ = _window("7d")
    totals = _per_kind_totals(db, identity, all_kinds, start, None)
    _, series = _daily(db, identity, all_kinds, 7)
    out = []
    for w in WORKSTREAMS:
        rows = [totals.get(k, {}) for k in w.kinds]
        daily = [sum(series[k][i] for k in w.kinds) for i in range(7)]
        out.append(WorkstreamSummary(
            id=w.id, label=w.label, tagline=w.tagline, kinds=list(w.kinds),
            pending=sum(r.get("pending", 0) for r in rows),
            new_7d=sum(r.get("new", 0) for r in rows),
            resolved_7d=sum(r.get("resolved", 0) for r in rows),
            daily_new_7d=daily,
        ))
    return out


@router.get("/workstreams/{workstream_id}/stats", response_model=WorkstreamStats)
def workstream_stats(
    workstream_id: str,
    range: Range = Query("7d"),
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_staff),
) -> WorkstreamStats:
    w = get_workstream(workstream_id)
    if not w:
        raise HTTPException(status_code=404, detail="Unknown workstream")
    kinds = list(w.kinds)
    start, prev_start, chart_days = _window(range)
    per_kind = _per_kind_totals(db, identity, kinds, start, prev_start)
    daily, series = _daily(db, identity, kinds, chart_days)
    jobs = _job_lookup(db)

    automations: list[AutomationStats] = []
    for k in kinds:
        kd = get_kind(k)
        if not kd:
            continue
        r = per_kind.get(k, {})
        job_id = KIND_JOB.get(k)
        automations.append(AutomationStats(
            kind=k, label=kd.label, description=kd.description,
            job=jobs.get(job_id) if job_id else None,
            pending=r.get("pending", 0), oldest_pending_at=r.get("oldest_pending_at"),
            new=r.get("new", 0), resolved=r.get("resolved", 0),
            approved=r.get("approved", 0), rejected=r.get("rejected", 0),
            new_prev=r.get("new_prev", 0) if start else None,
            resolved_prev=r.get("resolved_prev", 0) if start else None,
            acted_on_rate=_acted_on(r.get("approved", 0), r.get("rejected", 0)),
            median_resolve_seconds=r.get("median"),
            daily_new=series.get(k, [0] * chart_days)[-7:] if range == "all" else series.get(k, []),
        ))

    oldest = [a.oldest_pending_at for a in automations if a.oldest_pending_at]
    approved = sum(a.approved for a in automations)
    rejected = sum(a.rejected for a in automations)
    # A workstream-wide median needs its own query - medians don't add up.
    median = None
    if kinds:
        rq = ReviewQueueItem
        in_range = rq.reviewed_at >= start if start else rq.reviewed_at.isnot(None)
        median = db.scalar(_apply_scope(
            select(func.percentile_cont(0.5).within_group(extract("epoch", rq.reviewed_at - rq.created_at)))
            .where(rq.kind.in_(kinds), in_range, rq.status != "pending"), identity))

    totals = Totals(
        pending=sum(a.pending for a in automations),
        oldest_pending_at=min(oldest) if oldest else None,
        new=sum(a.new for a in automations),
        resolved=sum(a.resolved for a in automations),
        approved=approved, rejected=rejected,
        new_prev=sum(a.new_prev or 0 for a in automations) if start else None,
        resolved_prev=sum(a.resolved_prev or 0 for a in automations) if start else None,
        acted_on_rate=_acted_on(approved, rejected),
        median_resolve_seconds=median,
    )
    return WorkstreamStats(
        id=w.id, label=w.label, tagline=w.tagline, range=range, chart_days=chart_days,
        totals=totals, daily=daily, automations=automations,
    )


@router.get("/kinds/{kind}/detail", response_model=KindDetail)
def kind_detail(
    kind: str,
    range: Range = Query("7d"),
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_staff),
) -> KindDetail:
    """The expandable row under one automation in the workstream table -
    fetched only when a row is opened, never for the whole table."""
    kd = get_kind(kind)
    if not kd:
        raise HTTPException(status_code=404, detail="Unknown automation")
    start, _, _ = _window(range)
    rq = ReviewQueueItem
    in_range = rq.reviewed_at >= start if start else rq.reviewed_at.isnot(None)

    outcome_rows = db.execute(_apply_scope(
        select(rq.resolved_action, rq.status, func.count())
        .where(rq.kind == kind, in_range, rq.status != "pending")
        .group_by(rq.resolved_action, rq.status)
        .order_by(func.count().desc()), identity)).all()
    labels = {a.id: a.label for a in kd.actions}
    outcomes = [
        OutcomeCount(action_id=a or "unknown", label=labels.get(a or "", a or "Unknown"), status=s, count=c)
        for a, s, c in outcome_rows
    ]

    reviewer_rows = db.execute(_apply_scope(
        select(User.name, func.count())
        .select_from(rq).join(User, User.id == rq.reviewed_by_user_id)
        .where(rq.kind == kind, in_range, rq.status != "pending")
        .group_by(User.name).order_by(func.count().desc()).limit(3), identity)).all()

    ai_cost = ai_calls = None
    shared: list[str] = []
    prefix = KIND_COST_PREFIX.get(kind)
    if prefix:
        cost_filter = [LlmUsageEvent.purpose.like(f"{prefix}%")]
        if start:
            cost_filter.append(LlmUsageEvent.created_at >= start)
        cost, calls = db.execute(
            select(func.coalesce(func.sum(LlmUsageEvent.estimated_cost_usd), 0.0), func.count()).where(*cost_filter)
        ).one()
        ai_cost, ai_calls = float(cost), int(calls)
        shared = [
            get_kind(k).label for k, p in KIND_COST_PREFIX.items()
            if p == prefix and k != kind and get_kind(k)
        ]

    recent = db.scalars(_apply_scope(
        select(rq).where(rq.kind == kind).order_by(rq.created_at.desc()).limit(5), identity)).all()

    return KindDetail(
        kind=kind,
        outcomes=outcomes,
        top_reviewers=[ReviewerCount(name=n, count=c) for n, c in reviewer_rows],
        ai_cost_usd=ai_cost, ai_calls=ai_calls, ai_cost_shared_with=shared,
        recent=[
            RecentItem(id=str(i.id), summary=(i.payload or {}).get("summary") or "Review item",
                       status=i.status, created_at=i.created_at)
            for i in recent
        ],
    )


@router.get("/job-runs", response_model=dict[str, list[JobRunOut]])
def job_runs(
    per_job: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    _staff: Identity = Depends(require_staff),
) -> dict[str, list[JobRunOut]]:
    """Latest N runs for every job - the Scanners page's run log."""
    ranked = select(
        AutomationJobRun,
        func.row_number().over(partition_by=AutomationJobRun.job_id, order_by=AutomationJobRun.started_at.desc()).label("rn"),
    ).subquery()
    runs = db.execute(
        select(AutomationJobRun).join(ranked, ranked.c.id == AutomationJobRun.id)
        .where(ranked.c.rn <= per_job).order_by(AutomationJobRun.job_id, AutomationJobRun.started_at.desc())
    ).scalars().all()
    out: dict[str, list[JobRunOut]] = {j.id: [] for j in all_jobs()}
    for r in runs:
        out.setdefault(r.job_id, []).append(_run_out(r))
    return out
