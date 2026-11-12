"""The booking form's Publication drop-down: BMI's own list of what they sell (Craig McQuinn, 12 Nov 2026, v2), each
option filed under an existing sales title so nothing about the order register, figures or commission changes.

Each entry: (label, sales title slug, rate sections, rate words, rate words to leave out, booked by, edition words).
Empty lists mean "no filter". booked_by: issue | dates | event.
"""
from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BookingProduct, SalesRate, SalesTitle

SOLUS = ["solus", "dedicated"]
STARTING: list[tuple[str, list[tuple]]] = [
    ("Onboard Hospitality", [
        ("OBH Magazine", "obh", ["print", "sponsored"], [], [], "issue", []),
        ("OBH Weekly Newsletter", "obh-web", ["newsletter"], [], SOLUS, "dates", []),
        ("OBH Web", "obh-web", ["website"], [], [], "dates", []),
        ("OBH Client Solus Email", "obh-web", ["newsletter"], SOLUS, [], "dates", []),
        ("OBH Awards", "obh-awards", ["awards"], [], [], "event", []),
        ("OBH Finder", "obh-web", ["listings"], [], [], "dates", []),
    ]),
    ("The Business Travel Magazine", [
        ("TBTM Magazine", "tbtm", ["print", "sponsored"], [], [], "issue", []),
        ("TBTM Weekly Newsletter", "tbtm", ["newsletter"], [], SOLUS, "dates", []),
        ("TBTM Web", "tbtm", ["website"], [], [], "dates", []),
        ("TBTM Client Solus Email", "tbtm", ["newsletter"], SOLUS, [], "dates", []),
        ("TBTM People Awards", "tbtm-events", ["awards"], [], [], "event", ["award"]),
        ("TBTM Dinner Club", "tbtm-events", ["events"], ["dinner"], [], "event", ["dinner"]),
        ("TBTM Lunch Forum", "tbtm-events", ["events"], ["lunch"], [], "event", ["lunch"]),
        ("TBTM Travel Quiz", "tbtm-events", ["events"], ["quiz"], [], "event", ["quiz"]),
    ]),
    ("Selling Travel", [
        ("ST Magazine", "selling-travel", ["print", "sponsored"], [], [], "issue", []),
        ("ST Weekly Newsletter", "selling-travel-online", ["newsletter"], [], SOLUS, "dates", []),
        ("ST Web", "selling-travel-online", ["website"], [], [], "dates", []),
        ("ST Client Solus Email", "selling-travel-online", ["newsletter"], SOLUS, [], "dates", []),
        ("ST Travel for Everybody Awards", "travel-for-every-body-awards", [], [], [], "event", []),
        ("ST Connect Event", "stm-connect-events", [], [], [], "event", []),
        ("ST Selling Canada", "selling-canada", [], [], [], "issue", []),
        ("ST Selling Australia", "selling-australia", [], [], [], "issue", []),
        ("ST Guide to the Caribbean", "selling-travel-guides", [], ["caribbean"], [], "issue", ["caribbean"]),
        ("ST Visit USA Online", "visit-usa-online", [], [], [], "dates", []),
        ("ST Visit USA Travel Planner", "visit-usa-planner", [], [], [], "issue", []),
        ("ST Supplements", "selling-travel-supplements", [], [], [], "issue", []),
    ]),
]


def seed(db: Session) -> int:
    """Adds the starting list once (only when there are no options yet). Returns how many were added."""
    if db.scalar(select(BookingProduct.id).limit(1)):
        return 0
    titles = {t.slug: t.id for t in db.scalars(select(SalesTitle))}
    n = 0
    for gi, (group, items) in enumerate(STARTING):
        for i, (label, slug, sections, words, exclude, booked_by, ed_words) in enumerate(items):
            if slug not in titles:
                continue
            db.add(BookingProduct(id=uuid.uuid4(), label=label, group_label=group, title_id=titles[slug], rate_sections=sections,
                                  rate_words=words, rate_exclude=exclude, booked_by=booked_by, edition_words=ed_words,
                                  sort_order=(gi + 1) * 100 + i))
            n += 1
    db.flush()
    return n


def _has(text: str, words: list[str]) -> bool:
    t = (text or "").lower()
    return any(re.search(re.escape(w.lower()), t) for w in words if w.strip())


def rate_matches(p: BookingProduct, r: SalesRate) -> bool:
    if r.title_id != p.title_id:
        return False
    if p.rate_sections and r.section not in p.rate_sections:
        return False
    if p.rate_words and not _has(r.product, p.rate_words):
        return False
    return not (p.rate_exclude and _has(r.product, p.rate_exclude))


def out(p: BookingProduct, rates: list[SalesRate]) -> dict:
    return {"id": str(p.id), "label": p.label, "group": p.group_label, "title_id": str(p.title_id), "booked_by": p.booked_by,
            "rate_sections": p.rate_sections, "rate_words": p.rate_words, "rate_exclude": p.rate_exclude,
            "edition_words": p.edition_words, "sort_order": p.sort_order, "active": p.active,
            "rate_ids": [str(r.id) for r in rates if rate_matches(p, r)]}
