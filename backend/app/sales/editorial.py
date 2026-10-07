"""Editorial-plan helpers shared by the API, the seed and the deadline reminders.

Deadline rules (per brand, EditorialSetting.deadline_rules) say how a deadline is
usually worked out from the publication date:
  {"kind": "days_before", "value": 9}       -> 9 days before publication
  {"kind": "day_prev_month", "value": 25}   -> the 25th of the month before publication
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

STANDARD = {"editorial": "editorial_deadline", "advertising": "ad_deadline", "copy": "copy_deadline"}
STANDARD_LABELS = {"editorial": "Editorial deadline", "advertising": "Advertising deadline", "copy": "Copy & artwork deadline"}


def rule_date(rule: dict, pub: date) -> date | None:
    try:
        v = int(rule.get("value"))
    except (TypeError, ValueError):
        return None
    if rule.get("kind") == "days_before":
        return pub - timedelta(days=v)
    if rule.get("kind") == "day_prev_month":
        y, m = (pub.year, pub.month - 1) if pub.month > 1 else (pub.year - 1, 12)
        return date(y, m, min(max(v, 1), calendar.monthrange(y, m)[1]))
    return None


def compute_deadlines(rules: list[dict], pub: date | None) -> dict[str, date]:
    if not pub:
        return {}
    out = {}
    for r in rules or []:
        d = rule_date(r, pub)
        if d and r.get("key"):
            out[r["key"]] = d
    return out


def describe_rule(rule: dict) -> str:
    v = rule.get("value")
    if rule.get("kind") == "days_before":
        return f"{v} days before publication"
    if rule.get("kind") == "day_prev_month":
        suffix = "th" if 10 <= int(v) % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(int(v) % 10, "th")
        return f"{v}{suffix} of the month before publication"
    return ""


def shift_year(d: date | None) -> date | None:
    """Same weekday a year on - whichever of +52 or +53 weeks lands closer to the same day of the month."""
    if not d:
        return None
    a, b = d + timedelta(weeks=52), d + timedelta(weeks=53)
    try:
        target = d.replace(year=d.year + 1)
    except ValueError:
        target = d.replace(year=d.year + 1, day=28)
    return min((a, b), key=lambda x: abs((x - target).days))


# ---- issue facts for proposals, renewals and reminders ----------------------------------------

def fmt_day(d: date | None) -> str:
    return f"{d:%A} {d.day} {d:%B %Y}" if d else ""


def issue_label(e) -> str:
    return f"Issue {e.name}" if str(e.name).strip().isdigit() else e.name


def next_issue(db, title_id, today: date | None = None, kinds=("issue", "guide", "event", "awards")):
    """The title's next issue/event that is still open for bookings (advertising deadline, or failing that
    the publication date, not yet passed)."""
    from sqlalchemy import or_, select

    from app.models import SalesEdition
    today = today or date.today()
    return db.scalars(
        select(SalesEdition).where(SalesEdition.title_id == title_id, SalesEdition.kind.in_(kinds), SalesEdition.edition_date.isnot(None),
                                   or_(SalesEdition.ad_deadline >= today, (SalesEdition.ad_deadline.is_(None)) & (SalesEdition.edition_date >= today)))
        .order_by(SalesEdition.edition_date)
    ).first()


def issue_facts(db, e) -> dict:
    """What a proposal or renewal email may say about an issue - straight from the editorial plan."""
    from sqlalchemy import select

    from app.models import EditionFeature
    feats = list(db.scalars(select(EditionFeature).where(EditionFeature.edition_id == e.id, EditionFeature.status != "dropped")
                            .order_by(EditionFeature.sort_order)))
    sponsorable = [f.title for f in feats if f.sponsorable]
    return {
        "id": str(e.id), "label": issue_label(e), "name": e.name, "kind": e.kind, "publication": e.edition_date.isoformat() if e.edition_date else None,
        "publication_text": fmt_day(e.edition_date), "ad_deadline": e.ad_deadline.isoformat() if e.ad_deadline else None,
        "ad_deadline_text": fmt_day(e.ad_deadline), "theme": e.theme, "distribution": e.distribution, "period": e.period_label,
        "features": [f.title for f in feats][:12], "sponsorable": sponsorable[:6],
    }


def issue_sentence(f: dict) -> str:
    """"Issue 106 publishes on Thursday 11 June 2026 (advertising deadline Tuesday 2 June 2026)." """
    verb = "publishes on" if f.get("kind") in ("issue", "guide") else "takes place on"
    s = f"{f['label']} {verb} {f['publication_text']}" if f.get("publication_text") else f["label"]
    if f.get("ad_deadline_text") and f.get("kind") in ("issue", "guide"):
        s += f" (advertising deadline {f['ad_deadline_text']})"
    return s + "."


def renewal_issue(db, last, target_year: int, today: date | None = None):
    """The issue to offer a returning advertiser: this year's counterpart of the one they booked (same kind, nearest
    date a year on) while it's still open for bookings - otherwise the title's next open issue."""
    from sqlalchemy import func, select

    from app.models import SalesEdition
    today = today or date.today()
    if last.edition_date and target_year > last.year:
        want = shift_year(last.edition_date)
        e = db.scalars(select(SalesEdition).where(SalesEdition.title_id == last.title_id, SalesEdition.year == target_year,
                                                  SalesEdition.kind == last.kind, SalesEdition.edition_date.isnot(None))
                       .order_by(func.abs(SalesEdition.edition_date - want))).first()
        if e and (e.ad_deadline or e.edition_date) >= today:
            return e
    return next_issue(db, last.title_id, today)
