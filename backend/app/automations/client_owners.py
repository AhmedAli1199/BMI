"""Who looks after each client - the nightly run and the "not sure" question (rules: app/sales/ownership.py).

Every night the rules are worked out again for every company. Where the Brain isn't sure (Selling Travel clients
with no destination it can find), administrators get one Review Queue card per client and magazine, with a
suggestion: "Use the suggestion", "Someone else" (pick from the salespeople) or "Not now". An answer is kept for
good - the same as changing it on the company page - so it's never asked again. A card closes by itself if a note
or booking settles it first.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.automations.registry import ExtraField, ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.db.session import SessionLocal
from app.models import ClientOwner, Company, ReviewQueueItem, SalesRep, User
from app.sales import ownership

logger = logging.getLogger("app.automations.client_owners")

KIND = "client_owner"


def _dedupe(company_id, area: str) -> str:
    return f"{KIND}:{company_id}:{area}"


def _choices(db: Session, area: ownership.Area) -> list[dict]:
    reps = db.scalars(select(SalesRep).where(SalesRep.active.is_(True)).order_by(SalesRep.name)).all()
    team = [r for r in reps if r.code in area.team] or reps
    return [{"value": str(r.id), "label": r.name} for r in team]


def _payload(db: Session, company: Company, row: ClientOwner) -> dict:
    area = ownership.BY_KEY[row.area]
    rep = db.get(SalesRep, row.rep_id) if row.rep_id else None
    details = [
        {"label": "Client", "value": company.name, "href": f"/companies/{company.id}"},
        {"label": "Magazine", "value": area.magazine},
        {"label": "Why we're not sure", "value": row.reason},
        {"label": "Suggestion", "value": rep.name if rep else "No suggestion - choose someone"},
    ]
    if company.website:
        site = company.website if company.website.startswith("http") else f"https://{company.website}"
        details.append({"label": "Website", "value": company.website, "href": site})
    return {
        "summary": f"Who looks after {company.name} on {area.magazine}?",
        "details": details,
        "company_id": str(company.id),
        "area": row.area,
        "suggested_rep_id": str(rep.id) if rep else None,
        "related_entities": [{"type": "company", "id": str(company.id), "label": company.name}],
        "field_options": {"rep_id": _choices(db, area)},
        "field_defaults": {"rep_id": str(rep.id) if rep else ""},
        "facets": {"magazine": area.magazine, "suggestion": rep.name if rep else "No suggestion",
                   "why": "Last contact over two years ago" if rep else "No destination found"},
        "sort_date": row.evidence_on.isoformat() if row.evidence_on else None,
        "dedupe_key": _dedupe(company.id, row.area),
    }


def ask(db: Session, pairs: list[tuple], limit: int) -> int:
    """One card per (company, area) never asked before, most recently active first, at most `limit`."""
    if not pairs or limit <= 0:
        return 0
    asked = {r[0] for r in db.execute(select(ReviewQueueItem.payload["dedupe_key"].astext).where(ReviewQueueItem.kind == KIND))}
    rows = [db.scalars(select(ClientOwner).where(ClientOwner.company_id == c, ClientOwner.area == a)).first() for c, a in pairs
            if _dedupe(c, a) not in asked]
    rows = sorted((r for r in rows if r and r.rule == "not_sure"), key=lambda r: r.evidence_on or datetime.min.date(), reverse=True)
    made = 0
    for row in rows[:limit]:
        company = db.get(Company, row.company_id)
        if not company:
            continue
        db.add(ReviewQueueItem(id=uuid.uuid4(), kind=KIND, source_db=company.source_db, status="pending", entity_type="company",
                               entity_id=company.id, payload=_payload(db, company, row)))
        made += 1
    return made


def settle(db: Session) -> int:
    """Close questions the rules have answered since (a note or booking came in, or someone changed it on the company page)."""
    closed = 0
    now = datetime.now(timezone.utc)
    for it in db.scalars(select(ReviewQueueItem).where(ReviewQueueItem.kind == KIND, ReviewQueueItem.status == "pending")):
        row = db.scalars(select(ClientOwner).where(ClientOwner.company_id == uuid.UUID(it.payload["company_id"]),
                                                   ClientOwner.area == it.payload["area"])).first()
        if row and row.rule == "not_sure":
            continue
        rep = db.get(SalesRep, row.rep_id) if row and row.rep_id else None
        it.status, it.resolved_action, it.reviewed_at = "approved", "settled", now
        it.review_note = f"Settled: {rep.name if rep else 'nobody yet'} - {row.reason}" if row else "The client is no longer on this magazine."
        closed += 1
    return closed


def scan() -> None:
    db = SessionLocal()
    try:
        stats = ownership.refresh(db)
        closed = settle(db)
        made = ask(db, stats["not_sure"], runtime_settings.get_int(db, "ownership_max_questions"))
        db.commit()
        logger.info("client owners: %d companies, %d changed, %d questions asked, %d settled",
                    stats["companies"], stats["changed"], made, closed)
    finally:
        db.close()


def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "later":
        return
    company = db.get(Company, uuid.UUID(item.payload["company_id"]))
    if not company:
        raise ValueError("This client has been deleted, so there's nothing to decide.")
    if action_id == "suggested":
        rid = item.payload.get("suggested_rep_id")
        if not rid:
            raise ValueError("There's no suggestion for this one. Press Someone else and pick the salesperson.")
    elif action_id == "choose":
        rid = (input_data.get("rep_id") or "").strip()
        allowed = {o["value"] for o in (item.payload.get("field_options") or {}).get("rep_id", [])}
        if rid not in allowed:
            raise ValueError("Pick the salesperson from the list.")
    else:
        raise ValueError("That button isn't available on this card.")
    rep = db.get(SalesRep, uuid.UUID(rid))
    if not rep:
        raise ValueError("That salesperson isn't in BMI Brain any more. Choose someone else.")
    uid = input_data.get("_actor_user_id")
    user = db.get(User, uuid.UUID(uid)) if uid else None
    ownership.choose(db, company, item.payload["area"], rep, user.id if user else None, user.name if user else None)


register(ReviewKind(
    kind=KIND,
    label="Who looks after a client",
    description="Clients the Brain couldn't place with a salesperson by the agreed rules - usually Selling Travel clients with no destination it can find. Your answer is kept for good.",
    actions=[
        ReviewAction(id="suggested", label="Use the suggestion", style="primary", outcome="approved"),
        ReviewAction(id="choose", label="Someone else", style="secondary", outcome="approved",
                     extra_fields=[ExtraField(key="rep_id", label="Salesperson", field_type="select")]),
        ReviewAction(id="later", label="Not now", style="secondary", outcome="dismissed", reopenable=True),
    ],
    handler=_handle,
    audience="admin",
    facets=(("magazine", "Magazine"), ("suggestion", "Suggestion"), ("why", "Why")),
    date_sort_label="contact",
))

register_job(ScheduledJob(
    id="client_owner_refresh",
    label="Who looks after each client",
    description="Every night: works out which salesperson looks after each client on each magazine, and asks about the ones it isn't sure of.",
    cron="40 1 * * *",
    func=scan,
    enabled_flag="automations_client_owners_enabled",
))
