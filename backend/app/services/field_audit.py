"""Writes the per-user audit trail for direct Contact/Company field edits.
See app/models/field_change.py for the full design note.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models import FieldChange


def _stringify(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def record_field_changes(
    db: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    before: dict[str, object],
    updates: dict[str, object],
    changed_by_user_id: uuid.UUID | None,
) -> None:
    """One FieldChange row per field whose value actually changed - a
    field present in `updates` with the same value it already had (a
    no-op PATCH, or a form re-submitting an unedited field) writes
    nothing. `before` must have been captured from the row BEFORE the
    caller applies `updates` to it."""
    for field, new_value in updates.items():
        old_value = before.get(field)
        if old_value == new_value:
            continue
        db.add(FieldChange(
            id=uuid.uuid4(), entity_type=entity_type, entity_id=entity_id,
            field=field, old_value=_stringify(old_value), new_value=_stringify(new_value),
            changed_by_user_id=changed_by_user_id,
        ))
