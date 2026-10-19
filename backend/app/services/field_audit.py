"""Writes the per-user audit trail for direct Contact/Company field edits.
See app/models/field_change.py for the full design note.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, FieldChange

# Fields that hold a company's id - the history shows the company's name instead.
COMPANY_ID_FIELDS = {"company_id", "parent_company_id"}


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
    caller applies `updates` to it.

    changed_at is set here in Python rather than left to the column's
    server_default=func.now() - Postgres' now() returns the same value
    for every statement in one transaction, so two edits that land in the
    same transaction (a test's SAVEPOINT-wrapped isolation, or any future
    caller that batches several PATCHes in one db session before
    committing) would tie exactly, leaving "newest first" ordering
    undefined between them. A small increasing offset per row in this
    same call also guarantees a strict order between several fields
    changed in one PATCH, not just across separate calls."""
    now = datetime.now(timezone.utc)
    for i, (field, new_value) in enumerate(updates.items()):
        old_value = before.get(field)
        if old_value == new_value:
            continue
        db.add(FieldChange(
            id=uuid.uuid4(), entity_type=entity_type, entity_id=entity_id,
            field=field, old_value=_stringify(old_value), new_value=_stringify(new_value),
            changed_by_user_id=changed_by_user_id,
            changed_at=now + timedelta(microseconds=i),
        ))


def company_names_for(db: Session, rows: list[FieldChange]) -> dict[str, str]:
    """{company id as stored in the history: company name} for every company
    a set of history rows mentions, so the history reads "Acme Ltd", not an id.
    Resolved when the history is read, so older rows read properly too."""
    ids: set[uuid.UUID] = set()
    for r in rows:
        if r.field not in COMPANY_ID_FIELDS:
            continue
        for v in (r.old_value, r.new_value):
            if not v:
                continue
            try:
                ids.add(uuid.UUID(v))
            except ValueError:
                pass
    if not ids:
        return {}
    return {str(c.id): c.name for c in db.scalars(select(Company).where(Company.id.in_(ids)))}


def readable_value(field: str, value: str | None, company_names: dict[str, str]) -> str | None:
    if value is None or field not in COMPANY_ID_FIELDS:
        return value
    return company_names.get(value, "A company that has since been deleted")


# ---- phones, emails and addresses -------------------------------------------------

CHANNEL_FIELDS = {"Phone": "phone", "Email": "email", "Address": "address"}


def describe_channel(row: object) -> str | None:
    """One plain line for a phone, email or address, as the history shows it
    ("Mobile: 07700 900842")."""
    kind = type(row).__name__
    if kind == "Phone":
        text = " ".join(filter(None, [getattr(row, "number", None), f"ext. {row.extension}" if getattr(row, "extension", None) else None]))
    elif kind == "Email":
        text = getattr(row, "address", None) or ""
    else:
        parts = [getattr(row, f, None) for f in ("line1", "line2", "line3", "city", "state", "postal_code", "country")]
        text = ", ".join(p.strip() for p in parts if p and p.strip())
    text = (text or "").strip()
    if not text:
        return None
    label = (getattr(row, "type_label", None) or "").strip()
    return f"{label}: {text}" if label else text


def record_channel_change(
    db: Session, *, owner_field: str, owner_id: uuid.UUID, row: object,
    before: str | None, after: str | None, changed_by_user_id: uuid.UUID | None,
) -> None:
    """Adds a phone/email/address add, edit or removal to the owner's change
    history (the contact's or the company's). Does nothing when nothing changed."""
    field = CHANNEL_FIELDS.get(type(row).__name__)
    entity_type = {"contact_id": "contact", "company_id": "company"}.get(owner_field)
    if not field or not entity_type or before == after:
        return
    record_field_changes(
        db, entity_type=entity_type, entity_id=owner_id, before={field: before}, updates={field: after},
        changed_by_user_id=changed_by_user_id,
    )
