"""The 2026 prices from BMI's own media packs (sent by Matt Bonner, 6 Oct 2026),
ready to load into the rate card with one click. Everything loads marked
"please check" - a person confirms each price before it's treated as final.

Sources: OBH_Media_2026.pdf, onboardawards.com/cost-to-enter, TBTM-Media-PACK-2026,
Dinner-Club-2026-Media-Kit, NEW STM MEDIA KIT V12, and Matt's email for the
Business Travel People Awards 2027 sponsorship. Only figures that appear in
those documents are here.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RateOffer, SalesRate, SalesTitle
from app.sales.brands import get_brand

SEED_YEAR = 2026


@dataclass
class P:
    section: str
    product: str
    price: float | None
    unit: str = "each"
    price_type: str = "fixed"
    specs: str | None = None
    aliases: list[str] = field(default_factory=list)
    notes: str | None = None
    valid_until: date | None = None
    title: str | None = None  # sales title slug, when not the section's usual one


@dataclass
class O:
    kind: str
    label: str
    details: str | None = None
    rules: dict = field(default_factory=dict)
    section: str | None = None
    products: list[str] = field(default_factory=list)  # product names it applies to
    valid_until: date | None = None


SOURCES = {"obh": "Onboard Hospitality media pack 2026", "tbtm": "TBTM media kit 2026", "stm": "Selling Travel media kit (V12)"}

PRICES: dict[str, list[P]] = {
    "obh": [
        P("print", "Double page", None, price_type="poa", aliases=["DPS", "Double page spread"]),
        P("print", "Full page", 2990, aliases=["FP", "1"]),
        P("print", "Half page", 1600, aliases=["1/2", "HP"]),
        P("print", "Quarter page", 950, aliases=["1/4", "QP"]),
        P("print", "Inside front cover", 3400, aliases=["IFC"]),
        P("print", "Inside back cover", 3200, aliases=["IBC"]),
        P("print", "Outside back cover", 3600, aliases=["OBC"]),
        P("print", "Cover wrap", None, price_type="poa"),
        P("print", "Inserts", None, price_type="poa"),
        P("sponsored", "Advertorial / sponsored content", None, price_type="poa", aliases=["Advertorial"]),
        P("website", "Fireplace", 2000, unit="month", specs="Specs on application"),
        P("website", "Leaderboard", 1000, unit="month", specs="728px x 90px"),
        P("website", "Banner", 400, unit="month", specs="468px x 60px"),
        P("website", "Side banner (large)", 400, unit="month", specs="300px x 400px"),
        P("website", "Side banner (medium)", 250, unit="month", specs="300px x 200px"),
        P("newsletter", "Newsletter banner (Position A)", 750, specs="360px x 120px", notes="Onboard Hospitality Weekly, sent every Monday to 25,000+ readers"),
        P("newsletter", "Newsletter banner (Position B)", 550, specs="360px x 120px"),
        P("newsletter", "Newsletter button (Position C)", 300, specs="170px x 155px"),
        P("listings", "Onboard Finder - standard listing", 300, unit="year", notes="Logo, company name and phone number"),
        P("listings", "Onboard Finder - enhanced listing", 550, unit="year", notes="Adds a dedicated page with banner and 100-word description"),
        P("listings", "Onboard Finder - premium package", 750, unit="year", notes="Adds a slide show, video and testimonials"),
        P("awards", "Award entry (one category)", 480, unit="entry", notes="Onboard Hospitality Awards 2027. Includes a free standard Finder listing (worth £300)."),
        P("awards", "Onboard Experience of the Year entry", 2325, unit="entry", notes="Includes a double-page editorial feature and a year of online exposure"),
    ],
    "tbtm": [
        P("print", "Double page", 4750, aliases=["DPS", "Double page spread"]),
        P("print", "Inside front cover", 2950, aliases=["IFC"]),
        P("print", "Full page", 2850, aliases=["FP", "1"], notes="Or half a double page"),
        P("print", "Half page", 1950, aliases=["1/2", "HP"]),
        P("print", "Quarter page", 1650, aliases=["1/4", "QP"]),
        P("print", "Sixth page", 1250, aliases=["1/6"]),
        P("print", "Full cover wrap (4 pages)", 6500),
        P("print", "Front and outside back cover (2 pages)", 5500),
        P("print", "Front cover (1 page)", 4500),
        P("print", "Bellyband", 5000, specs="10cm deep, wrapped around the magazine", notes="An extra £2,000 fixes the band so the magazine opens at your advert"),
        P("print", "Design service", 250, unit="each", notes="We design the display advert - price per page"),
        P("sponsored", "Sponsored content - double page", 4750),
        P("sponsored", "Sponsored content - full page", 3750),
        P("sponsored", "Guest column", 2250, price_type="from"),
        P("sponsored", "Website-only article", 2500),
        P("sponsored", "Video podcast", 2000, notes="Interview shared on the website and in the newsletter"),
        P("sponsored", "Spotlight on… (short video)", 2000, notes="Showcases a product or service on the website and newsletter"),
        P("website", "Fireplace (high impact)", 2950, unit="month"),
        P("website", "Leaderboard", 1950, unit="month", specs="728px x 90px"),
        P("website", "Large skyscraper (MPU)", 1950, unit="month", specs="300px x 600px"),
        P("website", "Banner or medium skyscraper (MPU)", 1500, unit="month", specs="975px x 125px or 300px x 250px"),
        P("website", "Client whitepaper listing", 2000, notes="Listed for three months, with a news story / download link on the weekly newsletter"),
        P("website", "Whitepaper written by TBTM", None, price_type="poa"),
        P("website", "Sustainability Matters sponsorship", 750, unit="month", notes="Bi-weekly sponsor logo and link; discounts on longer bookings"),
        P("website", "Event promotion package", 5000, notes="Full-page digital advert, 2 dedicated emails, branded registration form, registration data (GDPR), newsletter news story"),
        P("newsletter", "Dedicated email", 1950, notes="Sent to the partner database of 20,000+"),
        P("newsletter", "Newsletter banner or button", 500, unit="week", price_type="from", specs="Banner 600px x 150px, button 300px x 274px", notes="Weekly newsletter every Wednesday; discounts on monthly bookings"),
        P("listings", "Business Travel Finder - standard listing", 295, unit="year"),
        P("listings", "Business Travel Finder - enhanced listing", 975, unit="year", notes="Adds key people, innovations, accreditations and a video"),
        P("events", "Dinner Club sponsorship", 4000, unit="event", notes="The Dorchester. Four non-competing sponsors per dinner; two places, preferred seating, logo branding and photo coverage"),
        P("events", "Lunch Forum sponsorship", 2450, unit="event", notes="Maximum six sponsors per lunch; double-page write-up in the magazine"),
        P("events", "Lunch Forum - single partner", 9000, unit="event"),
        P("awards", "People Awards 2027 - Gold sponsorship", 20000, valid_until=date(2027, 2, 1), notes="Early bird price"),
        P("awards", "People Awards 2027 - Silver sponsorship", 12000, valid_until=date(2027, 2, 1), notes="Early bird price"),
        P("awards", "People Awards 2027 - Bronze sponsorship", 5000, valid_until=date(2027, 2, 1), notes="Early bird price"),
        P("awards", "People Awards 2027 - Sapphire (build your own)", 10000, valid_until=date(2027, 2, 1), notes="Early bird price"),
    ],
    "stm": [
        P("print", "Cover wrap (4 pages)", 11380),
        P("print", "5 pages", 10875),
        P("print", "4 pages", 9415),
        P("print", "3 pages", 7795),
        P("print", "Double-page spread", 5995, aliases=["DPS", "Double page"]),
        P("print", "Full page", 3750, aliases=["FP", "1"]),
        P("print", "Half page", 2065, aliases=["1/2", "HP"]),
        P("print", "Quarter page", 1135, aliases=["1/4", "QP"]),
        P("print", "Eighth page", 625, aliases=["1/8"]),
        P("print", "Wraparound cover band", 4150),
        P("print", "Loose inserts", 495, price_type="from"),
        P("website", "Hub", 9500, price_type="from", title="selling-travel-guides"),
        P("website", "Fireplace", 3000, unit="month"),
        P("website", "Digital itinerary", 2250),
        P("website", "Immersive article", 1995),
        P("website", "Banner", 500, unit="month"),
        P("newsletter", "Newsletter banner", 500, notes="Weekly newsletter every Thursday to 25,000+ subscribers"),
        P("newsletter", "Dedicated email", 1500, notes="Sent to 16,000+ recipients"),
        P("events", "Connect event - London", 1295, unit="event"),
        P("events", "Connect event - outside London", 1095, unit="event"),
        P("events", "Connect event sponsorship", 1800, unit="event"),
        P("events", "Dedicated Connect event", 9500, unit="event", price_type="from"),
        P("awards", "Travel For Every Body Awards - Associate Partner", 1450),
        P("awards", "Travel For Every Body Awards - Silver", 4500),
        P("awards", "Travel For Every Body Awards - Gold", 9500),
        P("awards", "Travel For Every Body Awards - Headline", 19950),
        P("other", "Guides, supplements and contract publishing", None, price_type="poa"),
    ],
}

OFFERS: dict[str, list[O]] = {
    "obh": [
        O("series", "Enter more categories, pay less per entry", "1 entry £480, 2 £940, 3 £1,380, 4 £1,800, 5 £2,200, 6 £2,580, 7 £2,940, 8 £3,280, 9 £3,645, 10 £4,000. More than 10: ask Sue Williams.",
          {"tiers": [{"qty": 2, "total": 940}, {"qty": 3, "total": 1380}, {"qty": 4, "total": 1800}, {"qty": 5, "total": 2200}, {"qty": 6, "total": 2580},
                     {"qty": 7, "total": 2940}, {"qty": 8, "total": 3280}, {"qty": 9, "total": 3645}, {"qty": 10, "total": 4000}]},
          section="awards", products=["Award entry (one category)"]),
    ],
    "tbtm": [
        O("volume", "Book 2 adverts save 10%, 3 save 20%, 4 save 30%", "A full page then works out at £1,995 per advert.",
          {"tiers": [{"qty": 2, "discount_pct": 10}, {"qty": 3, "discount_pct": 20}, {"qty": 4, "discount_pct": 30}]}, section="print"),
        O("series", "Two or more dedicated emails: £1,750 each", None, {"tiers": [{"qty": 2, "unit_price": 1750}]}, section="newsletter", products=["Dedicated email"]),
        O("series", "Dinner Club: book more dinners, pay less per dinner", "2 dinners £3,750 each, 3 £3,500 each, all 4 £3,250 each.",
          {"tiers": [{"qty": 2, "unit_price": 3750}, {"qty": 3, "unit_price": 3500}, {"qty": 4, "unit_price": 3250}]}, section="events", products=["Dinner Club sponsorship"]),
        O("early_bird", "People Awards 2027 early-bird sponsorship prices", "Gold, Silver, Bronze and Sapphire prices are early-bird prices, valid until 1 February.",
          section="awards", valid_until=date(2027, 2, 1)),
        O("note", "Newsletter: discounts on monthly bookings", "Ask the publisher for the monthly rate.", section="newsletter"),
    ],
    "stm": [],
}


def seed_available(db: Session, brand_key: str, year: int) -> int:
    """How many prices the media-pack loader would add (0 if not for this year or already loaded)."""
    if year != SEED_YEAR or brand_key not in PRICES:
        return 0
    brand = get_brand(brand_key)
    title_ids = list(db.scalars(select(SalesTitle.id).where(SalesTitle.slug.in_(brand.title_slugs))))
    existing = db.scalar(select(SalesRate.id).where(SalesRate.title_id.in_(title_ids), SalesRate.year == year).limit(1)) if title_ids else None
    return 0 if existing else len(PRICES[brand_key])


def load_seed(db: Session, brand_key: str, year: int = SEED_YEAR) -> int:
    """Adds the media-pack prices and offers for a brand (skipping any product already there). Returns how many prices were added."""
    if year != SEED_YEAR or brand_key not in PRICES:
        return 0
    brand = get_brand(brand_key)
    titles = {t.slug: t for t in db.scalars(select(SalesTitle).where(SalesTitle.slug.in_(brand.title_slugs)))}
    added: dict[str, uuid.UUID] = {}
    order: dict[str, int] = {}
    for p in PRICES[brand_key]:
        t = titles.get(p.title or brand.title_for_section(p.section))
        if not t:
            continue
        if db.scalar(select(SalesRate.id).where(SalesRate.title_id == t.id, SalesRate.year == year, SalesRate.section == p.section, SalesRate.product == p.product)):
            continue
        order[p.section] = order.get(p.section, 0) + 1
        r = SalesRate(id=uuid.uuid4(), title_id=t.id, year=year, section=p.section, product=p.product, price_type=p.price_type,
                      price_gbp=p.price, unit=p.unit, specs=p.specs, aliases=p.aliases, notes=p.notes, valid_until=p.valid_until,
                      sort_order=order[p.section] * 10, needs_check=True, source=SOURCES[brand_key])
        db.add(r)
        added[p.product] = r.id
    db.flush()
    if added and not db.scalar(select(RateOffer.id).where(RateOffer.brand == brand_key, RateOffer.year == year).limit(1)):
        for i, o in enumerate(OFFERS.get(brand_key, [])):
            db.add(RateOffer(id=uuid.uuid4(), brand=brand_key, year=year, kind=o.kind, label=o.label, details=o.details, rules=o.rules,
                             section=o.section, rate_ids=[str(added[n]) for n in o.products if n in added], valid_until=o.valid_until,
                             sort_order=(i + 1) * 10, needs_check=True))
    return len(added)
