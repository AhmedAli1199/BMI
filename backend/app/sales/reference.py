"""Fixed reference data for the Sales Order Register: which titles have
their own SOR workbook, and who the initials in the "Salesper." column
belong to. Idempotent - safe to call on every import and from tests.

Rep → CRM user matching was done from the SOR headers against the team
in scripts/seed_team.py:
- "S.Thompson" / "Steve" is Steven Thompson (sales), not Susan Thompson
  (the data manager) - the Connect Spain sheet labels the same column
  "Steve".
- L.Merrigan, D.Clare, A.Rogers, S.De Berniere and C.Blackwell only
  appear as leftover commission columns with nothing credited to them in
  2026 - former reps, kept (inactive, no login) so older years still
  attribute correctly.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import SalesRep, SalesTitle, User


@dataclass(frozen=True)
class TitleDef:
    slug: str
    name: str
    product_line: str  # print | digital | events | awards
    crm_source_db: str
    sort_order: int
    # Matched against the workbook's file name (case-insensitive), first
    # match wins - so more specific patterns come first.
    file_pattern: str


TITLES: list[TitleDef] = [
    TitleDef("obh-awards", "OBH Awards", "awards", "onboard", 20, r"obh awards"),
    TitleDef("obh-web", "OBH Web", "digital", "onboard", 30, r"obh web"),
    TitleDef("obh-forum-asia", "OBH Forum Asia", "events", "onboard", 40, r"obh forum asia"),
    TitleDef("obh", "OnBoard Hospitality (OBH)", "print", "onboard", 10, r"\bobh\b"),
    TitleDef("selling-travel-online", "Selling Travel Online", "digital", "sellingtravel", 60, r"selling travel online"),
    TitleDef("selling-travel-supplements", "Selling Travel Supplements", "print", "sellingtravel", 70, r"selling travel supplements"),
    TitleDef("selling-travel-guides", "Selling Travel Guides & Hubs", "digital", "sellingtravel", 75, r"selling travel guides"),
    TitleDef("selling-travel-events", "Selling Travel Events", "events", "sellingtravel", 80, r"selling travel events"),
    TitleDef("selling-travel", "Selling Travel", "print", "sellingtravel", 50, r"selling travel"),
    TitleDef("selling-canada", "Selling Canada", "print", "sellingtravel", 90, r"selling canada"),
    TitleDef("selling-australia", "Selling Australia", "print", "sellingtravel", 100, r"selling australia"),
    TitleDef("stm-connect-events", "STM Connect Events", "events", "sellingtravel", 110, r"stm connect"),
    TitleDef("tbtm-events", "TBTM Events", "events", "sellingtravel", 130, r"tbtm events"),
    TitleDef("tbtm", "The Business Travel Magazine (TBTM)", "print", "sellingtravel", 120, r"\btbtm\b"),
    TitleDef("visit-usa-online", "Visit USA Online", "digital", "sellingtravel", 150, r"visit usa online"),
    TitleDef("visit-usa-planner", "Visit USA Travel Planner", "print", "sellingtravel", 140, r"(visit usa|vusa) travel ?planner"),
    TitleDef("travel-for-every-body-awards", "Travel for Every Body Awards", "awards", "sellingtravel", 160, r"travel for every ?body"),
]


def title_for_file(file_name: str) -> TitleDef | None:
    lowered = file_name.lower()
    for t in TITLES:
        if re.search(t.file_pattern, lowered):
            return t
    return None


@dataclass(frozen=True)
class RepDef:
    code: str
    name: str
    email: str | None
    active: bool
    # Every spelling the SOR uses for this person, in either the
    # "Salesper." column or a commission column header.
    aliases: tuple[str, ...]


REPS: list[RepDef] = [
    RepDef("SW", "Sue Williams", "sue.williams@onboardhospitality.com", True, ("SW", "S.WILLIAMS", "S.WILLIAM")),
    RepDef("CM", "Craig McQuinn", "craig.mcquinn@bmipublishing.co.uk", True, ("CM", "C.MCQUINN")),
    RepDef("KH", "Kirsty Hicks", "kirsty.hicks@bmipublishing.co.uk", True, ("KH", "K.HICKS")),
    RepDef("SP", "Sally Parker", "sally.parker@bmipublishing.co.uk", True, ("SP", "S.PARKER")),
    RepDef("ST", "Steven Thompson", "steven.thompson@bmipublishing.co.uk", True, ("ST", "S.THOMPSON", "STEVE")),
    RepDef("DW", "David Wilcox", "david.wilcox@bmipublishing.co.uk", True, ("DW", "D.WILCOX")),
    RepDef("ND", "Neil Dargie", "neil.dargie@bmipublishing.co.uk", True, ("ND", "NEIL")),
    RepDef("LM", "L. Merrigan", None, False, ("LM", "L.MERRIGAN")),
    RepDef("DC", "D. Clare", None, False, ("DC", "D.CLARE")),
    RepDef("AR", "A. Rogers", None, False, ("AR", "A.ROGERS")),
    RepDef("SDB", "S. De Berniere", None, False, ("SDB", "SD", "S.DE BERNIERE", "SDEB")),
    RepDef("CB", "C. Blackwell", None, False, ("CB", "C.BLACKWELL", "C.BLACWELL")),
]

_ALIAS_TO_CODE = {re.sub(r"\s+", " ", a): r.code for r in REPS for a in r.aliases}


def rep_code_for(raw: str | None) -> str | None:
    """Initials or a commission-column header -> rep code, or None."""
    if not raw:
        return None
    key = re.sub(r"\s+", " ", str(raw).strip().upper().replace(". ", "."))
    return _ALIAS_TO_CODE.get(key)


def ensure_reference_data(db: Session) -> None:
    for t in TITLES:
        row = db.query(SalesTitle).filter_by(slug=t.slug).one_or_none()
        if not row:
            db.add(SalesTitle(id=uuid.uuid4(), slug=t.slug, name=t.name, product_line=t.product_line,
                              crm_source_db=t.crm_source_db, sort_order=t.sort_order))
    for r in REPS:
        row = db.query(SalesRep).filter_by(code=r.code).one_or_none()
        user_id = None
        if r.email:
            user_id = db.query(User.id).filter(func.lower(User.email) == r.email.lower()).scalar()
        if not row:
            db.add(SalesRep(id=uuid.uuid4(), code=r.code, name=r.name, active=r.active, user_id=user_id))
        elif row.user_id is None and user_id is not None:
            row.user_id = user_id
    db.flush()
