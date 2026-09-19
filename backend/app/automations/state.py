"""Thin read/replace wrapper around AutomationState (see
app/models/automation_state.py) - the only two operations a producer job
actually needs from a cross-run cursor. Kept separate from the jobs that use
it so any future scan can reuse the same store without importing
mail-specific code.
"""
from __future__ import annotations

from datetime import datetime

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
    transaction."""
    row = db.get(AutomationState, key)
    if row:
        row.value = value
    else:
        db.add(AutomationState(key=key, value=value))


def get_cursor(db: Session, key: str) -> datetime | None:
    """Convenience for the common case: a single ISO-8601 timestamp stored
    under value["last_processed_at"]."""
    raw = get_state(db, key).get("last_processed_at")
    if not raw:
        return None
    return datetime.fromisoformat(raw)


def set_cursor(db: Session, key: str, when: datetime) -> None:
    set_state(db, key, {"last_processed_at": when.isoformat()})
