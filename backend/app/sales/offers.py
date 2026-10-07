"""Applies a brand's rate-card offers (app/models/sales.py RateOffer) to a list of
proposal lines - so a salesperson never has to work out "book 3, save 20%" by hand.

Each applied offer becomes its own line ("Offer: Book 2 adverts save 10%", a
negative amount) so the client sees exactly what was taken off and why.
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RateOffer, SalesRate, SalesTitle
from app.sales.brands import brand_for_title_slug


def _best(tiers: list[dict], qty: float) -> dict | None:
    ok = [t for t in tiers or [] if t.get("qty") and qty >= t["qty"]]
    return max(ok, key=lambda t: t["qty"]) if ok else None


def apply_offers(db: Session, lines: list[dict], title_id: uuid.UUID | None, year: int, today: date | None = None) -> tuple[list[dict], list[str]]:
    """(lines with any old offer lines replaced by fresh ones, notes about offers that couldn't apply)."""
    today = today or date.today()
    base = [ln for ln in lines if ln.get("source") != "offer"]
    t = db.get(SalesTitle, title_id) if title_id else None
    brand = brand_for_title_slug(t.slug) if t else None
    if not brand:
        return base, []
    rate_ids = [uuid.UUID(ln["rate_id"]) for ln in base if ln.get("source") == "rate_card" and ln.get("rate_id")]
    rates = {str(r.id): r for r in db.scalars(select(SalesRate).where(SalesRate.id.in_(rate_ids)))} if rate_ids else {}
    notes = []
    for ln in base:
        r = rates.get(ln.get("rate_id") or "")
        if r and r.valid_until and r.valid_until < today:
            notes.append(f"The price for {r.product} was valid until {r.valid_until:%d %b %Y} - check it's still right.")
    out = list(base)
    for o in db.scalars(select(RateOffer).where(RateOffer.brand == brand.key, RateOffer.year == year).order_by(RateOffer.sort_order)):
        if o.valid_until and o.valid_until < today:
            continue
        tiers = (o.rules or {}).get("tiers") or []
        ids = set(o.rate_ids or [])

        def eligible(ln: dict) -> bool:
            r = rates.get(ln.get("rate_id") or "")
            if not r or ln.get("source") != "rate_card":
                return False
            return str(r.id) in ids if ids else (o.section is None or r.section == o.section)

        if o.kind == "volume":
            el = [ln for ln in base if eligible(ln)]
            tier = _best(tiers, sum(float(ln["qty"]) for ln in el))
            if tier and tier.get("discount_pct"):
                amount = round(sum(float(ln["qty"]) * float(ln["unit_price"]) for ln in el) * float(tier["discount_pct"]) / 100, 2)
                if amount > 0:
                    out.append({"id": str(uuid.uuid4()), "product": f"Offer: {o.label}", "qty": 1, "unit_price": -amount, "source": "offer", "offer_id": str(o.id)})
        elif o.kind == "series":
            for ln in base:
                if not eligible(ln):
                    continue
                qty = float(ln["qty"])
                tier = _best(tiers, qty)
                if not tier:
                    continue
                each = float(tier["unit_price"]) if tier.get("unit_price") else float(tier["total"]) / float(tier["qty"])
                amount = round((float(ln["unit_price"]) - each) * qty, 2)
                if amount > 0:
                    out.append({"id": str(uuid.uuid4()), "product": f"Offer: {o.label} - {ln['product']}", "qty": 1, "unit_price": -amount,
                                "source": "offer", "offer_id": str(o.id)})
    return out, notes
