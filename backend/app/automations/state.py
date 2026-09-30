"""Thin read/replace wrapper around AutomationState (see
app/models/automation_state.py) - the only two operations a producer job
actually needs from a cross-run cursor. Kept separate from the jobs that use
it so any future scan can reuse the same store without importing
mail-specific code.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import AutomationState


def get_state(db: Session, key: str) -> dict:
    """Returns the stored value for `key`, or {} if nothing's been stored
    yet - callers never need to special-case "first run", they just get an
    empty dict to read defaults out of."""
    row = db.get(AutomationState, key)
    return dict(row.value) if row else {}


def set_state(db: Session, key: str, value: dict) -> None:
    """Replaces the stored value for `key` outright (not a merge) - callers
    that want to keep existing fields should read first via get_state()
    and pass the merged dict back in. Caller is responsible for committing
    (this only stages the write), so a scan can batch several keys into one
    transaction.

    A real INSERT ... ON CONFLICT DO UPDATE, not a check-then-branch on
    db.get() - the latter raced in production: the scheduled cron tick and
    a manual "Run now" click overlapped, both sessions saw no existing row
    for the same mailbox's cursor key (neither had committed yet), both
    tried to insert, and the second one hit a UniqueViolation on
    automation_state_pkey. An upsert is correct under that race regardless
    of timing - only one write ever "wins" the row, atomically, with no
    window where two sessions can both see "not found"."""
    stmt = pg_insert(AutomationState).values(key=key, value=value)
    stmt = stmt.on_conflict_do_update(index_elements=["key"], set_={"value": value})
    db.execute(stmt)


def get_cursor(db: Session, key: str) -> datetime | None:
    """Convenience for the common case: a single ISO-8601 timestamp stored
    under value["last_processed_at"]."""
    raw = get_state(db, key).get("last_processed_at")
    if not raw:
        return None
    return datetime.fromisoformat(raw)


def set_cursor(db: Session, key: str, when: datetime) -> None:
    set_state(db, key, {"last_processed_at": when.isoformat()})
