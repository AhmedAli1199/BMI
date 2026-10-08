"""Who may see which contacts, companies and groups - enforced on the server.

A person's access is a list of grants (Settings > Users > Database access): a whole
database, or one group inside a database (that group and its sub-groups). Admins,
and internal callers with no identity, see everything. Grants are read fresh from
the database on every request, so a change in Settings applies straight away.

`current()` is the signed-in person for this request (set by the middleware in
app/main.py), so the shared contact search (app/services/contact_lookup.py) and the
list endpoints can limit results without every caller passing it through.
"""
from __future__ import annotations

import contextvars
import uuid
from dataclasses import dataclass

from sqlalchemy import false, or_, select, text
from sqlalchemy.orm import Session

from fastapi import Depends, HTTPException, Request

from app.core.identity import Identity, get_identity
from app.db.session import get_db

_current: contextvars.ContextVar[Identity | None] = contextvars.ContextVar("bmi_identity", default=None)


def set_current(identity: Identity | None):
    return _current.set(identity)


def current() -> Identity | None:
    return _current.get()


@dataclass(frozen=True)
class Grants:
    unrestricted: bool
    full_dbs: frozenset[str]
    groups: frozenset[uuid.UUID]          # every group a person may see (their granted groups and sub-groups)
    group_dbs: frozenset[str]             # databases where they only have group access

    @property
    def nothing(self) -> bool:
        return not self.unrestricted and not self.full_dbs and not self.groups


def _subtree(db: Session, roots: list[uuid.UUID]) -> set[uuid.UUID]:
    if not roots:
        return set()
    rows = db.execute(text(
        "WITH RECURSIVE subtree AS (SELECT id FROM groups WHERE id = ANY(:ids) "
        "UNION ALL SELECT g.id FROM groups g JOIN subtree s ON g.parent_group_id = s.id) SELECT id FROM subtree"
    ), {"ids": [str(r) for r in roots]}).scalars().all()
    return {uuid.UUID(str(r)) for r in rows}


def grants(db: Session, identity: Identity | None = None) -> Grants:
    identity = identity if identity is not None else current()
    if identity is None or not identity.is_known or identity.is_admin:
        return Grants(True, frozenset(), frozenset(), frozenset())
    pairs: list[tuple[str, str | None]] = list(identity.access)
    uid = identity.user_uuid
    if uid:
        from app.models import UserAccess
        rows = db.execute(select(UserAccess.source_db, UserAccess.group_id).where(UserAccess.user_id == uid)).all()
        if rows:  # the saved grants win over what the browser session remembered
            pairs = [(s, str(g) if g else None) for s, g in rows]
    full = {s for s, g in pairs if not g}
    roots = []
    for s, g in pairs:
        if g and s not in full:
            try:
                roots.append(uuid.UUID(str(g)))
            except ValueError:
                continue
    return Grants(False, frozenset(full), frozenset(_subtree(db, roots)), frozenset({s for s, g in pairs if g and s not in full}))


def contact_clause(db: Session, identity: Identity | None = None):
    """A WHERE condition on Contact for what this person may see, or None for everything."""
    from app.models import Contact, GroupMembership
    g = grants(db, identity)
    if g.unrestricted:
        return None
    parts = []
    if g.full_dbs:
        parts.append(Contact.source_db.in_(g.full_dbs))
    if g.groups:
        parts.append(Contact.id.in_(select(GroupMembership.contact_id).where(GroupMembership.group_id.in_(g.groups))))
    return or_(*parts) if parts else false()


def company_clause(db: Session, identity: Identity | None = None):
    """Companies in a fully granted database, or the companies of the contacts someone may see through a group."""
    from app.models import Company, Contact, GroupMembership
    g = grants(db, identity)
    if g.unrestricted:
        return None
    parts = []
    if g.full_dbs:
        parts.append(Company.source_db.in_(g.full_dbs))
    if g.groups:
        parts.append(Company.id.in_(select(Contact.company_id).where(
            Contact.company_id.isnot(None),
            Contact.id.in_(select(GroupMembership.contact_id).where(GroupMembership.group_id.in_(g.groups))))))
    return or_(*parts) if parts else false()


def group_clause(db: Session, identity: Identity | None = None):
    from app.models import Group
    g = grants(db, identity)
    if g.unrestricted:
        return None
    parts = []
    if g.full_dbs:
        parts.append(Group.source_db.in_(g.full_dbs))
    if g.groups:
        parts.append(Group.id.in_(g.groups))
    return or_(*parts) if parts else false()


def _visible(db: Session, model, clause, ident: uuid.UUID) -> bool:
    if clause is None:
        return True
    return db.scalar(select(model.id).where(model.id == ident, clause)) is not None


def can_see_contact(db: Session, contact_id: uuid.UUID, identity: Identity | None = None) -> bool:
    from app.models import Contact
    return _visible(db, Contact, contact_clause(db, identity), contact_id)


def can_see_company(db: Session, company_id: uuid.UUID, identity: Identity | None = None) -> bool:
    from app.models import Company
    return _visible(db, Company, company_clause(db, identity), company_id)


def can_see_group(db: Session, group_id: uuid.UUID, identity: Identity | None = None) -> bool:
    from app.models import Group
    return _visible(db, Group, group_clause(db, identity), group_id)



def guard_records(request: Request, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)) -> None:
    """On the contact, company and group routes: a record outside someone's access simply doesn't exist for them."""
    params = request.path_params
    checks = (("contact_id", can_see_contact), ("successor_id", can_see_contact), ("company_id", can_see_company), ("group_id", can_see_group))
    for key, check in checks:
        raw = params.get(key)
        if not raw:
            continue
        try:
            ident = uuid.UUID(str(raw))
        except ValueError:
            continue
        if not check(db, ident, identity):
            raise HTTPException(404, "Not found")


def review_item_clause(db: Session, identity: Identity | None = None):
    """Review-queue / Today items about a contact or company only for people who can see that record."""
    from app.models import Company, Contact, ReviewQueueItem
    cc, co = contact_clause(db, identity), company_clause(db, identity)
    if cc is None:
        return None
    from sqlalchemy import and_
    return or_(
        and_(ReviewQueueItem.entity_type == "contact", ReviewQueueItem.entity_id.in_(select(Contact.id).where(cc))),
        and_(ReviewQueueItem.entity_type == "company", ReviewQueueItem.entity_id.in_(select(Company.id).where(co))),
        ReviewQueueItem.entity_type.is_(None),
        ReviewQueueItem.entity_type.notin_(("contact", "company")),
    )
