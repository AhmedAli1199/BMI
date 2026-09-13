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
