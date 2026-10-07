"""What BMI already knows about a client, gathered for a proposal: their
booking history from the order register and the rate card for the title.
Everything the drafting step may quote comes from here - nothing else.
"""
from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, SalesEdition, SalesOrder, SalesRate, SalesTitle
from app.sales.analytics import BOOKED

MAX_HISTORY_ROWS = 12


def gbp(v: float) -> str:
    return f"£{v:,.2f}" if v != int(v) else f"£{int(v):,}"


def rate_card(db: Session, title_id: uuid.UUID | None, year: int) -> list[dict]:
    if not title_id:
        return []
    rows = db.scalars(select(SalesRate).where(SalesRate.title_id == title_id, SalesRate.year == year, SalesRate.archived.is_(False),
                                              SalesRate.price_gbp.isnot(None))
                      .order_by(SalesRate.price_gbp.desc())).all()
    return [{"id": str(r.id), "product": r.product, "price_gbp": float(r.price_gbp), "notes": r.notes} for r in rows]


def client_history(db: Session, company_id: uuid.UUID) -> dict:
    rows = db.execute(
        select(SalesOrder, SalesEdition, SalesTitle)
        .join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
        .join(SalesTitle, SalesEdition.title_id == SalesTitle.id)
        .where(SalesOrder.company_id == company_id, SalesOrder.status == BOOKED)
        .order_by(SalesOrder.booked_on.desc().nullslast(), SalesEdition.year.desc())
    ).all()
    bookings = [{
        "title": t.name, "edition": e.name, "year": e.year, "size": o.size,
        "value_gbp": float(o.value_gbp or 0), "booked_on": o.booked_on.isoformat() if o.booked_on else None,
    } for o, e, t in rows]
    by_year: dict[int, float] = defaultdict(float)
    for b in bookings:
        by_year[b["year"]] += b["value_gbp"]
    return {
        "count": len(bookings),
        "total_gbp": round(sum(by_year.values()), 2),
        "by_year": {str(y): round(v, 2) for y, v in sorted(by_year.items(), reverse=True)},
        "bookings": bookings[:MAX_HISTORY_ROWS],
    }


def build_context(db: Session, company: Company, title: SalesTitle | None, year: int) -> tuple[dict, list[str]]:
    """(context, flags). Flags are plain-English gaps - the builder shows
    them instead of inventing what's missing."""
    history = client_history(db, company.id)
    rates = rate_card(db, title.id if title else None, year)
    flags: list[str] = []
    if not history["count"]:
        flags.append("No bookings on record for this client, so the proposal is written as for a new client.")
    if title and not rates:
        flags.append(f"No {year} rate card for {title.name} yet, so prices need adding by hand.")
    if not title:
        flags.append("No title chosen, so there are no rate card prices to pick from.")
    flags.append("The editorial plan isn't loaded yet, so add any editorial or feature details yourself.")
    return {"company": company.name, "title": title.name if title else None, "year": year,
            "history": history, "rates": rates}, flags
