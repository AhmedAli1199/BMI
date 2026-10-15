"""Editorial plan, live: deadlines coming up, the issues coming out, and one issue in full (features, dates,
bookings so far, who to pitch). Uses the editorial plan's own functions, so it says what the planner shows."""
from __future__ import annotations

import re
import uuid
from datetime import date, timedelta

from sqlalchemy import false, or_, select

from app.brain import access
from app.brain.registry import ToolEnv, ToolError, brain_tool


def _d(v: date | None) -> str | None:
    return v.strftime("%a %-d %b %Y") if v else None


def _brand(key: str):
    from app.sales.brands import BRANDS
    k = (key or "").strip().lower()
    if not k:
        return None
    hit = next((b for b in BRANDS if k in (b.key.lower(), b.name.lower(), b.short.lower())), None) or \
        next((b for b in BRANDS if k in b.name.lower()), None)
    if not hit:
        raise ToolError("No brand called that. Brands: " + ", ".join(b.name for b in BRANDS))
    return hit


@brain_tool("Checking the deadlines")
def editorial_deadlines(env: ToolEnv, days: int = 30, brand: str = "") -> dict:
    """Every editorial, advertising and copy deadline and publication date coming up, soonest first.

    Args:
      days: how many days ahead (1-180)
      brand: optional brand, e.g. "Selling Travel"
    """
    access.require(env, "editorial")
    from app.api.routes import editorial as ed
    b = _brand(brand)
    rows = ed.deadlines(days=max(1, min(int(days or 30), 180)), past=0, brand=b.key if b else None, db=env.db)
    return {"deadlines": [{"when": _d(r.date), "in_days": r.days, "what": r.what, "issue": f"{r.issue.title_name} · {r.issue.name}",
                           "link": f"/editorial/issues/{r.issue.id}"} for r in rows[:40]],
            "more": max(0, len(rows) - 40), "see_all": "/editorial"}


@brain_tool("Checking the editorial plan")
def editorial_upcoming(env: ToolEnv, brand: str = "", months: int = 3) -> dict:
    """The issues, guides and events coming out in the next few months: dates, deadlines, theme, how many
    features are planned and what's booked so far.

    Args:
      brand: optional brand, e.g. "OnBoard Hospitality"
      months: how far ahead (1-12)
    """
    access.require(env, "editorial")
    from app.api.routes import editorial as ed
    from app.sales import brands as B
    today = date.today()
    end = today + timedelta(days=31 * max(1, min(int(months or 3), 12)))
    b = _brand(brand)
    titles = ed._titles_by_id(env.db)
    out = []
    for br in [b] if b else B.BRANDS:
        eds = [e for e in ed._brand_editions(env.db, br) if e.kind in ed.PLAN_KINDS and e.edition_date and today <= e.edition_date <= end]
        books, feats = ed._bookings(env.db, [e.id for e in eds]), ed._feature_counts(env.db, [e.id for e in eds])
        for e in eds:
            o = ed._out(e, titles[e.title_id], books, feats)
            out.append({"issue": f"{o.title_name} · {o.name}", "brand": o.brand_name, "out": _d(o.edition_date), "theme": o.theme,
                        "ad_deadline": _d(o.ad_deadline), "copy_deadline": _d(o.copy_deadline), "editorial_deadline": _d(o.editorial_deadline),
                        "features_planned": o.features, "booked_gbp": o.booked_gbp, "items_booked": o.orders,
                        "link": f"/editorial/issues/{o.id}", "_sort": o.edition_date})
    out.sort(key=lambda x: x.pop("_sort"))
    return {"issues": out[:30], "more": max(0, len(out) - 30), "see_all": "/editorial"}


def _find_issue(env: ToolEnv, issue: str):
    from app.models import SalesEdition, SalesTitle
    from app.api.routes import editorial as ed
    s = (issue or "").strip()
    if re.fullmatch(r"[0-9a-fA-F-]{36}", s):
        e = env.db.get(SalesEdition, uuid.UUID(s))
        if e:
            return e, []
    words = [w for w in re.findall(r"\w+", s) if len(w) > 1]
    stmt = select(SalesEdition).join(SalesTitle, SalesTitle.id == SalesEdition.title_id).where(SalesEdition.kind.in_(ed.PLAN_KINDS))
    for w in words:
        stmt = stmt.where(or_(SalesEdition.name.ilike(f"%{w}%"), SalesTitle.name.ilike(f"%{w}%"), SalesEdition.theme.ilike(f"%{w}%"),
                              (SalesEdition.year == int(w)) if w.isdigit() and len(w) == 4 else false()))
    rows = env.db.scalars(stmt.order_by(SalesEdition.edition_date.desc().nulls_last()).limit(8)).all()
    if len(rows) == 1:
        return rows[0], []
    today = date.today()
    nxt = [r for r in rows if r.edition_date and r.edition_date >= today]
    if len(nxt) == 1:
        return nxt[0], []
    return None, rows


@brain_tool("Looking at the issue")
def editorial_issue(env: ToolEnv, issue: str) -> dict:
    """One issue in full: dates and deadlines, theme, the planned features, what's booked against last year, and
    who to pitch (last year's advertisers not back yet, and companies that fit a feature).

    Args:
      issue: the issue's name with its title (e.g. "Selling Travel AprMay 2026"), or its id from the page
    """
    access.require(env, "editorial")
    from app.api.routes import editorial as ed
    e, choices = _find_issue(env, issue)
    if not e:
        if not choices:
            raise ToolError("No issue matches that. Try the title and the issue name, e.g. \"Selling Travel AprMay\".")
        titles = ed._titles_by_id(env.db)
        return {"which_one": [{"issue": f"{titles[c.title_id].name} · {c.name}", "out": _d(c.edition_date), "id": str(c.id)} for c in choices]}
    d = ed.issue(e.id, db=env.db, identity=env.identity)
    out = {
        "issue": f"{d.title_name} · {d.name}", "brand": d.brand_name, "out": _d(d.edition_date), "theme": d.theme,
        "deadlines": {"editorial": _d(d.editorial_deadline), "advertising": _d(d.ad_deadline), "copy": _d(d.copy_deadline),
                      "other": [{"what": m.label, "when": _d(m.date)} for m in d.milestones]},
        "features": [{"title": f.title, "about": f.description, "status": f.status, "can_be_sponsored": f.sponsorable} for f in d.feature_list],
        "booked_gbp": d.booked_gbp, "items_booked": d.orders, "last_year": d.last_year, "notes": d.notes,
        "link": f"/editorial/issues/{d.id}", "sales_page": f"/sales/editions/{d.id}",
    }
    if access.can(env, "editions") or access.can(env, "renewals"):
        try:
            p = ed.who_to_pitch(e.id, db=env.db)
            def row(c):
                return {"company": c.name, "why": c.reason, "last_booked": _d(c.last_booked), "last_value_gbp": c.last_value_gbp,
                        "salesperson": c.rep, **({"link": f"/companies/{c.company_id}"} if c.company_id else {})}
            out["who_to_pitch"] = {"not_back_from_last_year": [row(c) for c in p.lapsed[:8]], "from_the_issue_before": [row(c) for c in p.previous[:5]],
                                   "fit_a_feature": [row(c) | {"feature": c.feature} for c in p.feature_matches[:5]], "already_booked": p.already_booked}
        except Exception:
            out["who_to_pitch"] = None
    return out
