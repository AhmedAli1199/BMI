"""Online booking forms (Jotform, Stova): set up in Bookings settings, entries received at a public address.
See app/automations/booking_forms.py."""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automations import booking_forms as bf
from app.core.config import settings
from app.core.identity import Identity, get_identity
from app.db.session import get_db
from app.models import BookingForm, SalesEdition, SalesRate, SalesRep, SalesTitle
from app.roles import CAN_USE_AUTOMATIONS

router = APIRouter(prefix="/sales/booking-forms", tags=["orders"])


def _need_staff(identity: Identity) -> None:
    if identity.is_known and identity.role not in CAN_USE_AUTOMATIONS:
        raise HTTPException(403, "Only administrators and data managers can set up booking forms.")


def _out(db: Session, f: BookingForm) -> dict:
    return {"id": str(f.id), "name": f.name, "source": f.source, "active": f.active,
            "title_id": str(f.title_id) if f.title_id else None, "edition_id": str(f.edition_id) if f.edition_id else None,
            "rate_id": str(f.rate_id) if f.rate_id else None, "rep_id": str(f.rep_id) if f.rep_id else None,
            "description": f.description, "unit_price": float(f.unit_price) if f.unit_price is not None else None,
            "becomes": bf._what(db, f), "received": f.received or 0,
            "last_received_at": f.last_received_at.isoformat() if f.last_received_at else None,
            "address": f"{settings.app_base_url.rstrip('/')}/api/booking-forms/{f.token}"}


class FormIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source: str = Field(default="jotform", pattern="^(jotform|stova|other)$")
    title_id: uuid.UUID | None = None
    edition_id: uuid.UUID | None = None
    rate_id: uuid.UUID | None = None
    rep_id: uuid.UUID | None = None
    description: str = Field(default="", max_length=300)
    unit_price: float | None = Field(default=None, ge=0, le=10_000_000)
    active: bool = True


def _apply(db: Session, f: BookingForm, p: FormIn) -> None:
    ed = db.get(SalesEdition, p.edition_id) if p.edition_id else None
    if p.edition_id and not ed:
        raise HTTPException(422, "That issue or event no longer exists.")
    if p.title_id and not db.get(SalesTitle, p.title_id):
        raise HTTPException(422, "That title no longer exists.")
    if not (p.title_id or ed):
        raise HTTPException(422, "Choose the title (and the issue or event, if you know it).")
    if p.rate_id and not db.get(SalesRate, p.rate_id):
        raise HTTPException(422, "That rate card product no longer exists.")
    if p.rep_id and not db.get(SalesRep, p.rep_id):
        raise HTTPException(422, "Unknown salesperson")
    f.name, f.source, f.description, f.active = p.name.strip(), p.source, p.description.strip(), p.active
    f.title_id = ed.title_id if ed else p.title_id
    f.edition_id, f.rate_id, f.rep_id, f.unit_price = p.edition_id, p.rate_id, p.rep_id, p.unit_price
    f.updated_at = datetime.now(timezone.utc)


@router.get("")
def list_forms(db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> list[dict]:
    _need_staff(identity)
    return [_out(db, f) for f in db.scalars(select(BookingForm).order_by(BookingForm.name))]


@router.post("", status_code=201)
def create_form(p: FormIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    _need_staff(identity)
    f = BookingForm(id=uuid.uuid4(), token=secrets.token_urlsafe(24), received=0)
    _apply(db, f, p)
    db.add(f)
    db.commit()
    return _out(db, f)


@router.put("/{form_id}")
def update_form(form_id: uuid.UUID, p: FormIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    _need_staff(identity)
    f = db.get(BookingForm, form_id)
    if not f:
        raise HTTPException(404, "That booking form no longer exists.")
    _apply(db, f, p)
    db.commit()
    return _out(db, f)


@router.delete("/{form_id}", status_code=204, response_model=None)
def delete_form(form_id: uuid.UUID, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> None:
    _need_staff(identity)
    f = db.get(BookingForm, form_id)
    if f:
        db.delete(f)
        db.commit()


@router.post("/receive/{token}")
async def receive(token: str, request: Request, db: Session = Depends(get_db)) -> dict:
    """An entry from the form itself (forwarded by the frontend's public /api/booking-forms/{token})."""
    f = db.scalars(select(BookingForm).where(BookingForm.token == token)).first()
    if not f or not f.active:
        raise HTTPException(404, "Not found.")
    ctype = request.headers.get("content-type", "")
    if "multipart/form-data" in ctype or "application/x-www-form-urlencoded" in ctype:
        form = await request.form()
        ref, answers = bf.parse(ctype, b"", {k: v for k, v in form.items() if isinstance(v, str)})
    else:
        ref, answers = bf.parse(ctype, await request.body())
    if not answers:
        raise HTTPException(422, "The entry had no answers in it.")
    item = bf.receive(db, f, ref, answers)
    db.commit()
    return {"ok": True, "queued": bool(item)}
