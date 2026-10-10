"""Prices a proposal: lines across several titles and issues, rate-card offers, a % off any
line, a % off the whole proposal, and options the client chooses between.

A line ({"product", "qty", "unit_price", "source", "rate_id", "title_id", "issues", "discount_pct", "option"}):
- runs in the issues listed (from the editorial plan), so its quantity is the number of issues;
  or has a plain quantity (a year of website banners, 4 newsletters);
- rate-card lines are priced from the rate card, whatever the browser sent; own lines keep the typed price;
- "option" groups lines into choices ("Option A: one issue", "Option B: the year"). Lines without an
  option are part of every option. With no options there's one total.
Rate-card offers ("book 3, save 20%") are worked out per option and title and shown as their own lines.
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SalesEdition, SalesRate, SalesTitle
from app.sales.offers import apply_offers

KINDS = {
    "issue": "A single issue",
    "multi": "Several issues",
    "annual": "A year's programme",
    "digital": "Digital (website, newsletters, social)",
    "sponsorship": "Awards or event sponsorship",
    "mixed": "A mixed package",
}


def _r(v: float) -> float:
    return round(v + 0.0, 2)


def _issue_label(db: Session, eid: str) -> tuple[str | None, str | None]:
    from app.sales.editorial import fmt_day, issue_label
    try:
        e = db.get(SalesEdition, uuid.UUID(str(eid)))
    except ValueError:
        return None, None
    if not e:
        return None, None
    return issue_label(e), (fmt_day(e.edition_date) if e.edition_date else None)


def price_lines(db: Session, raw: list[dict], default_title_id: uuid.UUID | None, year: int) -> tuple[list[dict], list[str]]:
    """(priced lines including offer lines, notes). Raises 422 for a line that can't be priced."""
    base: list[dict] = []
    for ln in raw:
        if ln.get("source") == "offer":
            continue
        issues = [str(i) for i in (ln.get("issues") or []) if i]
        labels = []
        for i in issues:
            label, day = _issue_label(db, i)
            if not label:
                raise HTTPException(422, f"One of the issues for “{ln.get('product')}” isn't in the editorial plan any more.")
            labels.append(f"{label} ({day})" if day else label)
        qty = len(issues) if issues else max(1, int(ln.get("qty") or 1))
        disc = min(max(float(ln.get("discount_pct") or 0), 0.0), 1.0)
        title_id = ln.get("title_id") or (str(default_title_id) if default_title_id else None)
        out = {"id": ln.get("id") or str(uuid.uuid4()), "qty": qty, "issues": issues, "issue_labels": labels, "discount_pct": disc,
               "option": (ln.get("option") or "").strip()[:80] or None, "title_id": title_id}
        if ln.get("source") == "rate_card":
            rate = db.get(SalesRate, uuid.UUID(str(ln["rate_id"]))) if ln.get("rate_id") else None
            if rate is None and title_id:
                rate = db.scalars(select(SalesRate).where(SalesRate.title_id == uuid.UUID(str(title_id)), SalesRate.year == year,
                                                          SalesRate.product == ln.get("product"))).first()
            if rate is None:
                raise HTTPException(422, f"“{ln.get('product')}” isn't on the rate card - add it as your own line instead.")
            if rate.price_gbp is None:
                raise HTTPException(422, f"“{rate.product}” is priced on request - add it as your own line with the price you've agreed.")
            out.update(product=rate.product, unit_price=float(rate.price_gbp), source="rate_card", rate_id=str(rate.id),
                       list_price=float(rate.price_gbp), title_id=str(rate.title_id))
        else:
            if ln.get("unit_price") is None:
                raise HTTPException(422, f"Add a price for “{ln.get('product')}”.")
            out.update(product=(ln.get("product") or "").strip(), unit_price=round(float(ln["unit_price"]), 2), source="manual")
        if not out["product"]:
            raise HTTPException(422, "Every line needs a name.")
        base.append(out)
    # Rate-card offers, per option (lines in every option count towards each) and per title.
    notes: list[str] = []
    result = list(base)
    options = [o for o in dict.fromkeys(ln["option"] for ln in base) if o]
    for opt in (options or [None]):
        group = [ln for ln in base if ln["option"] in (opt, None)]
        for tid in dict.fromkeys(ln["title_id"] for ln in group):
            lines = [ln for ln in group if ln["title_id"] == tid]
            priced, n = apply_offers(db, lines, uuid.UUID(tid) if tid else None, year)
            notes += [x for x in n if x not in notes]
            for off in (x for x in priced if x.get("source") == "offer"):
                off.update(option=opt, title_id=tid, issues=[], issue_labels=[], discount_pct=0.0)
                result.append(off)
    return result, notes


def line_total(ln: dict) -> float:
    return _r(float(ln.get("qty") or 1) * float(ln.get("unit_price") or 0) * (1 - float(ln.get("discount_pct") or 0)))


def totals(lines: list[dict], discount_pct: float = 0.0) -> list[dict]:
    """One entry per option (or a single one): what's in it, and its total after the % off the whole proposal."""
    options = [o for o in dict.fromkeys(ln.get("option") for ln in lines) if o]
    out = []
    for opt in (options or [None]):
        group = [ln for ln in lines if ln.get("option") in (opt, None)]
        sub = _r(sum(line_total(ln) for ln in group))
        disc = _r(sub * min(max(discount_pct, 0.0), 1.0))
        rate = _r(sum(float(ln.get("qty") or 1) * float(ln.get("list_price") or ln.get("unit_price") or 0) for ln in group if ln.get("source") != "offer"))
        out.append({"option": opt, "subtotal_gbp": sub, "discount_gbp": disc, "total_gbp": _r(sub - disc), "rate_card_gbp": rate,
                    "lines": len([ln for ln in group if ln.get("source") != "offer"])})
    return out


def headline_total(lines: list[dict], discount_pct: float = 0.0) -> float:
    return totals(lines, discount_pct)[0]["total_gbp"]


def title_names(db: Session, lines: list[dict]) -> list[str]:
    ids = [uuid.UUID(t) for t in dict.fromkeys(ln.get("title_id") for ln in lines) if t]
    names = {str(t.id): t.name for t in db.scalars(select(SalesTitle).where(SalesTitle.id.in_(ids)))} if ids else {}
    return [names[str(i)] for i in ids if str(i) in names]
