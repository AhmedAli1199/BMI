"""BMI's three brands, the way BMI itself talks about them (and lays out its
media packs): Onboard Hospitality, The Business Travel Magazine and Selling
Travel. The order register splits each brand into several "sales titles"
(OBH Web, TBTM Events...) - the rate card and editorial plan show brands, and
quietly file each price or issue under the right sales title so bookings,
renewals and proposals still match.

Who may edit a brand's rate card and editorial plan: admins and data managers
(everything), plus that brand's own publishers (their SalesRep codes below).
Change the `editors` lists here if the team changes.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.identity import Identity
from app.models import SalesRep, SalesTitle
from app.roles import CAN_USE_AUTOMATIONS


@dataclass(frozen=True)
class Section:
    key: str
    label: str
    hint: str


# Same order as the media packs.
SECTIONS: list[Section] = [
    Section("print", "Print magazine", "Display adverts in the printed and digital magazine - pages, covers, inserts."),
    Section("sponsored", "Sponsored content", "Paid articles, interviews and profiles written with the editorial team."),
    Section("website", "Website", "Banners and placements on the website, usually sold per month."),
    Section("newsletter", "Newsletter & emails", "Newsletter banners and dedicated emails to the database."),
    Section("events", "Events & sponsorship", "Event places and sponsorship packages - dinners, lunches, Connect events."),
    Section("awards", "Awards", "Award entries and award sponsorship."),
    Section("listings", "Directory listings", "Online directory (Finder) listings, usually priced per year."),
    Section("other", "Other", "Anything else - guides, supplements, contract publishing."),
]
SECTION_KEYS = [s.key for s in SECTIONS]


@dataclass(frozen=True)
class Brand:
    key: str
    name: str
    short: str
    website: str
    title_slugs: tuple[str, ...]            # every sales title that belongs to the brand, main one first
    section_title: dict[str, str] = field(default_factory=dict)  # which sales title a section's prices are booked under
    editors: tuple[str, ...] = ()           # SalesRep codes of the brand's publishers

    def title_for_section(self, section: str) -> str:
        return self.section_title.get(section, self.title_slugs[0])


BRANDS: list[Brand] = [
    Brand(
        "obh", "Onboard Hospitality", "OBH", "onboardhospitality.com",
        ("obh", "obh-web", "obh-awards", "obh-forum-asia"),
        {"print": "obh", "sponsored": "obh", "website": "obh-web", "newsletter": "obh-web", "listings": "obh-web",
         "awards": "obh-awards", "events": "obh-forum-asia", "other": "obh"},
        ("SW", "CM"),
    ),
    Brand(
        "tbtm", "The Business Travel Magazine", "TBTM", "thebusinesstravelmag.com",
        ("tbtm", "tbtm-events"),
        {"print": "tbtm", "sponsored": "tbtm", "website": "tbtm", "newsletter": "tbtm", "listings": "tbtm",
         "events": "tbtm-events", "awards": "tbtm-events", "other": "tbtm"},
        ("KH",),
    ),
    Brand(
        "stm", "Selling Travel", "STM", "sellingtravel.co.uk",
        ("selling-travel", "selling-travel-online", "selling-travel-supplements", "selling-travel-guides", "selling-travel-events",
         "stm-connect-events", "travel-for-every-body-awards", "selling-canada", "selling-australia", "visit-usa-planner", "visit-usa-online"),
        {"print": "selling-travel", "sponsored": "selling-travel", "website": "selling-travel-online", "newsletter": "selling-travel-online",
         "listings": "selling-travel-guides", "events": "stm-connect-events", "awards": "travel-for-every-body-awards",
         "other": "selling-travel-supplements"},
        ("SP", "ST", "DW"),
    ),
]
BY_KEY = {b.key: b for b in BRANDS}


def get_brand(key: str) -> Brand | None:
    return BY_KEY.get(key)


def brand_for_title_slug(slug: str) -> Brand | None:
    return next((b for b in BRANDS if slug in b.title_slugs), None)


def brand_titles(db: Session, brand: Brand) -> list[SalesTitle]:
    rows = {t.slug: t for t in db.scalars(select(SalesTitle).where(SalesTitle.slug.in_(brand.title_slugs)))}
    return [rows[s] for s in brand.title_slugs if s in rows]


def title_id_for_section(db: Session, brand: Brand, section: str) -> uuid.UUID | None:
    t = db.scalars(select(SalesTitle).where(SalesTitle.slug == brand.title_for_section(section))).first()
    return t.id if t else None


def my_rep_code(db: Session, identity: Identity) -> str | None:
    uid = identity.user_uuid
    if not uid:
        return None
    rep = db.scalars(select(SalesRep).where(SalesRep.user_id == uid)).first()
    return rep.code if rep else None


def can_edit_brand(db: Session, identity: Identity, brand: Brand) -> bool:
    """Admins and data managers edit every brand; a publisher edits only their own brand."""
    if not identity.is_known or identity.role in CAN_USE_AUTOMATIONS:
        return True
    return my_rep_code(db, identity) in brand.editors
