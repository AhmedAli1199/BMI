"""Shared CRUD helpers for the polymorphic contact-or-company channel
tables (Address/Phone/Email) - see contact_channel.py's docstring. Used by
both contacts.py and companies.py so "add an email to a contact" and "add
an email to a company" don't duplicate the same six near-identical
endpoints twice. Manually-created/edited channel rows get source_db
MANUAL_SOURCE_DB, same provenance rule as every other manual CRM write.
"""
from __future__ import annotations

import uuid
from typing import TypeVar

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.schemas import MANUAL_SOURCE_DB

ModelT = TypeVar("ModelT")


def create_channel(db: Session, model: type[ModelT], owner_field: str, owner_id: uuid.UUID, payload: BaseModel) -> ModelT:
    row = model(
        id=uuid.uuid4(),
        source_db=MANUAL_SOURCE_DB,
        source_act_id=str(uuid.uuid4()),
        is_primary=False,
        **{owner_field: owner_id},
        **payload.model_dump(exclude_unset=True),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_channel(
    db: Session, model: type[ModelT], owner_field: str, owner_id: uuid.UUID, channel_id: uuid.UUID, payload: BaseModel
) -> ModelT:
    row = db.get(model, channel_id)
    if not row or getattr(row, owner_field) != owner_id:
        raise HTTPException(status_code=404, detail="Not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete_channel(db: Session, model: type[ModelT], owner_field: str, owner_id: uuid.UUID, channel_id: uuid.UUID) -> None:
    row = db.get(model, channel_id)
    if not row or getattr(row, owner_field) != owner_id:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(row)
    db.commit()


def delete_entity_row(db: Session, model: type[ModelT], entity_type: str, entity_id: uuid.UUID, row_id: uuid.UUID) -> None:
    """Same idea as delete_channel, for the polymorphic (entity_type,
    entity_id) ownership shape Note and HistoryEntry use instead of a
    simple contact_id/company_id FK (see note.py/history.py's docstrings
    on why they're flattened this way). A hard delete, not a soft/
    tombstone one - matches how every other CRM record in this app is
    removed (see delete_channel above, delete_contact/delete_company) -
    there's no separate "restore" flow anywhere else either, so adding
    one just for notes/history would be an inconsistent one-off. The
    frontend's own confirm-before-delete dialog is the safety net."""
    row = db.get(model, row_id)
    if not row or row.entity_type != entity_type or row.entity_id != entity_id:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(row)
    db.commit()
