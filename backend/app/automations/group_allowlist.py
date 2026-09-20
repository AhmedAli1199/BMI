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
