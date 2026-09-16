"""Batch-resolve created_by_user_id -> UserSummary for Note/History/Activity
rows, shared by contacts.py, companies.py and activities.py so each doesn't
reimplement the same N+1-avoiding lookup.
"""
from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import UserSummary
from app.models import User


class _HasCreator(Protocol):
    created_by_user_id: uuid.UUID | None


def resolve_creators(db: Session, rows: list[_HasCreator]) -> dict[uuid.UUID, User]:
    ids = {r.created_by_user_id for r in rows if r.created_by_user_id}
    if not ids:
        return {}
    return {u.id: u for u in db.scalars(select(User).where(User.id.in_(ids)))}


def creator_summary(row: _HasCreator, creators: dict[uuid.UUID, User]) -> UserSummary | None:
    if not row.created_by_user_id:
        return None
    user = creators.get(row.created_by_user_id)
    return UserSummary.model_validate(user) if user else None
