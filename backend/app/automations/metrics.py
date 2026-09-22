"""SALES-013's "metrics store" (actioned/outstanding per rep per day) -
deliberately NOT a new table with its own write path. Every fact the
spec's metrics store wants already lives on ReviewQueueItem (status,
resolved_action, created_at, reviewed_at) plus the same owner-resolution
logic morning_queue.py already has - this module only aggregates that
existing data, on read. No new writes anywhere in this file; nothing here
can ever drift from the real review-queue state, because it doesn't keep
its own copy of it.

"Outstanding" is inherently a point-in-time count (how many are pending
right now), not a per-day one - there's no daily snapshot job, and adding
one just to plot a fake-precise outstanding-per-day chart would be
manufacturing data. "Actioned" genuinely is per-day (a real
resolved/reviewed_at timestamp), so that's what gets a daily breakdown;
outstanding is reported once, as of now, per rep.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.automations.morning_queue import _SOURCE_KINDS, _resolve_owner
from app.models import ReviewQueueItem


def _day_bucket(dt: datetime) -> date:
    return dt.astimezone(timezone.utc).date() if dt.tzinfo else dt.date()


def get_rep_metrics(db: Session, days: int = 14) -> dict:
    """Returns {"range_start", "range_end", "reps": [{"owner_name",
    "owner_user_id", "outstanding_now", "actioned_by_day": [{"date",
    "approved", "rejected"}], "actioned_total"}]} - one entry per rep who
    has ANY signal_trigger/followup_due item (pending or resolved) in the
    window, "Unassigned" included so nothing silently vanishes from the
    picture, same rule morning_queue.py already follows."""
    range_end = datetime.now(timezone.utc)
    range_start = range_end - timedelta(days=days)

    pending_items = (
        db.query(ReviewQueueItem)
        .filter(ReviewQueueItem.kind.in_(_SOURCE_KINDS), ReviewQueueItem.status == "pending")
        .all()
    )
    resolved_items = (
        db.query(ReviewQueueItem)
        .filter(
            ReviewQueueItem.kind.in_(_SOURCE_KINDS),
            ReviewQueueItem.status.in_(["approved", "rejected"]),
            ReviewQueueItem.reviewed_at >= range_start,
        )
        .all()
    )

    outstanding_by_rep: dict[tuple[str | None, str], int] = defaultdict(int)
    for item in pending_items:
        owner_id, owner_name = _resolve_owner(db, item)
        outstanding_by_rep[(owner_id, owner_name)] += 1

    # {(owner_id, owner_name): {day: {"approved": n, "rejected": n}}}
    actioned_by_rep: dict[tuple[str | None, str], dict[date, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: {"approved": 0, "rejected": 0}))
    for item in resolved_items:
        if not item.reviewed_at:
            continue
        owner_id, owner_name = _resolve_owner(db, item)
        day = _day_bucket(item.reviewed_at)
        actioned_by_rep[(owner_id, owner_name)][day][item.status] += 1

    reps: dict[tuple[str | None, str], dict] = {}
    for key in set(outstanding_by_rep) | set(actioned_by_rep):
        owner_id, owner_name = key
        by_day = actioned_by_rep.get(key, {})
        actioned_by_day = [
            {"date": d.isoformat(), "approved": counts["approved"], "rejected": counts["rejected"]}
            for d, counts in sorted(by_day.items())
        ]
        reps[key] = {
            "owner_user_id": owner_id,
            "owner_name": owner_name,
            "outstanding_now": outstanding_by_rep.get(key, 0),
            "actioned_by_day": actioned_by_day,
            "actioned_total": sum(c["approved"] + c["rejected"] for c in by_day.values()),
        }

    ordered = sorted(reps.values(), key=lambda r: (r["owner_name"] == "Unassigned", r["owner_name"]))
    return {"range_start": range_start.isoformat(), "range_end": range_end.isoformat(), "reps": ordered}
