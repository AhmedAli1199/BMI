"""Repeating activities ("Repeats" on Log or schedule): when one is marked done, the next one is scheduled.

The calendar is a task list (open / overdue / done), so only the next occurrence is ever open - no pile of future
copies to wade through or tidy up when the repeat stops. Clearing it schedules the one after, and so on; setting
Repeats back to Never stops it. The next one is the first date in the pattern after today (a weekly call cleared
three weeks late isn't re-created already overdue).
"""
from __future__ import annotations

import calendar
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Activity


def _step(start: datetime, recurrence: str, n: int) -> datetime | None:
    if recurrence == "daily":
        return start + timedelta(days=n)
    if recurrence == "weekly":
        return start + timedelta(weeks=n)
    if recurrence == "monthly":
        y, m = divmod(start.month - 1 + n, 12)
        y += start.year
        return start.replace(year=y, month=m + 1, day=min(start.day, calendar.monthrange(y, m + 1)[1]))
    return None


def schedule_next(db: Session, a: Activity, now: datetime | None = None) -> Activity | None:
    """The next occurrence of a repeating activity that has just been marked done. None if it doesn't repeat,
    or the next one is already there (e.g. it was marked done, undone and done again)."""
    if (a.recurrence or "never") == "never" or not a.start_at:
        return None
    now = now or datetime.now(timezone.utc)
    start = a.start_at if a.start_at.tzinfo else a.start_at.replace(tzinfo=timezone.utc)
    n, nxt = 1, _step(start, a.recurrence, 1)
    while nxt is not None and nxt <= now and n < 1000:
        n += 1
        nxt = _step(start, a.recurrence, n)
    if nxt is None:
        return None
    same = select(Activity.id).where(Activity.start_at == nxt, Activity.recurrence == a.recurrence,
                                     Activity.subject.is_(None) if a.subject is None else Activity.subject == a.subject,
                                     Activity.contact_id.is_(None) if a.contact_id is None else Activity.contact_id == a.contact_id,
                                     Activity.company_id.is_(None) if a.company_id is None else Activity.company_id == a.company_id)
    if db.scalar(same.limit(1)):
        return None
    copy = Activity(
        id=uuid.uuid4(), source_db=a.source_db, source_act_id=str(uuid.uuid4()),
        contact_id=a.contact_id, company_id=a.company_id, activity_type=a.activity_type, subject=a.subject,
        details=a.details, location=a.location, start_at=nxt,
        end_at=(nxt + (a.end_at - a.start_at)) if a.end_at and a.end_at >= a.start_at else None,
        is_timeless=a.is_timeless, is_private=a.is_private, priority=a.priority or "normal",
        duration_minutes=a.duration_minutes, organized_by_name=a.organized_by_name, recurrence=a.recurrence,
        created_by_user_id=a.created_by_user_id,
    )
    db.add(copy)
    return copy
