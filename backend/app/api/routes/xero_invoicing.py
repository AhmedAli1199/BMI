"""Draft invoices in Xero from bookings (app/services/xero_invoices.py): accounts only."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.identity import Identity, get_identity
from app.db.session import get_db
from app.models import SalesDeal
from app.sales import accounts as acc
from app.sales import deals as dl
from app.services import xero_invoices as xi

router = APIRouter(prefix="/xero-invoicing", tags=["xero"])


def _need_accounts(db: Session, identity: Identity) -> None:
    if not acc.can_approve(db, identity.user_uuid, identity.role if identity.is_known else None):
        raise HTTPException(403, "Only accounts can make invoices (or an administrator while accounts are away).")


def _deal(db: Session, deal_id: uuid.UUID) -> SalesDeal:
    d = db.get(SalesDeal, deal_id)
    if not d:
        raise HTTPException(404, "We couldn't find that booking.")
    if d.status != "confirmed":
        raise HTTPException(409, "Only a confirmed booking can be invoiced.")
    return d


@router.get("/deals/{deal_id}")
def preview(deal_id: uuid.UUID, order_ids: list[uuid.UUID] = Query(default=[]), db: Session = Depends(get_db),
            identity: Identity = Depends(get_identity)) -> dict:
    """What the invoice would be, and anything that needs sorting first."""
    _need_accounts(db, identity)
    return xi.plan(db, _deal(db, deal_id), order_ids or None)


class LineOverride(BaseModel):
    account_code: str | None = Field(default=None, max_length=20)
    item_code: str | None = Field(default=None, max_length=40)
    unit_amount: float | None = Field(default=None, ge=0, le=10_000_000)
    description: str | None = Field(default=None, max_length=4000)
    tracking: list[dict] | None = None


class CreateIn(BaseModel):
    order_ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)
    contact_id: str | None = Field(default=None, max_length=64)
    contact_name: str | None = Field(default=None, max_length=255)
    reference: str | None = Field(default=None, max_length=255)
    currency: str | None = Field(default=None, pattern="^[A-Z]{3}$")
    lines: dict[str, LineOverride] = Field(default_factory=dict)
    remember_codes: bool = True


@router.post("/deals/{deal_id}")
def create(deal_id: uuid.UUID, p: CreateIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    """One click: make the draft invoice in Xero. Problems come back as {ok: false, problems, draft} to fix in the dialog."""
    _need_accounts(db, identity)
    d = _deal(db, deal_id)
    overrides = {"contact_id": p.contact_id, "contact_name": p.contact_name, "reference": p.reference, "currency": p.currency,
                 "lines": {k: v.model_dump(exclude_none=True) for k, v in p.lines.items()}, "remember_codes": p.remember_codes}
    result = xi.create(db, d, p.order_ids or None, overrides, identity.user_uuid)
    db.commit()
    return result


@router.get("/contacts")
def contacts(q: str = "", db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> list[dict]:
    _need_accounts(db, identity)
    try:
        return xi.search_contacts(db, q)
    except xi.XeroUnavailable as exc:
        raise HTTPException(409, str(exc)) from None


@router.get("/reference")
def reference(fresh: bool = False, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    """Xero's account codes, items, tracking categories and currencies - for the pickers."""
    _need_accounts(db, identity)
    try:
        return xi.reference_data(db, fresh)
    except xi.XeroUnavailable as exc:
        raise HTTPException(409, str(exc)) from None


class CodesIn(BaseModel):
    default: dict = Field(default_factory=dict)
    titles: dict[str, dict] = Field(default_factory=dict)


def _clean_codes(c: dict) -> dict:
    out = {}
    for k in ("account_code", "item_code"):
        if isinstance(c.get(k), str) and c[k].strip():
            out[k] = c[k].strip()[:40]
    tr = [{"name": str(x.get("name"))[:100], "option": str(x.get("option"))[:100]} for x in c.get("tracking") or []
          if isinstance(x, dict) and x.get("name") and x.get("option")]
    if tr:
        out["tracking"] = tr[:2]   # Xero allows two tracking categories
    return out


@router.get("/codes")
def get_codes(db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    _need_accounts(db, identity)
    st = dl.settings(db)
    codes = st.xero_codes or {}
    return {"default": codes.get("default") or {}, "titles": codes.get("titles") or {}}


@router.put("/codes")
def save_codes(p: CodesIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    _need_accounts(db, identity)
    st = dl.settings(db)
    st.xero_codes = {"default": _clean_codes(p.default), "titles": {k: v for k, v in ((k, _clean_codes(v)) for k, v in p.titles.items()) if v}}
    db.commit()
    return get_codes(db, identity)
