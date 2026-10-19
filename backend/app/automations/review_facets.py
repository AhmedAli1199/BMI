"""Shared helpers for review-card filters ("facets"), date sorting and record links.

Each kind that declares `ReviewKind.facets` also gives a `derive_facets(db, item)` function that
returns what to merge into the card's payload: {"facets": {...}, "sort_date": "YYYY-MM-DD", ...}.
New cards are stamped with it as they are queued (`stamp`), and a kind's scan calls `backfill` so
cards queued before the kind had filters pick them up on the next run. A card that still has no
filter values shows under "Not set" on the review screen (see review_queue.py's _facet_expr).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import MANUAL_SOURCE_DB
from app.models import Company, Contact, Publication, ReviewQueueItem, User

NOT_SET = "Not set"
# Enough to catch up a big queue over a few runs without making any one scan slow.
BACKFILL_LIMIT = 500


def database_name(db: Session, source_db: str | None) -> str:
    if not source_db:
        return "No database"
    if source_db == "*":
        return "Shared inbox"
    if source_db == MANUAL_SOURCE_DB:
        return "Added in the CRM"
    return db.scalar(select(Publication.name).where(Publication.slug == source_db)) or source_db


def user_name(db: Session, user_id) -> str | None:
    if not user_id:
        return None
    try:
        user = db.get(User, user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id)))
    except ValueError:
        return None
    return user.name if user else None


def owner_name(db: Session, contact: Contact | None) -> str:
    """Who looks after this contact: their own owner, else their company's owner."""
    if not contact:
        return "No owner"
    name = user_name(db, contact.owner_user_id)
    if not name and contact.company_id:
        company = db.get(Company, contact.company_id)
        name = user_name(db, company.owner_user_id) if company else None
    return name or "No owner"


def iso_day(value) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and value:
        return value[:10]
    return None


def contact_of(db: Session, contact_id) -> Contact | None:
    if not contact_id:
        return None
    try:
        return db.get(Contact, contact_id if isinstance(contact_id, uuid.UUID) else uuid.UUID(str(contact_id)))
    except ValueError:
        return None


def contact_label(contact: Contact) -> str:
    return contact.full_name or " ".join(filter(None, [contact.first_name, contact.last_name])) or "Contact"


def company_link(db: Session, contact: Contact | None, label: str = "Company") -> dict | None:
    """A details row linking the contact's company, if they have one in the CRM."""
    if not contact or not contact.company_id:
        return None
    company = db.get(Company, contact.company_id)
    if not company:
        return None
    return {"key": "company_link", "label": label, "value": company.name, "href": f"/companies/{company.id}"}


def with_links(details: list[dict] | None, rows: Iterable[dict | None]) -> list[dict]:
    """Adds link rows to a card's details, skipping any whose key is already there (so re-running is safe)."""
    out = list(details or [])
    have = {d.get("key") for d in out if d.get("key")}
    for row in rows:
        if row and row.get("key") not in have:
            out.append(row)
            have.add(row.get("key"))
    return out


def stamp(db: Session, item: ReviewQueueItem) -> ReviewQueueItem:
    """Fill in this card's filter values (and sort date / links) from its kind's derive_facets."""
    from app.automations.registry import get_kind

    kind_def = get_kind(item.kind)
    if kind_def and kind_def.derive_facets:
        item.payload = {**(item.payload or {}), **kind_def.derive_facets(db, item)}
    return item


def backfill(db: Session, kinds: Iterable[str], limit: int = BACKFILL_LIMIT) -> int:
    """Gives waiting cards of these kinds that were queued before filters existed their filter values.
    Bounded per run; the rest are picked up next time. Caller commits."""
    items = db.scalars(
        select(ReviewQueueItem)
        .where(ReviewQueueItem.kind.in_(list(kinds)), ReviewQueueItem.status == "pending",
               ~ReviewQueueItem.payload.has_key("facets"))  # JSONB "?" operator
        .limit(limit)
    ).all()
    for item in items:
        stamp(db, item)
    return len(items)
