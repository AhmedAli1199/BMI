"""Curated group allowlist for SALES-011's "suggested groups" feature.

The groups research (832 total groups across the 3 source databases) found
real, clean segmentation lists sitting alongside ad-hoc historical import
artifacts ("TBTM New Data August 2019", "Hide from Craig", one-off test
groups). A group's size or name pattern alone can't tell those apart, so
this is a hand-curated allowlist, not a computed one - "suggested groups"
only ever draws from this set, never the full group table. Extend it as
BMI confirms more real segments; never add a group here by inferring it
from size/name matching alone.

Newsletter/distribution lists (TBTM Weekly Newsletter, Digital Newsletter,
etc.) are handled separately, as a single boolean "subscribe to
newsletter" toggle (see NEWSLETTER_GROUP) rather than a general group
suggestion - they're each tens of thousands of members and behave like an
opt-in flag, not a segment a rep picks from several options.
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Contact, Group, GroupMembership

# Real, curated segment groups eligible for "suggested groups" - keyed by
# source_db, matched by exact group name (case-insensitive).
ALLOWLISTED_GROUPS: dict[str, set[str]] = {
    "sellingtravel": {
        "leeds", "manchester", "chester", "bristol", "edinburgh", "newcastle", "birmingham",
    },
    "onboard": {
        "technology", "caterers", "reader airlines commercial",
    },
    "prospects": {
        "tbtm distribution uk only",
    },
}

# The one canonical newsletter/distribution group per source_db, offered as
# a single checkbox rather than a "suggested group" pick.
NEWSLETTER_GROUP: dict[str, str] = {
    "prospects": "TBTM Weekly newsletter",
    "onboard": "A = Circulation Digital Newsletter",
    "sellingtravel": "Full Export Email Only",
}


def is_allowlisted(source_db: str, group_name: str) -> bool:
    return group_name.strip().lower() in ALLOWLISTED_GROUPS.get(source_db, set())


def suggest_groups(db: Session, source_db: str, company_id) -> list:
    """Real segment groups this company's other contacts already belong
    to, restricted to the curated allowlist - shared by SALES-011 (inbound
    capture) and SALES-002 (business card dedupe), the two places that
    suggest groups for a newly-added contact. Never queries the raw group
    table beyond this filter - see this module's docstring for why."""
    allowed = ALLOWLISTED_GROUPS.get(source_db)
    if not company_id or not allowed:
        return []
    rows = (
        db.query(Group, func.count(GroupMembership.id).label("n"))
        .join(GroupMembership, GroupMembership.group_id == Group.id)
        .join(Contact, Contact.id == GroupMembership.contact_id)
        .filter(Contact.company_id == company_id, func.lower(Group.name).in_(allowed))
        .group_by(Group.id)
        .order_by(func.count(GroupMembership.id).desc())
        .limit(3)
        .all()
    )
    return [g for g, _ in rows]
