"""Links SOR clients (free text, typed by reps) to CRM companies.

- An exact match on a normalised name ("Air Canada Ltd" = "air canada")
  links every booking for that client straight away - no reviewer needed.
  When the same name exists in more than one CRM database, the one the
  title belongs to (OBH -> onboard, everything else -> sellingtravel)
  wins.
- A likely-but-not-certain match (pg_trgm similarity) becomes ONE
  "sor_client_match" review item per client name - not per booking - so a
  reviewer confirms "Brunswick - Delice de France" is Brunswick once and
  all of its bookings follow.
- A client with no plausible match stays unlinked; that's normal for a
  new advertiser who isn't in the CRM yet.
"""
from __future__ import annotations

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Company, ReviewQueueItem, SalesEdition, SalesOrder, SalesTitle

MATCH_KIND = "sor_client_match"
SIMILARITY_THRESHOLD = 0.45

_SUFFIXES = r"\b(ltd|limited|inc|llc|plc|gmbh|bv|b\.v|sa|s\.a|ag|co|corp|corporation|group|the)\b"


def normalise(name: str) -> str:
    s = name.lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"\bvia\b.*$", " ", s)  # "Walther Trowal via VIP Kommunikation" -> the advertiser
    s = re.sub(_SUFFIXES, " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


def _already_queued(db: Session) -> set[str]:
    return {
        (v or "").lower()
        for v in db.scalars(
            select(ReviewQueueItem.payload["client_name"].astext).where(
                ReviewQueueItem.kind == MATCH_KIND, ReviewQueueItem.status == "pending")
        )
    }


def match_clients(db: Session, max_queued: int = 200) -> tuple[int, int]:
    """Returns (bookings linked, review items queued)."""
    rows = db.execute(
        select(SalesOrder.id, SalesOrder.client_name, SalesTitle.crm_source_db, SalesOrder.value_gbp)
        .join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
        .join(SalesTitle, SalesEdition.title_id == SalesTitle.id)
        .where(SalesOrder.company_id.is_(None), SalesOrder.match_dismissed.is_(False))
    ).all()
    if not rows:
        return 0, 0

    by_key: dict[str, list[tuple[uuid.UUID, str]]] = {}
    for c in db.execute(select(Company.id, Company.name, Company.source_db)).all():
        key = normalise(c.name or "")
        if key:
            by_key.setdefault(key, []).append((c.id, c.source_db))

    groups: dict[str, dict] = {}
    for order_id, client, source_db, value in rows:
        g = groups.setdefault(client.strip().lower(), {"name": client.strip(), "ids": [], "source_db": source_db, "value": 0.0})
        g["ids"].append(order_id)
        g["value"] += float(value or 0)

    linked = 0
    queued = 0
    already = _already_queued(db)
    for lowered, g in groups.items():
        key = normalise(g["name"])
        if not key:
            continue
        hits = by_key.get(key)
        if hits:
            company_id = next((cid for cid, sdb in hits if sdb == g["source_db"]), hits[0][0])
            db.query(SalesOrder).filter(SalesOrder.id.in_(g["ids"])).update(
                {SalesOrder.company_id: company_id}, synchronize_session=False)
            linked += len(g["ids"])
            continue
        if lowered in already or queued >= max_queued or len(key) < 3:
            continue
        best = db.execute(
            select(Company, func.similarity(func.lower(Company.name), lowered).label("score"))
            .where(func.lower(Company.name).op("%")(lowered))
            .order_by(func.similarity(func.lower(Company.name), lowered).desc())
            .limit(1)
        ).first()
        if not best or best.score < SIMILARITY_THRESHOLD:
            continue
        company, score = best
        db.add(ReviewQueueItem(
            id=uuid.uuid4(), kind=MATCH_KIND, source_db=company.source_db,
            entity_type="company", entity_id=company.id,
            payload={
                "summary": f"Is SOR client “{g['name']}” the CRM company “{company.name}”?",
                "details": [
                    {"key": "client_name", "label": "Client in the order register", "value": g["name"]},
                    {"key": "company", "label": "Suggested CRM company", "value": company.name},
                    {"key": "bookings", "label": "Bookings affected", "value": f"{len(g['ids'])} (£{g['value']:,.0f})"},
                    {"key": "similarity", "label": "Name similarity", "value": f"{score:.0%}"},
                ],
                "related_entities": [{"type": "company", "id": str(company.id), "label": company.name}],
                "client_name": g["name"],
                "company_id": str(company.id),
                "confidence": round(float(score), 2),
            },
        ))
        already.add(lowered)
        queued += 1
    db.flush()
    return linked, queued
