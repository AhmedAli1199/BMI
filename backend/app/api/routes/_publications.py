"""Shared by contacts.py and companies.py's create endpoints - resolves
and validates the source_db a new record should be filed under."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import MANUAL_SOURCE_DB
from app.models import Publication


def resolve_source_db(db: Session, source_db: str | None) -> str:
    if not source_db:
        return MANUAL_SOURCE_DB
    if source_db == MANUAL_SOURCE_DB:
        return MANUAL_SOURCE_DB
    if not db.scalar(select(Publication).where(Publication.slug == source_db)):
        raise HTTPException(status_code=400, detail=f"Unknown database: {source_db!r}")
    return source_db
