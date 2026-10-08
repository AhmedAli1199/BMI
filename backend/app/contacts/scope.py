""""Which contacts?" for the tools that act on many at once (copy emails,
bulk update): either a hand-picked list, or a search exactly like the one on
the contacts screen. Always limited to the databases the signed-in person may
see."""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contacts.conditions import BadCondition, parse_conditions
from app.core.identity import Identity
from app.models import Contact
from app.services.contact_lookup import LookupFilters, lookup_ids

MAX_CONTACTS = 50000


class Scope(BaseModel):
    ids: list[uuid.UUID] = Field(default_factory=list, max_length=MAX_CONTACTS)
    q: str | None = None
    source_db: str | None = None
    company_id: uuid.UUID | None = None
    group_id: uuid.UUID | None = None
    company: str | None = None
    city: str | None = None
    country: str | None = None
    title: str | None = None
    conds: str | None = None
    match: str = "all"
    label: str | None = None  # shown in the history ("12 Travel Counsellors")


def resolve(db: Session, scope: Scope, identity: Identity) -> list[uuid.UUID]:
    try:
        conditions = parse_conditions(scope.conds)
    except BadCondition as exc:
        raise HTTPException(422, str(exc))
    if scope.ids:
        f = LookupFilters(contact_ids=list(dict.fromkeys(scope.ids)))
    else:
        f = LookupFilters(q=scope.q, source_db=scope.source_db, company_id=scope.company_id, group_id=scope.group_id,
                          company=scope.company, city=scope.city, country=scope.country, title=scope.title,
                          conditions=conditions, match_any=scope.match == "any")
    ids = lookup_ids(db, f, limit=MAX_CONTACTS + 1)
    if len(ids) > MAX_CONTACTS:
        raise HTTPException(413, f"That's more than {MAX_CONTACTS:,} contacts - narrow the search first.")
    from app.core.visibility import contact_clause

    seen = contact_clause(db, identity)  # whole databases or groups they've been given, read from their saved access
    if seen is not None and ids:
        ok = set(db.scalars(select(Contact.id).where(Contact.id.in_(ids), seen)))
        ids = [i for i in ids if i in ok]
    return ids
