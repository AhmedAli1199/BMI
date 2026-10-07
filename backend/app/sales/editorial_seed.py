"""BMI's 2026 editorial plan as published (Onboard Hospitality 2026 features page,
TBTM 2026 forward features list and media kit, Dinner Club media kit), ready to
load into the editorial plan with one click. Dates the sources only give as a
month (TBTM issues) are set to the 1st and marked "please check"; nothing else is
guessed. Selling Travel's features list couldn't be read, so it has none yet.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EditionFeature, EditorialSetting, SalesEdition, SalesTitle
from app.sales.brands import get_brand
from app.sales.editorial import compute_deadlines

SEED_YEAR = 2026


@dataclass
class I:
    title: str          # sales title slug
    name: str
    kind: str           # issue | event | awards | guide
    fmt: str            # print_digital | print | digital | event | awards
    pub: date
    period: str | None = None
    editorial: date | None = None
    ad: date | None = None
    copy: date | None = None
    theme: str | None = None
    distribution: str | None = None
    features: list[str] = field(default_factory=list)
    milestones: list[dict] = field(default_factory=list)
    estimated: bool = False  # date known only to the month
    year: int = SEED_YEAR


def _f(text: str) -> list[str]:
    return [x.strip() for x in text.split(";") if x.strip()]


SETTINGS = {
    "obh": {
        "about": "Quarterly magazine, published to coincide with the industry's key trade shows and sent to 25,000+ decision-makers, "
                 "key purchasers and suppliers of inflight, rail and cruise hospitality.",
        "deadline_rules": [
            {"key": "editorial", "label": "Editorial deadline", "kind": "days_before", "value": 28},
            {"key": "advertising", "label": "Advertising deadline", "kind": "days_before", "value": 9},
        ],
        "regular_sections": [{"name": n, "description": d} for n, d in (
            ("Food & Beverage", "Every issue"), ("Design & Innovation", "Every issue"), ("Wellbeing", "Every issue"), ("Retail", "Every issue"),
            ("People", "Every issue"), ("Technology", "Every issue"), ("Accessibility", "Part of our Travel For Every Body campaign"))],
    },
    "tbtm": {
        "about": "Quarterly print and digital magazine (March, June, September, December), digital specials, a weekly newsletter "
                 "and year-round events.",
        "deadline_rules": [
            {"key": "copy", "label": "Copy & artwork deadline", "kind": "day_prev_month", "value": 25},
            {"key": "sponsored", "label": "Sponsored content deadline", "kind": "day_prev_month", "value": 18},
        ],
        "regular_sections": [{"name": n, "description": d} for n, d in (
            ("The Conversation", "Interview with a senior business travel industry figure"), ("Opening Shots", "Picture-led feature on what's new"),
            ("Take Five", "Experts share five insights on a specific topic"), ("Everyone's Talking about…", "Soundbites on a current issue"),
            ("One to Watch", "A notable newcomer to the sector"), ("According to Clive", "Column from BTA CEO Clive Wratten"),
            ("Diary of a CTO", "Column from TripStax CTO Scott Wylie"), ("Six of the Best…", "Hotels, venues, business class seats etc."),
            ("On the Move", "The latest business travel appointments"), ("Events", "Key industry dates"),
            ("Ask the Expert", "Top tips for travel managers and arrangers"), ("Talking Travel", "A well-known personality on their travel"),
            ("Speaking Out", "Industry professionals air their views"), ("Scott says", "Update from ITM CEO Scott Davies"),
            ("On business in…", "Guides to key business destinations"), ("Focus on…", "In-depth guide to doing business in a city or region"),
            ("Meeting in…", "Meeting and event venues in a destination"), ("Gadgets and Gear", "Products for the business traveller"),
            ("Reality Check", "First-hand reviews of hotels, flights, rail, tech"), ("The Final Word", "The quirky side of travel"))],
    },
    "stm": {
        "about": "Print and interactive digital magazine, 5 issues a year.",
        "deadline_rules": [],
        "regular_sections": [],
    },
}

ISSUES: dict[str, list[I]] = {
    "obh": [
        I("obh", "105", "issue", "print_digital", date(2026, 3, 19), "March, April, May", date(2026, 2, 16), date(2026, 3, 10),
          distribution="WTCE / AIX 2026, Hamburg", theme="AIX / WTCE preview",
          features=_f("AIX/WTCE preview; OBH Awards; European F&B trends; Premium drinks; Inflight bloating; Sweet snacks and ice creams; Glassware design; "
                      "Inspired by nature; Sustainable amenity kits; Inflight skin care; Charitable connections; Future of inflight entertainment; "
                      "AI kids stories; Payment options; Retail fraud; Focus on retail trends; Live sports (FIFA World Cup)")),
        I("obh", "106", "issue", "print_digital", date(2026, 6, 11), "June, July, August", date(2026, 5, 18), date(2026, 6, 2),
          theme="Onboard Hospitality Award winners",
          features=_f("Onboard Hospitality Award winners; WTCE review; Kitchen innovations; Seafood; Welcome snacks; Cruise chef collaborations; "
                      "Non-alcoholic beverages; Kids concepts; Trolleys; Onboard advertising; Wellness menus; Pyjamas and socks; "
                      "Allergens and special meals; Headset innovations; Inflight charging")),
        I("obh", "107", "issue", "print_digital", date(2026, 8, 13), "September, October, November", date(2026, 7, 16), date(2026, 8, 3),
          distribution="IFSA Global Expo, Dallas", theme="IFSA Dallas and FTE/APEX Singapore previews",
          features=_f("Previews of IFSA in Dallas (September) and FTE/APEX in Singapore (November); OBH Awards 2027 entries open; US food trends; "
                      "Lounge catering; Cocktails; Sous vide; Packaging for retail success; Onboard delivery; Top sellers; Onboard textiles; "
                      "Jetlag solutions; Onboard rail apps; Cruise connectivity; Offer personalisation; IFE audio selection and podcasts")),
        I("obh", "108", "issue", "print_digital", date(2026, 12, 10), "December, January, February", date(2026, 11, 16), date(2026, 12, 2),
          theme="IFSA review",
          features=_f("IFSA review; Catering Asia Pacific; Disposable cutlery; Napkins; Inflight sales; Branded purchases; Face creams; Eye masks; "
                      "Toilets in focus; Cabin lighting innovations; Accessibility in action; Airline apps; Revenue from onboard sales; Safety videos")),
        I("obh-awards", "Onboard Hospitality Awards 2027", "awards", "awards", date(2027, 4, 6), distribution="Hamburg, Germany",
          theme="Awards ceremony", year=2027),
    ],
    "tbtm": [
        I("tbtm", "Guide to Serviced Accommodation 2026", "guide", "print", date(2026, 2, 1), "February", estimated=True,
          theme="The 2026 Guide to Serviced Accommodation"),
        I("tbtm", "Spring issue", "issue", "print_digital", date(2026, 3, 1), "March / April", estimated=True,
          theme="Sustainability, duty of care and DE&I - how suppliers across all sectors are meeting corporates' ESG needs",
          features=_f("How to choose the most responsible suppliers; The latest developments in Sustainable Aviation Fuel (SAF); "
                      "Does sustainable business travel cost more?; Booking European and UK domestic rail; 10 top tips for travel risk management; "
                      "The art of science in influencing traveller behaviour; Neuro-diversity in business travel; "
                      "How to get the most from your accommodation programme; Car rental focus; 2026 Business Travel People Awards judges revealed; "
                      "The 2026 Guide to Serviced Accommodation (print)")),
        I("tbtm", "Sustainability Movers and Shakers 2026", "issue", "digital", date(2026, 5, 1), "May", estimated=True,
          theme="Who is making the biggest impact in sustainability",
          features=_f("Case studies from organisations leading the way on sustainable business travel; Interviews with travel sustainability leaders")),
        I("tbtm", "Summer issue", "issue", "print_digital", date(2026, 6, 1), "June / July", estimated=True,
          theme="How TMCs and technology providers are responding to the changing needs of corporates",
          features=_f("TMC/tech consolidation and what it means for you; The changing role of the TMC; How to make best use of your data; "
                      "The growing impact of AI in business travel; Bots versus humans - finding the right balance; Managing meetings and events; "
                      "Entries open for the 2026 Tech Hotlist; Our latest TMC directory; 10 top tips for RFPs; "
                      "2026 Business Travel People Awards shortlist; Adapting programmes and policies to new ways of working")),
        I("tbtm", "Autumn issue", "issue", "print_digital", date(2026, 9, 1), "September / October", estimated=True,
          theme="Tech Hotlist 2026 - the innovators shaking up business travel. Plus business travel for SMEs",
          features=_f("Tech Hotlist 2026; SME market overview; Finding the right tech partners; Agentic AI and what it means for you; "
                      "Getting to grips with payments; Managing travel and expense; Focus on online booking tools; Our latest tech directory; "
                      "10 top tips for policy compliance; How to manage loyalty schemes")),
        I("tbtm", "Top business travel trends for 2027", "issue", "digital", date(2026, 11, 1), "November", estimated=True,
          theme="Experts across all sectors on the key trends for 2027"),
        I("tbtm", "Winter issue", "issue", "print_digital", date(2026, 12, 1), "December / January", estimated=True,
          theme="The latest developments in air travel, and how to navigate major changes in distribution",
          features=_f("Premium air travel; Focus on long haul; Private jets; Booking low-cost carriers; Fare forecasts; Getting to grips with NDC; "
                      "The road to sustainable aviation; Managing taxis, transfers and chauffeur services; Six of the best airport lounges; "
                      "10 top tips for traveller wellbeing; Focus on budget hotels; Business Travel People Awards 2027 categories unveiled")),
        I("tbtm-events", "Dinner Club - March", "event", "event", date(2026, 3, 10), distribution="The Dorchester, London"),
        I("tbtm-events", "Lunch Forum - Ground Transport / Ancillaries", "event", "event", date(2026, 4, 2)),
        I("tbtm-events", "Lunch Forum - Accommodation", "event", "event", date(2026, 5, 21)),
        I("tbtm-events", "Dinner Club - June", "event", "event", date(2026, 6, 9), distribution="The Dorchester, London"),
        I("tbtm-events", "Lunch Forum - Air", "event", "event", date(2026, 7, 9)),
        I("tbtm-events", "Business Travel People Awards 2026", "awards", "awards", date(2026, 9, 15), distribution="Grand Connaught Rooms, London",
          theme="Awards ceremony"),
        I("tbtm-events", "Lunch Forum - Technology", "event", "event", date(2026, 10, 7)),
        I("tbtm-events", "Dinner Club - October", "event", "event", date(2026, 10, 22), distribution="The Dorchester, London"),
        I("tbtm-events", "Dinner Club - December", "event", "event", date(2026, 12, 1), distribution="The Dorchester, London"),
    ],
    "stm": [],
}


def _brand_editions(db: Session, brand_key: str, year: int) -> list[SalesEdition]:
    brand = get_brand(brand_key)
    ids = list(db.scalars(select(SalesTitle.id).where(SalesTitle.slug.in_(brand.title_slugs))))
    return list(db.scalars(select(SalesEdition).where(SalesEdition.title_id.in_(ids), SalesEdition.year == year))) if ids else []


def seed_available(db: Session, brand_key: str, year: int) -> int:
    items = [i for i in ISSUES.get(brand_key, []) if i.year == year]
    if year != SEED_YEAR or not items:
        return 0
    eds = _brand_editions(db, brand_key, year)
    planned = [e for e in eds if e.editorial_deadline or e.ad_deadline or e.copy_deadline or e.theme]
    if planned or (eds and db.scalar(select(EditionFeature.id).where(EditionFeature.edition_id.in_([e.id for e in eds])).limit(1))):
        return 0
    return len(items)


def _find(db: Session, title_id, year: int, item: I) -> SalesEdition | None:
    eds = list(db.scalars(select(SalesEdition).where(SalesEdition.title_id == title_id, SalesEdition.year == year)))
    same = next((e for e in eds if e.name.strip().lower() == item.name.lower()), None)
    if same or item.kind not in ("issue", "guide"):
        return same
    # An issue the order register already has under its own name, published the same month.
    return next((e for e in eds if e.kind == item.kind and e.edition_date and e.edition_date.month == item.pub.month
                 and e.edition_date.year == item.pub.year), None)


def load_seed(db: Session, brand_key: str, year: int = SEED_YEAR) -> dict:
    """Fills the brand's plan: settings (if empty), then each issue - matched to an edition the order
    register already has, or created. Only empty fields are filled; features only if the issue has none."""
    if year != SEED_YEAR or brand_key not in ISSUES:
        return {"issues": 0, "features": 0}
    cfg = SETTINGS.get(brand_key)
    st = db.get(EditorialSetting, brand_key)
    if cfg and (st is None or (not st.deadline_rules and not st.regular_sections)):
        if st is None:
            st = EditorialSetting(brand=brand_key)
            db.add(st)
        st.deadline_rules, st.regular_sections, st.about = cfg["deadline_rules"], cfg["regular_sections"], cfg["about"]
    rules = (st.deadline_rules if st else []) or []
    titles = {t.slug: t for t in db.scalars(select(SalesTitle))}
    n_issues = n_features = 0
    for item in ISSUES[brand_key]:
        t = titles.get(item.title)
        if not t:
            continue
        ed = _find(db, t.id, item.year, item)
        if ed is None:
            ed = SalesEdition(id=uuid.uuid4(), title_id=t.id, year=item.year, name=item.name, kind=item.kind, status="open",
                              edition_date=item.pub, date_set_in_plan=True)
            db.add(ed)
            db.flush()
        elif ed.edition_date is None or not item.estimated:
            ed.edition_date, ed.date_set_in_plan = item.pub, True
        auto = compute_deadlines(rules, ed.edition_date) if ed.edition_date and item.kind in ("issue", "guide") else {}
        ed.period_label = ed.period_label or item.period
        ed.editorial_deadline = ed.editorial_deadline or item.editorial or auto.get("editorial")
        ed.ad_deadline = ed.ad_deadline or item.ad or auto.get("advertising")
        ed.copy_deadline = ed.copy_deadline or item.copy or auto.get("copy")
        if not ed.milestones:
            extra = [{"label": r["label"], "date": auto[r["key"]].isoformat()} for r in rules
                     if r["key"] not in ("editorial", "advertising", "copy") and auto.get(r["key"])]
            ed.milestones = item.milestones + extra
        ed.theme = ed.theme or item.theme
        ed.distribution = ed.distribution or item.distribution
        ed.format = ed.format or item.fmt
        ed.plan_needs_check = ed.plan_needs_check or item.estimated or bool(auto)
        n_issues += 1
        if item.features and not db.scalar(select(EditionFeature.id).where(EditionFeature.edition_id == ed.id).limit(1)):
            for i, ft in enumerate(item.features):
                db.add(EditionFeature(id=uuid.uuid4(), edition_id=ed.id, title=ft[:300], sort_order=(i + 1) * 10))
                n_features += 1
    db.flush()
    return {"issues": n_issues, "features": n_features}
