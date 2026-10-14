"""The examples library (app/proposals/examples.py): links to past pages and resources that anyone can drop
into a proposal. Shared by everyone on a brand."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.api.routes.messaging import current_user
from app.models import ProposalExample, User
from app.proposals import examples as ex
from app.sales.brands import BRANDS, get_brand

router = APIRouter(prefix="/proposal-examples", tags=["proposals"])


def _out(r: ProposalExample) -> dict:
    return {"id": str(r.id), "brand": r.brand, "kind": r.kind, "label": r.label, "url": r.url, "format": r.format, "sector": r.sector,
            "client": r.client, "notes": r.notes, "archived": r.archived, "link_ok": r.link_ok,
            "checked_at": r.checked_at.isoformat() if r.checked_at else None, "use_count": r.use_count}


@router.get("")
def list_examples(brand: str = "tbtm", include_archived: bool = False, db: Session = Depends(get_db),
                  user: User = Depends(current_user)) -> dict:
    if not get_brand(brand):
        raise HTTPException(404, "Unknown brand")
    if ex.ensure_seed(db, brand):
        db.commit()
    q = select(ProposalExample).where(ProposalExample.brand == brand)
    if not include_archived:
        q = q.where(ProposalExample.archived.is_(False))
    rows = list(db.scalars(q.order_by(ProposalExample.kind.desc(), ProposalExample.sort_order, ProposalExample.label)))
    return {"items": [_out(r) for r in rows], "sectors": ex.SECTORS,
            "formats": sorted({r.format for r in rows if r.format}), "brands": [{"key": b.key, "name": b.name} for b in BRANDS]}


class ExampleIn(BaseModel):
    brand: str
    kind: str = Field(default="example", pattern="^(example|resource)$")
    label: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=4, max_length=1000)
    format: str | None = Field(default=None, max_length=60)
    sector: str | None = Field(default=None, max_length=40)
    client: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=300)
    archived: bool = False


def _apply(r: ProposalExample, p: ExampleIn) -> None:
    if not get_brand(p.brand):
        raise HTTPException(422, "Unknown brand")
    url = ex.clean_url(p.url)
    if not url.startswith(("http://", "https://", "mailto:")):
        raise HTTPException(422, "The link needs to start with https://")
    if p.sector and p.sector not in ex.SECTORS:
        raise HTTPException(422, "Unknown sector")
    if url != r.url:
        r.link_ok, r.checked_at = None, None
    r.brand, r.kind, r.label, r.url = p.brand, p.kind, p.label.strip(), url
    r.format, r.sector = (p.format or "").strip() or None, p.sector or None
    r.client, r.notes, r.archived = (p.client or "").strip() or None, (p.notes or "").strip() or None, p.archived
    r.updated_at = datetime.now(timezone.utc)


@router.post("", status_code=201)
def create_example(p: ExampleIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    r = ProposalExample(id=uuid.uuid4(), sort_order=1000, use_count=0)
    _apply(r, p)
    db.add(r)
    db.commit()
    return _out(r)


@router.put("/{eid}")
def update_example(eid: uuid.UUID, p: ExampleIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    r = db.get(ProposalExample, eid)
    if not r:
        raise HTTPException(404, "That example no longer exists.")
    _apply(r, p)
    db.commit()
    return _out(r)


def _check_all(brand: str) -> None:
    db = SessionLocal()
    try:
        rows = list(db.scalars(select(ProposalExample).where(ProposalExample.brand == brand, ProposalExample.archived.is_(False))))
        ex.check_links(db, rows)
        db.commit()
    finally:
        db.close()


@router.post("/check")
def check(background: BackgroundTasks, brand: str = "tbtm", user: User = Depends(current_user)) -> dict:
    """Checks every link of the brand (takes a minute; the list shows the results when it's done)."""
    if not get_brand(brand):
        raise HTTPException(404, "Unknown brand")
    background.add_task(_check_all, brand)
    return {"ok": True}
