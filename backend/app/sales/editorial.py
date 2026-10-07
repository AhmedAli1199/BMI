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
