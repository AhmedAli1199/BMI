"""Orders with several items, and their order confirmations (app/models/deal.py, app/sales/deals.py).

Everyone can see orders (like bookings). The salesperson on an order (or in its split), whoever
created it, and administrators / data managers can change it. Nothing is sent to a client
unless the salesperson presses Send.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.schemas import MANUAL_SOURCE_DB
from app.core.identity import Identity, get_identity
from app.db.session import get_db
from app.models import (Address, Company, Contact, Email, Note, SalesDeal, SalesEdition, SalesOrder, SalesRate,
                        SalesRep, SalesTitle, User)
from app.models.deal import DEAL_STATUSES
from app.models.messaging import MailAccount
from app.models.proposal import Proposal
from app.roles import CAN_USE_AUTOMATIONS
from app.sales import deals as dl

router = APIRouter(prefix="/sales/deals", tags=["orders"])


# ---- input ------------------------------------------------------------------------------------

class PlacementIn(BaseModel):
    order_id: uuid.UUID | None = None
    edition_id: uuid.UUID | None = None
    item_date: date | None = None
    copy_due: date | None = None
    note: str | None = Field(default=None, max_length=300)
    booked_on: date | None = None


class LineIn(BaseModel):
    key: str | None = Field(default=None, max_length=40)
    title_id: uuid.UUID | None = None
    rate_id: uuid.UUID | None = None
    description: str = Field(default="", max_length=300)
    detail: str | None = Field(default=None, max_length=1000)    # extra wording under the line on the confirmation
    size: str | None = Field(default=None, max_length=120)       # the order register's shorthand ("FP", "DPS")
    qty: int = Field(default=1, ge=1, le=999)
    unit_price: float | None = Field(default=None, ge=0, le=10_000_000)
    list_price: float | None = Field(default=None, ge=0, le=10_000_000)
    discount_pct: float = Field(default=0, ge=0, le=1)
    added_value: bool = False
    share_gbp: float | None = Field(default=None, ge=0)          # package split "manual": this line's share
    placements: list[PlacementIn] = Field(default_factory=list, max_length=60)


class SplitIn(BaseModel):
    rep_id: uuid.UUID
    pct: float = Field(gt=0, le=1)


class DealIn(BaseModel):
    company_id: uuid.UUID | None = None
    client_name: str = Field(default="", max_length=256)
    contact_id: uuid.UUID | None = None
    contact_name: str | None = Field(default=None, max_length=200)
    contact_email: str | None = Field(default=None, max_length=320)
    confirmation_address: str | None = Field(default=None, max_length=1000)
    invoice_to: str | None = Field(default=None, max_length=1000)
    invoice_email: str | None = Field(default=None, max_length=320)
    po_number: str | None = Field(default=None, max_length=80)
    agency_name: str | None = Field(default=None, max_length=200)
    agency_pct: float = Field(default=0, ge=0, le=1)
    rep_id: uuid.UUID | None = None
    split: list[SplitIn] = Field(default_factory=list, max_length=6)
    booked_on: date | None = None
    title_id: uuid.UUID | None = None
    publication_label: str | None = Field(default=None, max_length=200)
    insertions_label: str | None = Field(default=None, max_length=300)
    document: str = Field(default="confirmation", pattern="^(confirmation|schedule)$")
    pricing: str = Field(default="items", pattern="^(items|package)$")
    package_price_gbp: float | None = Field(default=None, ge=0, le=10_000_000)
    package_label: str | None = Field(default=None, max_length=200)
    package_split: str = Field(default="rate_card", pattern="^(rate_card|even|manual)$")
    discount_pct: float = Field(default=0, ge=0, le=1)
    lines: list[LineIn] = Field(default_factory=list, max_length=60)
    invoice_plan: str = Field(default="on_publication", pattern="^(upfront|on_publication|custom)$")
    special_instructions: str | None = Field(default=None, max_length=3000)
    copy_instructions: str | None = Field(default=None, max_length=3000)
    production_contact: str | None = Field(default=None, max_length=200)
    show_artwork_specs: bool = True
    notes: str | None = Field(default=None, max_length=3000)
    proposal_id: uuid.UUID | None = None
    status: str = Field(default="pencilled", pattern="^(pencilled|confirmed)$")  # only used when creating


FIELDS = ("company_id", "client_name", "contact_id", "contact_name", "contact_email", "confirmation_address", "invoice_to",
          "invoice_email", "po_number", "agency_name", "agency_pct", "rep_id", "title_id", "publication_label", "insertions_label",
          "document", "pricing", "package_price_gbp", "package_label", "package_split", "discount_pct", "invoice_plan",
          "special_instructions", "copy_instructions", "production_contact", "show_artwork_specs", "notes")


# ---- access ------------------------------------------------------------------------------------

def _staff(identity: Identity) -> bool:
    return not identity.is_known or identity.role in CAN_USE_AUTOMATIONS


def _my_rep(db: Session, identity: Identity) -> SalesRep | None:
    return db.scalars(select(SalesRep).where(SalesRep.user_id == identity.user_uuid)).first() if identity.user_uuid else None


def _can_edit(db: Session, identity: Identity, d: SalesDeal) -> bool:
    if _staff(identity) or (identity.user_uuid and d.created_by_user_id == identity.user_uuid):
        return True
    me = _my_rep(db, identity)
    return bool(me and (d.rep_id == me.id or any(str(s.get("rep_id")) == str(me.id) for s in d.split or [])))


def _get(db: Session, deal_id: uuid.UUID) -> SalesDeal:
    d = db.get(SalesDeal, deal_id)
    if not d:
        raise HTTPException(404, "Order not found")
    return d


def _need_edit(db: Session, identity: Identity, d: SalesDeal) -> None:
    if not _can_edit(db, identity, d):
        raise HTTPException(403, "Only the salesperson on this order or a manager can change it.")


# ---- shaping -------------------------------------------------------------------------------------

def _clean(v):
    return v.strip() or None if isinstance(v, str) else v


def _apply(db: Session, d: SalesDeal, p: DealIn) -> None:
    if p.company_id and not db.get(Company, p.company_id):
        raise HTTPException(422, "That company isn't in the CRM any more.")
    if p.rep_id and not db.get(SalesRep, p.rep_id):
        raise HTTPException(422, "Unknown salesperson")
    for s in p.split:
        if not db.get(SalesRep, s.rep_id):
            raise HTTPException(422, "Unknown salesperson in the split")
    if p.split and abs(sum(s.pct for s in p.split) - 1) > 0.001:
        raise HTTPException(422, "The split between salespeople needs to add up to 100%.")
    for k in FIELDS:
        setattr(d, k, _clean(getattr(p, k)))
    if not d.client_name:
        company = db.get(Company, p.company_id) if p.company_id else None
        if not company:
            raise HTTPException(422, "Choose the client.")
        d.client_name = company.name
    d.split = [{"rep_id": str(s.rep_id), "pct": s.pct} for s in p.split]
    d.booked_on = p.booked_on or d.booked_on or date.today()
    if not p.lines:
        raise HTTPException(422, "Add at least one item to the order.")


def _lines_in(p: DealIn) -> list[dict]:
    out = []
    for ln in p.lines:
        d = ln.model_dump(mode="json")
        d["key"] = d.get("key") or uuid.uuid4().hex[:12]
        d["placements"] = [{k: v for k, v in pl.items() if v is not None} for pl in d["placements"]]
        out.append(d)
    return out


def _price_or_422(d: SalesDeal, lines: list[dict]) -> dl.Priced:
    try:
        return dl.price_deal(d, lines)
    except dl.OrderError as exc:
        raise HTTPException(422, str(exc)) from exc


def _labels(db: Session) -> tuple[dict, dict]:
    from app.api.routes.sales import edition_label
    titles = {t.id: t for t in db.scalars(select(SalesTitle))}
    return titles, edition_label


def _out(db: Session, d: SalesDeal, identity: Identity) -> dict:
    from app.sales.order_query import xero_state
    titles, edition_label = _labels(db)
    pr = dl.price_deal(d)
    items = db.scalars(select(SalesOrder).where(SalesOrder.deal_id == d.id)).all()
    states = dict(db.execute(select(SalesOrder.id, xero_state()).where(SalesOrder.deal_id == d.id)).all()) if items else {}
    by_id = {str(o.id): o for o in items}
    eds = {e.id: e for e in db.scalars(select(SalesEdition).where(SalesEdition.id.in_({o.edition_id for o in items})))} if items else {}
    today = date.today()
    schedule, warnings = [], list(pr.warnings)
    for ln in pr.lines:
        for pl in ln["placements"]:
            o = by_id.get(str(pl.get("order_id")))
            ed = eds.get(o.edition_id) if o else None
            t = titles.get(ed.title_id) if ed else None
            runs = (o.item_date if o and o.item_date else (ed.edition_date if ed else None))
            row = {
                "order_id": str(o.id) if o else None, "line": ln["key"], "description": ln.get("description") or ln.get("size") or "",
                "edition_id": str(ed.id) if ed else None, "edition": edition_label(t, ed) if ed and t else None,
                "title": t.name if t else None, "runs_on": runs.isoformat() if runs else None,
                "ad_deadline": ed.ad_deadline.isoformat() if ed and ed.ad_deadline else None,
                "copy_due": (o.copy_due or (ed.copy_deadline if ed else None)).isoformat() if o and (o.copy_due or (ed and ed.copy_deadline)) else None,
                "value_gbp": pl["value_gbp"], "agency_gbp": pl["agency_gbp"], "added_value": bool(ln.get("added_value")),
                "status": o.status if o else None, "invoice_number": o.invoice_number if o else None,
                "xero_state": states.get(o.id) if o else None, "booked_on": o.booked_on.isoformat() if o and o.booked_on else None,
                "published": bool(runs and runs <= today),
            }
            row["ready_to_invoice"] = bool(o and o.status == "booked" and not o.invoice_number and pl["value_gbp"] > 0
                                           and (d.invoice_plan == "upfront" or row["published"]))
            if o and ed and d.status != "cancelled" and o.status != "cancelled":
                if ed.ad_deadline and ed.ad_deadline < today and not row["published"] and o.created_at and o.created_at.date() > ed.ad_deadline:
                    warnings.append(f"{row['edition']}: booked after its advertising deadline ({ed.ad_deadline:%-d %b}). Check production can still fit it in.")
                if ed.status == "closed":
                    warnings.append(f"{row['edition']} is marked closed.")
            schedule.append(row)
    schedule.sort(key=lambda r: (r["runs_on"] or "9999", r["description"]))
    reps = {r.id: r for r in db.scalars(select(SalesRep))}
    rep = reps.get(d.rep_id)
    invoiced = sum(r["value_gbp"] for r in schedule if r["invoice_number"])
    return {
        "id": str(d.id), "number": d.number, "status": d.status, "document": d.document,
        **{k: (getattr(d, k) if not isinstance(getattr(d, k), (uuid.UUID,)) else str(getattr(d, k))) for k in FIELDS},
        "agency_pct": float(d.agency_pct or 0), "discount_pct": float(d.discount_pct or 0),
        "package_price_gbp": float(d.package_price_gbp) if d.package_price_gbp is not None else None,
        "split": d.split or [], "booked_on": d.booked_on.isoformat(), "lines": pr.lines,
        "rep": {"id": str(rep.id), "code": rep.code, "name": rep.name} if rep else None,
        "split_names": [{"rep_id": s["rep_id"], "name": reps[uuid.UUID(s["rep_id"])].name, "pct": s["pct"]} for s in d.split or [] if uuid.UUID(s["rep_id"]) in reps],
        "totals": {"gross_gbp": pr.gross_gbp, "discount_gbp": pr.discount_gbp, "total_gbp": pr.total_gbp, "agency_gbp": pr.agency_gbp,
                   "payable_gbp": pr.payable_gbp, "rate_card_gbp": pr.rate_card_gbp, "added_value_gbp": pr.added_value_gbp,
                   "off_rate_card_pct": pr.off_rate_card_pct, "invoiced_gbp": round(invoiced, 2),
                   "to_invoice_gbp": round(sum(r["value_gbp"] for r in schedule if r["ready_to_invoice"]), 2)},
        "schedule": schedule, "warnings": list(dict.fromkeys(warnings)),
        "insertions": dl.insertions_text(db, d),
        "proposal_id": str(d.proposal_id) if d.proposal_id else None, "rebooked_from_id": str(d.rebooked_from_id) if d.rebooked_from_id else None,
        "rebooked_from_number": db.get(SalesDeal, d.rebooked_from_id).number if d.rebooked_from_id and db.get(SalesDeal, d.rebooked_from_id) else None,
        "confirmed_at": d.confirmed_at.isoformat() if d.confirmed_at else None, "sent_at": d.sent_at.isoformat() if d.sent_at else None,
        "sent_to": d.sent_to, "cancelled_reason": d.cancelled_reason, "created_at": d.created_at.isoformat() if d.created_at else None,
        "can_edit": _can_edit(db, identity, d),
    }


# ---- list / read -------------------------------------------------------------------------------------

@router.get("")
def list_deals(q: str | None = None, status: list[str] = Query(default=[]), rep_id: list[uuid.UUID] = Query(default=[]),
               title_id: list[uuid.UUID] = Query(default=[]), company_id: uuid.UUID | None = None, year: int | None = None,
               mine: bool = False, sort: str = "number", desc: bool = True, limit: int = Query(default=50, le=200), offset: int = 0,
               db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    stmt = select(SalesDeal)
    if q and q.strip():
        like = f"%{q.strip()}%"
        conds = [SalesDeal.client_name.ilike(like), SalesDeal.po_number.ilike(like), SalesDeal.contact_name.ilike(like), SalesDeal.agency_name.ilike(like)]
        if q.strip().isdigit():
            conds.append(SalesDeal.number == int(q.strip()))
        stmt = stmt.where(or_(*conds))
    if status:
        stmt = stmt.where(SalesDeal.status.in_([s for s in status if s in DEAL_STATUSES]))
    if mine:
        me = _my_rep(db, identity)
        stmt = stmt.where(or_(SalesDeal.rep_id == (me.id if me else None), SalesDeal.created_by_user_id == identity.user_uuid))
    if rep_id:
        stmt = stmt.where(SalesDeal.rep_id.in_(rep_id))
    if title_id:
        stmt = stmt.where(SalesDeal.id.in_(select(SalesOrder.deal_id).join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
                                           .where(SalesEdition.title_id.in_(title_id))))
    if company_id:
        stmt = stmt.where(SalesDeal.company_id == company_id)
    if year:
        stmt = stmt.where(func.extract("year", SalesDeal.booked_on) == year)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    live = stmt.where(SalesDeal.status != "cancelled").subquery()
    value = float(db.scalar(select(func.coalesce(func.sum(live.c.total_gbp), 0))) or 0) if total else 0.0
    col = {"number": SalesDeal.number, "client": func.lower(SalesDeal.client_name), "value": SalesDeal.total_gbp, "booked": SalesDeal.booked_on}.get(sort, SalesDeal.number)
    rows = db.scalars(stmt.order_by(col.desc() if desc else col.asc(), SalesDeal.number.desc()).limit(limit).offset(offset)).all()
    ids = [d.id for d in rows]
    span = {r[0]: r[1:] for r in db.execute(
        select(SalesOrder.deal_id, func.count(), func.min(func.coalesce(SalesOrder.item_date, SalesEdition.edition_date)),
               func.max(func.coalesce(SalesOrder.item_date, SalesEdition.edition_date)),
               func.coalesce(func.sum(SalesOrder.value_gbp).filter(SalesOrder.invoice_number.isnot(None)), 0))
        .join(SalesEdition, SalesOrder.edition_id == SalesEdition.id).where(SalesOrder.deal_id.in_(ids)).group_by(SalesOrder.deal_id))} if ids else {}
    reps = {r.id: r for r in db.scalars(select(SalesRep))}
    items = []
    for d in rows:
        n, first, last, invoiced = span.get(d.id, (0, None, None, 0))
        items.append({"id": str(d.id), "number": d.number, "status": d.status, "client_name": d.client_name,
                      "company_id": str(d.company_id) if d.company_id else None, "rep": reps[d.rep_id].name if d.rep_id in reps else None,
                      "booked_on": d.booked_on.isoformat(), "total_gbp": float(d.total_gbp or 0), "items": n,
                      "first": first.isoformat() if first else None, "last": last.isoformat() if last else None,
                      "invoiced_gbp": float(invoiced or 0), "sent_at": d.sent_at.isoformat() if d.sent_at else None,
                      "po_number": d.po_number, "agency_name": d.agency_name})
    return {"items": items, "total": total, "total_value_gbp": round(value, 2)}


@router.get("/prefill")
def prefill(company_id: uuid.UUID | None = None, contact_id: uuid.UUID | None = None, proposal_id: uuid.UUID | None = None,
            edition_id: uuid.UUID | None = None, option: str | None = None,
            db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    """What a new order can start from: the client's address and contact details, a proposal's products, or an issue."""
    out: dict = {"lines": [], "rep_id": None}
    me = _my_rep(db, identity)
    out["rep_id"] = str(me.id) if me else None
    p = db.get(Proposal, proposal_id) if proposal_id else None
    if p:
        company_id, contact_id = company_id or p.company_id, contact_id or p.contact_id
        out["proposal_id"] = str(p.id)
        out["title_id"] = str(p.title_id) if p.title_id else None
        from app.proposals.pricing import totals as proposal_totals
        tots = proposal_totals(p.lines or [], float(p.discount_pct or 0))
        chosen = next((t for t in tots if t["option"] == option), tots[0]) if tots else None
        out["option"] = chosen["option"] if chosen else None
        out["options"] = [t["option"] for t in tots if t["option"]]
        lines = [ln for ln in p.lines or [] if ln.get("option") in ((chosen or {}).get("option"), None)]
        has_offers = any(ln.get("source") == "offer" for ln in lines)
        for ln in lines:
            if ln.get("source") == "offer":
                continue
            rate = db.get(SalesRate, uuid.UUID(str(ln["rate_id"]))) if ln.get("rate_id") else None
            tid = ln.get("title_id") or (str(p.title_id) if p.title_id else None)
            issues = ln.get("issues") or []
            places = [{"edition_id": i} for i in issues] or [{"edition_id": str(p.edition_id)} if p.edition_id else {} for _ in range(int(ln.get("qty") or 1))]
            out["lines"].append({"title_id": tid, "rate_id": ln.get("rate_id"), "description": ln.get("product") or "", "qty": 1,
                                 "unit_price": ln.get("unit_price"), "discount_pct": float(ln.get("discount_pct") or 0),
                                 "list_price": float(rate.price_gbp) if rate and rate.price_gbp is not None else ln.get("unit_price"),
                                 "placements": places})
        if has_offers and chosen:
            # Rate-card offers were taken off the whole group: keep the agreed total exactly as a package price.
            out.update(pricing="package", package_price_gbp=chosen["total_gbp"], package_split="rate_card",
                       package_label=f"{p.campaign_name}{' - ' + chosen['option'] if chosen['option'] else ''}")
        else:
            out["discount_pct"] = float(p.discount_pct or 0)
    ed = db.get(SalesEdition, edition_id) if edition_id else None
    if ed and not out["lines"]:
        out["title_id"] = str(ed.title_id)
        out["lines"].append({"title_id": str(ed.title_id), "description": "", "qty": 1, "placements": [{"edition_id": str(ed.id)}]})
    c = db.get(Company, company_id) if company_id else None
    if c:
        out["company"] = {"id": str(c.id), "label": c.name}
        out["client_name"] = c.name
        a = db.scalars(select(Address).where(Address.company_id == c.id).order_by(Address.is_primary.desc())).first()
        if a:
            out["confirmation_address"] = "\n".join(x for x in (c.name, a.line1, a.line2, a.line3, a.city, a.state, a.postal_code, a.country) if x and x.strip())
        last = db.scalars(select(SalesDeal).where(SalesDeal.company_id == c.id).order_by(SalesDeal.number.desc())).first()
        if last:  # the same client is usually invoiced the same way
            for k in ("invoice_to", "invoice_email", "agency_name", "agency_pct", "confirmation_address"):
                if getattr(last, k) and not out.get(k):
                    out[k] = float(getattr(last, k)) if k == "agency_pct" else getattr(last, k)
            out["last_order"] = {"id": str(last.id), "number": last.number}
    ct = db.get(Contact, contact_id) if contact_id else None
    if ct:
        out["contact"] = {"id": str(ct.id), "label": ct.full_name or " ".join(x for x in (ct.first_name, ct.last_name) if x)}
        out["contact_name"] = out["contact"]["label"]
        em = db.scalars(select(Email.address).where(Email.contact_id == ct.id).order_by(Email.is_primary.desc())).first()
        out["contact_email"] = em
    return out


@router.get("/issues")
def issues(title_id: uuid.UUID, include: list[uuid.UUID] = Query(default=[]), db: Session = Depends(get_db)) -> list[dict]:
    """A title's issues, months and events from three months ago on - what an order's items can go in -
    with the booking and copy deadlines so the salesperson sees what's still open."""
    from app.sales.editorial import issue_label
    today = date.today()
    eds = list(db.scalars(select(SalesEdition).where(SalesEdition.title_id == title_id, or_(SalesEdition.edition_date.is_(None),
                                                     SalesEdition.edition_date >= today - timedelta(days=92)))
                          .order_by(SalesEdition.edition_date.nulls_last(), SalesEdition.name).limit(120)))
    have = {e.id for e in eds}
    eds += [e for e in (db.get(SalesEdition, i) for i in include if i not in have) if e]
    return [{"id": str(e.id), "label": issue_label(e), "kind": e.kind, "edition_date": e.edition_date.isoformat() if e.edition_date else None,
             "ad_deadline": e.ad_deadline.isoformat() if e.ad_deadline else None, "copy_deadline": e.copy_deadline.isoformat() if e.copy_deadline else None,
             "open": bool((e.ad_deadline or e.edition_date or today) >= today), "status": e.status} for e in eds]


@router.get("/settings")
def get_settings(db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    st = dl.settings(db)
    db.commit()
    return {"next_number": st.next_number, "company_block": st.company_block, "footer": st.footer, "terms": st.terms,
            "artwork_specs": st.artwork_specs, "can_edit": not identity.is_known or identity.role == "admin"}


class SettingsIn(BaseModel):
    next_number: int = Field(ge=1, le=10_000_000)
    company_block: str = Field(default="", max_length=2000)
    footer: str = Field(default="", max_length=2000)
    terms: str = Field(default="", max_length=3000)
    artwork_specs: str = Field(default="", max_length=5000)


@router.put("/settings")
def save_settings(p: SettingsIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    if identity.is_known and identity.role != "admin":
        raise HTTPException(403, "Only administrators can change what every confirmation says.")
    st = dl.settings(db)
    highest = db.scalar(select(func.max(SalesDeal.number))) or 0
    if p.next_number <= highest:
        raise HTTPException(422, f"Order {highest} already exists, so the next number has to be higher.")
    for k, v in p.model_dump().items():
        setattr(st, k, v)
    st.updated_at = datetime.now(timezone.utc)
    db.commit()
    return get_settings(db, identity)


class PreviewIn(BaseModel):
    pricing: str = Field(default="items", pattern="^(items|package)$")
    package_price_gbp: float | None = Field(default=None, ge=0)
    package_split: str = Field(default="rate_card", pattern="^(rate_card|even|manual)$")
    discount_pct: float = Field(default=0, ge=0, le=1)
    agency_pct: float = Field(default=0, ge=0, le=1)
    lines: list[LineIn] = Field(default_factory=list, max_length=60)


@router.post("/preview")
def preview(p: PreviewIn) -> dict:
    """Totals for the form as it's filled in - the same sums the order is saved with."""
    lines = [dict(ln.model_dump(mode="json"), placements=[pl.model_dump(mode="json") for pl in ln.placements] or [{}]) for ln in p.lines]
    try:
        pr = dl.price(lines, pricing=p.pricing, package_price=p.package_price_gbp, package_split=p.package_split,
                      discount_pct=p.discount_pct, agency_pct=p.agency_pct) if lines else dl.Priced(lines=[])
    except dl.OrderError as exc:
        return {"error": str(exc)}
    return {"lines": [{"total_gbp": ln["total_gbp"], "placements": [x["value_gbp"] for x in ln["placements"]]} for ln in pr.lines],
            "gross_gbp": pr.gross_gbp, "discount_gbp": pr.discount_gbp, "total_gbp": pr.total_gbp, "agency_gbp": pr.agency_gbp,
            "payable_gbp": pr.payable_gbp, "rate_card_gbp": pr.rate_card_gbp, "added_value_gbp": pr.added_value_gbp,
            "off_rate_card_pct": pr.off_rate_card_pct, "warnings": pr.warnings}


@router.get("/{deal_id}")
def get_deal(deal_id: uuid.UUID, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    return _out(db, _get(db, deal_id), identity)


# ---- write -------------------------------------------------------------------------------------------

def _save(db: Session, d: SalesDeal, p: DealIn, identity: Identity) -> list[str]:
    _apply(db, d, p)
    lines = _lines_in(p)
    pr = _price_or_422(d, lines)
    try:
        notes = dl.sync_items(db, d, pr, identity.user_uuid)
    except dl.OrderError as exc:
        raise HTTPException(422, str(exc)) from exc
    d.lines = [{k: v for k, v in ln.items()} for ln in pr.lines]
    d.total_gbp = pr.total_gbp
    d.updated_at = datetime.now(timezone.utc)
    return notes


@router.post("", status_code=201)
def create_deal(p: DealIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    d = SalesDeal(id=uuid.uuid4(), number=dl.next_number(db), status=p.status, created_by_user_id=identity.user_uuid, lines=[], split=[])
    if p.proposal_id and not db.get(Proposal, p.proposal_id):
        raise HTTPException(422, "That proposal no longer exists.")
    if not p.rep_id:
        me = _my_rep(db, identity)
        p.rep_id = me.id if me else None
    if p.status == "confirmed":
        d.confirmed_at = datetime.now(timezone.utc)
    _apply(db, d, p)
    db.add(d)
    notes = _save(db, d, p, identity)
    db.commit()
    return {**_out(db, d, identity), "notes": notes}


@router.put("/{deal_id}")
def update_deal(deal_id: uuid.UUID, p: DealIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    d = _get(db, deal_id)
    _need_edit(db, identity, d)
    if d.status == "cancelled":
        raise HTTPException(409, "This order is cancelled. Reopen it first to change it.")
    notes = _save(db, d, p, identity)
    db.commit()
    return {**_out(db, d, identity), "notes": notes}


class StatusIn(BaseModel):
    status: str = Field(pattern="^(pencilled|confirmed|cancelled)$")
    reason: str | None = Field(default=None, max_length=300)
    # Cancelling: keep items that have already run or been invoiced (the usual case), or cancel everything.
    keep_run: bool = True


@router.post("/{deal_id}/status")
def set_status(deal_id: uuid.UUID, p: StatusIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    d = _get(db, deal_id)
    _need_edit(db, identity, d)
    today = date.today()
    items = db.scalars(select(SalesOrder).where(SalesOrder.deal_id == d.id)).all()
    eds = {e.id: e for e in db.scalars(select(SalesEdition).where(SalesEdition.id.in_({o.edition_id for o in items})))} if items else {}
    kept = 0
    if p.status == "cancelled":
        if not (p.reason or "").strip():
            raise HTTPException(422, "Say briefly why the order is cancelled - it's kept on the bookings.")
        d.status, d.cancelled_reason = "cancelled", p.reason.strip()
        for o in items:
            ran = (o.item_date or eds[o.edition_id].edition_date or today) <= today
            if p.keep_run and (ran or o.invoice_number):
                kept += 1
                continue
            o.status, o.status_reason = "cancelled", f"Order {d.number} cancelled: {d.cancelled_reason}"
    else:
        if p.status == "confirmed" and not d.confirmed_at:
            d.confirmed_at = datetime.now(timezone.utc)
        d.status, d.cancelled_reason = p.status, None
        for o in items:
            o.status, o.status_reason = dl.ITEM_STATUS[p.status], None
    d.updated_at = datetime.now(timezone.utc)
    if p.status != "cancelled":
        # live total again (a cancelled order keeps its total for the record)
        d.total_gbp = dl.price_deal(d).total_gbp
    db.commit()
    out = _out(db, d, identity)
    out["notes"] = [f"{kept} item{'s' if kept != 1 else ''} that already ran or were invoiced stay booked."] if kept else []
    return out


@router.delete("/{deal_id}", status_code=204, response_model=None)
def delete_deal(deal_id: uuid.UUID, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> None:
    """Only a pencilled order with nothing invoiced can be deleted - anything else is cancelled, so it stays on record."""
    d = _get(db, deal_id)
    _need_edit(db, identity, d)
    items = db.scalars(select(SalesOrder).where(SalesOrder.deal_id == d.id)).all()
    if d.status != "pencilled" or any(o.invoice_number or o.xero_invoice_id for o in items):
        raise HTTPException(409, "Only a pencilled order with nothing invoiced can be deleted. Cancel it instead, so it stays on record.")
    for o in items:
        db.delete(o)
    db.delete(d)
    db.commit()


@router.post("/{deal_id}/rebook")
def rebook(deal_id: uuid.UUID, year: int | None = None, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    """Next year's order for the same client: a pencilled copy with each item moved to next year's matching issue and
    next year's rate card price. Nothing is confirmed until the salesperson confirms it."""
    src = _get(db, deal_id)
    eds = [db.get(SalesEdition, uuid.UUID(str(p["edition_id"]))) for ln in src.lines or [] for p in ln.get("placements") or [] if p.get("edition_id")]
    years = [e.year for e in eds if e]
    target = year or ((max(years) + 1) if years else date.today().year + 1)
    lines, notes = dl.rebook_lines(db, src, target)
    if any(not p.get("edition_id") for ln in lines for p in ln["placements"]):
        return {"id": None, "lines": lines, "notes": notes, "needs_issues": True, "year": target}
    d = SalesDeal(id=uuid.uuid4(), number=dl.next_number(db), status="pencilled", created_by_user_id=identity.user_uuid,
                  rebooked_from_id=src.id, lines=[], split=list(src.split or []))
    for k in FIELDS:
        setattr(d, k, getattr(src, k))
    d.booked_on, d.notes = date.today(), f"Rebooked from order {src.number}."
    d.insertions_label = None
    db.add(d)
    db.flush()
    pr = dl.price_deal(d, lines)
    dl.sync_items(db, d, pr, identity.user_uuid)
    d.lines, d.total_gbp = pr.lines, pr.total_gbp
    db.commit()
    return {**_out(db, d, identity), "notes": notes}


# ---- documents ---------------------------------------------------------------------------------------

@router.get("/{deal_id}/document")
def document(deal_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    return dl.document(db, _get(db, deal_id))


def _file_name(d: SalesDeal) -> str:
    safe = "".join(c for c in d.client_name if c.isalnum() or c in " -_").strip() or "Client"
    return f"{'Schedule of works' if d.document == 'schedule' else 'Order confirmation'} {d.number} {safe}.docx"


@router.get("/{deal_id}/document.docx")
def document_docx(deal_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    d = _get(db, deal_id)
    data = dl.build_docx(dl.document(db, d))
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="{_file_name(d)}"'})


@router.get("/{deal_id}/email-draft")
def email_draft(deal_id: uuid.UUID, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    d = _get(db, deal_id)
    user = db.get(User, identity.user_uuid) if identity.user_uuid else None
    first = (d.contact_name or "").split(" ")[0] or "there"
    kind = "schedule of works" if d.document == "schedule" else "order confirmation"
    runs = dl.insertions_text(db, d)
    body = (f"Hi {first},\n\nThank you for your booking. Please find attached the {kind} for order {d.number}"
            f"{f' ({runs})' if runs else ''}. Do check the details and let me know if anything needs changing.\n\n"
            + ("The invoice will follow.\n\n" if d.document != "schedule" else "")
            + f"Kind regards,\n{(user.name if user else '') or ''}")
    acct = db.scalar(select(MailAccount).where(MailAccount.user_id == user.id)) if user else None
    return {"to": [d.contact_email] if d.contact_email else [], "cc": [], "subject": f"{kind.capitalize()}: order {d.number}, {d.client_name}",
            "body": body, "outlook_connected": bool(acct), "outlook_email": acct.email if acct else None}


def _log_sent(db: Session, d: SalesDeal, user_id: uuid.UUID | None, via: str, to: list[str]) -> None:
    now = datetime.now(timezone.utc)
    d.sent_at, d.sent_to = now, ", ".join(to)[:400] or via
    if d.company_id:
        pr = dl.price_deal(d)
        body = (f"{'Schedule of works' if d.document == 'schedule' else 'Order confirmation'} {d.number} sent"
                f"{' to ' + ', '.join(to) if to else ''}: {dl.insertions_text(db, d) or ''}. Total £{pr.total_gbp:,.2f} before VAT"
                f"{f', less agency commission £{pr.agency_gbp:,.2f}' if pr.agency_gbp else ''}.")
        db.add(Note(id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()), entity_type="company", entity_id=d.company_id,
                    note_type="Order confirmation", body=body, act_created_at=now, created_by_user_id=user_id))


class SendIn(BaseModel):
    to: list[str] = Field(min_length=1, max_length=20)
    cc: list[str] = Field(default_factory=list, max_length=20)
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(max_length=20000)


@router.post("/{deal_id}/send")
def send(deal_id: uuid.UUID, p: SendIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    """Emails the confirmation from the salesperson's own Outlook, Word file attached, and notes it on the client."""
    from app.services import mail_merge as mm
    from app.services import outlook

    d = _get(db, deal_id)
    _need_edit(db, identity, d)
    if d.status == "cancelled":
        raise HTTPException(409, "This order is cancelled, so there's nothing to confirm.")
    acct = db.scalar(select(MailAccount).where(MailAccount.user_id == identity.user_uuid)) if identity.user_uuid else None
    if not acct:
        raise HTTPException(409, "Connect your Outlook first (Settings > Email) - confirmations are sent from your own account.")
    to, cc = [a.strip() for a in p.to if a.strip()], [a.strip() for a in p.cc if a.strip()]
    for a in [*to, *cc]:
        if "@" not in a or " " in a:
            raise HTTPException(422, f"“{a}” doesn't look like an email address.")
    data = dl.build_docx(dl.document(db, d))
    try:
        outlook.send_mail(db, acct, to=to, cc=cc, subject=p.subject, html_body=mm.to_html(p.body),
                          attachments=[(_file_name(d), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", data)])
    except outlook.OutlookAuthError:
        raise HTTPException(409, "Your Outlook connection has expired. Reconnect it in Settings > Email, then send again.")
    except outlook.RateLimited:
        raise HTTPException(429, "Outlook is asking us to slow down - try again in a minute.")
    except Exception:
        raise HTTPException(502, "Outlook didn't accept the email, so nothing was sent. Please try again.")
    if d.status == "pencilled":  # sending the confirmation confirms the order
        d.status, d.confirmed_at = "confirmed", datetime.now(timezone.utc)
        for o in db.scalars(select(SalesOrder).where(SalesOrder.deal_id == d.id)):
            o.status = "booked"
    _log_sent(db, d, identity.user_uuid, "outlook", to)
    db.commit()
    return _out(db, d, identity)


class MarkSentIn(BaseModel):
    to: str | None = Field(default=None, max_length=300)


@router.post("/{deal_id}/mark-sent")
def mark_sent(deal_id: uuid.UUID, p: MarkSentIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> dict:
    """Sent some other way (downloaded and emailed by hand): noted on the client the same way."""
    d = _get(db, deal_id)
    _need_edit(db, identity, d)
    _log_sent(db, d, identity.user_uuid, "other", [p.to.strip()] if p.to and p.to.strip() else [])
    db.commit()
    return _out(db, d, identity)
