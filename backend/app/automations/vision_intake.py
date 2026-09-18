"""Shared helpers for the two photo-upload automations - business card
capture (business_card.py) and returned copy processing (returned_copy.py).
Both follow the same shape: a rep uploads a photo, a vision model reads it,
we try to match what it read against an existing contact/company, and
queue a review item either way. This module holds the two pieces that
shape has in common so neither automation duplicates it.
"""
from __future__ import annotations

import base64

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Company, Contact

# Below this trigram similarity, don't even suggest a match - a low-
# confidence guess is worse than no guess (same principle as every other
# automation's confidence gating in this codebase).
MATCH_THRESHOLD = 0.35

MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8MB - generous for a phone photo, cheap to reject anything absurd upfront


def encode_image_data_url(image_bytes: bytes, content_type: str) -> str:
    b64 = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{content_type};base64,{b64}"


def find_similar_contact(db: Session, *, name: str | None, company_name: str | None, source_db: str) -> Contact | None:
    """Best-effort fuzzy match on name (+ company name as a tiebreaker),
    scoped to one source_db - contacts are deliberately kept separate per
    title (see contact.py's docstring), so a match should never cross that
    boundary. Returns the single best match above MATCH_THRESHOLD, or None
    - callers always have a "create new" path for a None result, never
    block on this.
    """
    if not name:
        return None
    row = db.execute(
        text(
            "SELECT id, similarity(full_name, :name) AS sim "
            "FROM contacts WHERE source_db = :source_db AND full_name IS NOT NULL "
            "ORDER BY sim DESC LIMIT 1"
        ),
        {"name": name, "source_db": source_db},
    ).first()
    if not row or row.sim < MATCH_THRESHOLD:
        return None
    return db.get(Contact, row.id)


def find_similar_company(db: Session, *, name: str | None, source_db: str) -> Company | None:
    if not name:
        return None
    row = db.execute(
        text(
            "SELECT id, similarity(name, :name) AS sim "
            "FROM companies WHERE source_db = :source_db "
            "ORDER BY sim DESC LIMIT 1"
        ),
        {"name": name, "source_db": source_db},
    ).first()
    if not row or row.sim < MATCH_THRESHOLD:
        return None
    return db.get(Company, row.id)
