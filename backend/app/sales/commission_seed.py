"""BMI's commission structure as Matt sent it (Oct 2026), ready to load with one
button on the commission plans page. Titles are the order register's slugs
(app/sales/reference.py); where the note didn't name a title, the choice is
written in the rule's notes so a manager can see it and change it.
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CommissionRule, SalesRep

STM = ["selling-travel", "selling-travel-online"]
GUIDES = ["selling-travel-supplements", "selling-travel-guides", "visit-usa-planner", "selling-canada"]
OBH = ["obh", "obh-web", "obh-awards", "obh-forum-asia"]
DW_CHANGE = date(2027, 6, 1)

PLANS: dict[str, list[dict]] = {
    "SP": [
        dict(name="Selling Travel Magazine (print and digital)", titles=STM, base=0.055, nb=0.02),
        dict(name="Guides and supplements", titles=GUIDES, base=0.025, nb=0.02, guide_bonus=200,
             notes="Includes Visit USA Travel Planner, Selling Canada and Guide to the Caribbean (recorded under Selling Travel Supplements)."),
        dict(name="Guide newsletters", titles=["visit-usa-online"], base=0.025, nb=0.02, threshold_bonus=200, threshold=8000,
             notes="£200 for each newsletter whose revenue passes £8,000 in a calendar year. Add the Selling Canada newsletter's title here once it has one."),
    ],
    "ST": [
        dict(name="Selling Travel Magazine (print and digital)", titles=STM, base=0.05, nb=0.02),
        dict(name="Guides and supplements (contract publishing)", titles=GUIDES, base=0.02, nb=0.02, guide_bonus=200),
        dict(name="Events (Selling Travel Connect)", titles=["stm-connect-events", "selling-travel-events"], base=0.05, nb=0.02),
    ],
    "DW": [
        dict(name="Selling Travel Magazine (print and digital)", titles=STM, base=0.05, nb=0.05, nb_after=0.02, nb_change=DW_CHANGE),
        dict(name="Selling Australia", titles=["selling-australia"], base=0.05, nb=0.05, nb_after=0.02, nb_change=DW_CHANGE),
        dict(name="Travel For Every Body Awards", titles=["travel-for-every-body-awards"], base=0.05, nb=0.05, nb_after=0.02, nb_change=DW_CHANGE),
        dict(name="Guides and supplements (contract publishing)", titles=GUIDES, base=0.02, nb=0.02, guide_bonus=200),
    ],
    "CM": [dict(name="Onboard Hospitality and the Onboard Awards", titles=OBH, base=0.05, nb=0.02)],
    "SW": [dict(name="Onboard Hospitality and the Onboard Awards", titles=OBH, base=0.175, nb=0)],
    "KH": [
        dict(name="The Business Travel Magazine (print and digital)", titles=["tbtm"], base=0.05, nb=0.02, client_bonus=100),
        dict(name="Events (Dinner Club, Lunch Forum, Business Travel Quiz)", titles=["tbtm-events"], base=0.02, nb=0, event_profit=0.10),
    ],
}


def plan_count(db: Session) -> int:
    return len(db.scalars(select(CommissionRule.id)).all())


def load_structure(db: Session, *, replace: bool = False) -> int:
    """Creates every rule above (for salespeople that exist). With replace, existing rules for those people go first."""
    reps = {r.code: r for r in db.scalars(select(SalesRep))}
    n = 0
    for code, rules in PLANS.items():
        rep = reps.get(code)
        if not rep:
            continue
        existing = db.scalars(select(CommissionRule).where(CommissionRule.rep_id == rep.id)).all()
        if existing and not replace:
            continue
        for r in existing:
            db.delete(r)
        for i, d in enumerate(rules):
            db.add(CommissionRule(
                id=uuid.uuid4(), rep_id=rep.id, name=d["name"], title_slugs=d["titles"], base_rate=d["base"], new_business_rate=d["nb"],
                new_business_rate_after=d.get("nb_after"), new_business_rate_change_on=d.get("nb_change"),
                new_guide_bonus_gbp=d.get("guide_bonus"), threshold_bonus_gbp=d.get("threshold_bonus"), threshold_gbp=d.get("threshold"),
                new_client_bonus_gbp=d.get("client_bonus"), event_profit_rate=d.get("event_profit"), notes=d.get("notes"), sort_order=i))
            n += 1
    db.flush()
    return n
