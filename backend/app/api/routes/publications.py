from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import PUBLICATION_SLUG_PATTERN, PublicationCreate, PublicationOut
from app.db.session import get_db
from app.models import Publication

router = APIRouter(prefix="/publications", tags=["publications"])

_SLUG_RE = re.compile(PUBLICATION_SLUG_PATTERN)


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug[:64] or "db"


@router.get("", response_model=list[PublicationOut])
def list_publications(db: Session = Depends(get_db)) -> list[PublicationOut]:
    """Every registered "database" (really: source_db label) - the
    publication switcher, quick filters, dashboard tiles, and the contact/
    company creation forms all render entirely from this list, so adding
    one here is enough for it to show up everywhere without a frontend
    change or redeploy."""
    rows = db.execute(select(Publication).order_by(Publication.created_at.asc())).scalars().all()
    return [PublicationOut.model_validate(p) for p in rows]


@router.post("", response_model=PublicationOut, status_code=201)
def create_publication(payload: PublicationCreate, db: Session = Depends(get_db)) -> PublicationOut:
    slug = payload.slug.strip().lower() if payload.slug else _slugify(payload.name)
    if not _SLUG_RE.match(slug):
        raise HTTPException(
            status_code=400,
            detail="Slug must be lowercase letters/digits/hyphens, 3-64 characters, and not start/end with a hyphen.",
        )
    if slug == "manual":
        raise HTTPException(status_code=400, detail='"manual" is reserved for contacts/companies added without a publication.')
    if db.scalar(select(Publication).where(Publication.slug == slug)):
        raise HTTPException(status_code=409, detail=f"A database with slug {slug!r} already exists.")

    publication = Publication(
        id=uuid.uuid4(),
        slug=slug,
        name=payload.name.strip(),
        description=payload.description,
        color=payload.color,
        icon=payload.icon,
    )
    db.add(publication)
    db.commit()
    db.refresh(publication)
    return PublicationOut.model_validate(publication)
