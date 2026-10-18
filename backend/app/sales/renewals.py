"""What a renewal email (SALES-021) needs to know about one advertiser,
beyond the booking itself: where their previous ad can be seen online,
this year's price for the same product, whether they've rebooked since,
which rep owns them and who at the company to write to.

Every lookup here answers "unknown" rather than guessing - a missing
price or link is flagged on the review card, never invented.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Company, Contact, Email, SalesEdition, SalesOrder, SalesRate, SalesRep, SalesTitle
from app.sales.analytics import BOOKED, edition_date_expr, period_bounds
from app.sales.matching import normalise

_SIZE_ALIASES = {
    "fp": "full page", "page": "full page", "1": "full page", "full page": "full page", "1 page": "full page",
    "dps": "double page spread", "double page": "double page spread", "double page spread": "double page spread",
    "0.5": "half page", "1/2": "half page", "1/2 page": "half page", "half page": "half page", "hp": "half page",
    "0.25": "quarter page", "1/4": "quarter page", "1/4 page": "quarter page", "quarter page": "quarter page", "qp": "quarter page",
}


def product_key(size: str | None) -> str | None:
    """"FP", "1", "Full page" -> "full page", so the rate card and the
    sheets can each use their own shorthand and still match."""
    if not size or not size.strip():
        return None
    s = re.sub(r"\s+", " ", size.strip().lower())
    return _SIZE_ALIASES.get(s, s)


def page_number(order: SalesOrder) -> int | None:
    """The page the ad ran on, when the sheet recorded one: the "Page
    number" column, or a position like "p. 23" / "23". Anything vaguer
    ("first right", "inside back cover") isn't a page number."""
    raw = (order.extra or {}).get("Page number") or order.position
    if raw is None:
        return None
    m = re.fullmatch(r"\s*(?:p(?:age)?\.?\s*)?(\d{1,3})\s*", str(raw), flags=re.IGNORECASE)
    return int(m.group(1)) if m else None


@dataclass
class PlacementLink:
    url: str | None
    level: str | None  # "page" (their own ad) | "issue" (the whole edition) | None

    @property
    def note(self) -> str:
        if self.level == "page":
            return "Links to their ad"
        if self.level == "issue":
            return "Links to the issue (their page isn't known)"
        return "No online link set up for this title"


def _fill(template: str, edition: SalesEdition, page: int | None) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", edition.name.lower()).strip("-")
    return (template.replace("{edition}", slug).replace("{year}", str(edition.year))
            .replace("{page}", str(page) if page else ""))


def placement_link(title: SalesTitle, edition: SalesEdition, order: SalesOrder) -> PlacementLink:
    page = page_number(order)
    if title.digital_page_url and page:
        return PlacementLink(_fill(title.digital_page_url, edition, page), "page")
    if edition.digital_url:
        return PlacementLink(edition.digital_url, "issue")
    if title.digital_issue_url:
        return PlacementLink(_fill(title.digital_issue_url, edition, None), "issue")
    return PlacementLink(None, None)


def current_price(db: Session, title_id: uuid.UUID, year: int, size: str | None) -> SalesRate | None:
    key = product_key(size)
    if not key:
        return None
    for rate in db.scalars(select(SalesRate).where(SalesRate.title_id == title_id, SalesRate.year == year, SalesRate.archived.is_(False),
                                                   SalesRate.price_gbp.isnot(None)).order_by(SalesRate.section, SalesRate.sort_order)):
        # The rate card's own name, or any shorthand it lists under "also called" ("FP", "1/2").
        if product_key(rate.product) == key or any(product_key(a) == key for a in (rate.aliases or [])):
            return rate
    return None


# A booking taken this long after its issue came out is almost always a typing slip or a booking put in the wrong issue.
LATE_BOOKING_DAYS = 60


def in_period(year: int, financial: bool = False, start_month: int = 7):
    """SQL filter for the editions of a renewals year: calendar years by the edition's year, financial years by its date
    (the same rule as the sales overview)."""
    if not financial:
        return SalesEdition.year == year
    lo, hi = period_bounds(year, True, start_month)
    return edition_date_expr().between(lo, hi)


def date_problem(booked_on: date | None, edition_date: date | None, today: date | None = None) -> str | None:
    """Plain words when a booking date can't be right - in the future, or long after its issue came out."""
    today = today or date.today()
    if not booked_on:
        return None
    if booked_on > today + timedelta(days=1):
        return f"Booked date {booked_on:%d %b %Y} is in the future - probably a typing slip."
    if edition_date and booked_on > edition_date + timedelta(days=LATE_BOOKING_DAYS):
        return f"Booked on {booked_on:%d %b %Y}, after the issue came out ({edition_date:%d %b %Y}) - is it in the right issue?"
    return None


def rebooked_rows(db: Session, title_id: uuid.UUID, year: int, financial: bool = False, start_month: int = 7,
                  today: date | None = None) -> list[tuple[str, uuid.UUID | None]]:
    """(client name, company) of everyone who counts as "back" this year: booked into one of this year's editions,
    or took a booking with this title during this year (whatever issue it went into - if they gave us money this
    year, a renewal email would be wrong). Booking dates in the future don't count."""
    today = today or date.today()
    lo, hi = period_bounds(year, financial, start_month)
    in_year = db.execute(
        select(SalesOrder.client_name, SalesOrder.company_id).join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
        .where(SalesEdition.title_id == title_id, in_period(year, financial, start_month), SalesOrder.status == BOOKED)).all()
    taken = db.execute(
        select(SalesOrder.client_name, SalesOrder.company_id).join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
        .where(SalesEdition.title_id == title_id, SalesOrder.status == BOOKED,
               SalesOrder.booked_on >= lo, SalesOrder.booked_on <= min(hi, today))).all()
    return [(n, c) for n, c in [*in_year, *taken]]


def rebooked(db: Session, title_id: uuid.UUID, year: int, client_name: str, company_id: uuid.UUID | None,
             financial: bool = False, start_month: int = 7) -> bool:
    """Booked this title again in `year` already - checked when the item is
    queued *and* again when someone approves or sends it, since the order
    register is the source of truth and may have changed in between."""
    rows = rebooked_rows(db, title_id, year, financial, start_month)
    key = normalise(client_name) or client_name.strip().lower()
    return any((normalise(n) or n.strip().lower()) == key or (company_id and c == company_id) for n, c in rows)


def owner_user_id(db: Session, order: SalesOrder) -> uuid.UUID | None:
    """The rep who sold it last time (if their login is linked), else the
    CRM company's owner."""
    if order.rep_id:
        rep = db.get(SalesRep, order.rep_id)
        if rep and rep.user_id:
            return rep.user_id
    if order.company_id:
        company = db.get(Company, order.company_id)
        if company and company.owner_user_id:
            return company.owner_user_id
    return None


def best_recipient(db: Session, company_id: uuid.UUID | None) -> tuple[str, str] | None:
    """(email, name) of the most likely person to write to at the company -
    a contact with a working email, most recently updated first. The rep
    can change it before sending."""
    if not company_id:
        return None
    email = (select(Email.address).where(Email.contact_id == Contact.id)
             .order_by(Email.is_primary.desc()).limit(1).correlate(Contact).scalar_subquery())
    row = db.execute(
        select(email, Contact.full_name)
        .where(Contact.company_id == company_id,
               func.coalesce(Contact.is_unsubscribed, False).is_(False),
               func.coalesce(Contact.has_bounced, False).is_(False),
               Contact.has_left.is_(False))
        .where(email.isnot(None))
        .order_by(Contact.updated_at.desc().nulls_last())
        .limit(1)
    ).first()
    return (row[0], row[1] or "") if row else None
