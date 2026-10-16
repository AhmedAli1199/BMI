"""The Brain as a coach: at most one tip for the page someone is on, the welcome tour they've finished, and whether
they want tips and celebrations at all (Settings > The Brain). Tips are plain rules over data the person can already
see - no model call, so they're instant and free. Each tip has a stable id so "Not now" / "Got it" can hide it.

State lives in users.preferences: the two switches are normal preferences (app/preferences.py); the tours done and
the dismissed tips are internal keys that don't show on the Settings page.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.identity import Identity
from app.models import Reminder, ReviewQueueItem, SalesDeal, SalesEdition, SalesRep, SalesTitle, User
from app.preferences import resolve

TOURS_KEY = "_brain_tours_done"
DISMISSED_KEY = "_brain_tips_dismissed"   # {tip_id: "until" ISO date}
UNSENT_DAYS = 3
DEADLINE_DAYS = 7


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fmt_day(d: date) -> str:
    return f"{d:%a} {d.day} {d:%b}"


def _dismissed(user: User, today: date) -> set[str]:
    out = set()
    for tid, until in ((user.preferences or {}).get(DISMISSED_KEY) or {}).items():
        try:
            if date.fromisoformat(until) >= today:
                out.add(tid)
        except (TypeError, ValueError):
            continue
    return out


def _my_rep_ids(db: Session, user: User) -> list:
    return list(db.scalars(select(SalesRep.id).where(SalesRep.user_id == user.id)))


def _mine(db: Session, user: User):
    """Bookings that are this person's: they sold it, or they made it."""
    reps = _my_rep_ids(db, user)
    conds = [SalesDeal.created_by_user_id == user.id]
    if reps:
        conds.append(SalesDeal.rep_id.in_(reps))
    from sqlalchemy import or_
    return or_(*conds)


def _unsent_one(db: Session, user: User, deal_id: str) -> dict | None:
    try:
        d = db.get(SalesDeal, deal_id)
    except Exception:
        return None
    if not d or d.status != "confirmed" or d.sent_at or not d.confirmed_at:
        return None
    if d.created_by_user_id != user.id and d.rep_id not in _my_rep_ids(db, user):
        return None
    days = (_now() - d.confirmed_at).days
    if days < UNSENT_DAYS:
        return None
    return {"id": f"unsent:{d.id}", "mood": "pointing",
            "text": f"This booking was confirmed {days} days ago, but the confirmation hasn't gone to the client yet.",
            "show": "Email the confirmation", "action": "Show me", "forever": True}


def _unsent_many(db: Session, user: User) -> dict | None:
    cutoff = _now() - timedelta(days=UNSENT_DAYS)
    n = db.scalar(select(func.count()).select_from(SalesDeal).where(
        SalesDeal.status == "confirmed", SalesDeal.sent_at.is_(None), SalesDeal.confirmed_at <= cutoff, _mine(db, user)))
    if not n:
        return None
    return {"id": f"unsent-list:{n}", "mood": "pointing",
            "text": (f"{n} of your confirmed bookings haven't had their confirmation sent yet." if n > 1
                     else "One of your confirmed bookings hasn't had its confirmation sent yet."),
            "link": "/sales/deals?mine=1&status=confirmed", "action": "See them"}


def _deadline(db: Session, identity: Identity) -> dict | None:
    today = _now().date()
    q = (select(SalesEdition, SalesTitle).join(SalesTitle, SalesEdition.title_id == SalesTitle.id)
         .where(SalesEdition.status == "open", SalesEdition.ad_deadline >= today,
                SalesEdition.ad_deadline <= today + timedelta(days=DEADLINE_DAYS))
         .order_by(SalesEdition.ad_deadline))
    if identity.is_known and not identity.is_admin:
        dbs = {a[0] for a in identity.access}
        if not dbs:
            return None
        q = q.where(SalesTitle.crm_source_db.in_(dbs))
    row = db.execute(q.limit(1)).first()
    if not row:
        return None
    e, t = row
    days = (e.ad_deadline - today).days
    when = "today" if days == 0 else "tomorrow" if days == 1 else f"in {days} days"
    label = f"{t.name} {'Issue ' if e.kind == 'issue' and e.name.isdigit() else ''}{e.name}"
    return {"id": f"deadline:{e.id}", "mood": "pointing",
            "text": f"Booking deadline for {label} is {_fmt_day(e.ad_deadline)} - {when}.",
            "link": f"/sales/editions/{e.id}", "action": "Open the edition", "forever": True}


def _queue(db: Session, identity: Identity) -> dict | None:
    from app.api.routes.review_queue import _apply_scope
    n = db.scalar(_apply_scope(select(func.count()).select_from(ReviewQueueItem).where(ReviewQueueItem.status == "pending"), identity, db))
    if not n:
        return None
    return {"id": f"queue:{_now().date()}", "mood": "happy",
            "text": f"{n} {'suggestions are' if n > 1 else 'suggestion is'} waiting for you in the Review Queue.",
            "link": "/automations/review", "action": "Open the Review Queue"}


def _reminders(db: Session, user: User) -> dict | None:
    n = db.scalar(select(func.count()).select_from(Reminder).where(
        Reminder.user_id == user.id, Reminder.status == "open", Reminder.due_at <= _now()))
    if not n:
        return None
    return {"id": f"reminders:{_now().date()}", "mood": "pointing",
            "text": f"You have {n} reminder{'s' if n > 1 else ''} due.", "link": "/reminders", "action": "See them"}


def tip_for(db: Session, identity: Identity, user: User, path: str) -> dict | None:
    """The single most useful tip for this page, or None. Cheap queries only; never raises."""
    path = (path or "/").split("?")[0]
    checks = []
    if path.startswith("/sales/deals/") and len(path.split("/")) == 4 and path.split("/")[3] not in ("new",):
        checks.append(lambda: _unsent_one(db, user, path.split("/")[3]))
    if path == "/" or path == "/sales/deals":
        checks.append(lambda: _unsent_many(db, user))
    if path in ("/", "/sales", "/sales/editions", "/editorial", "/sales/dashboard"):
        checks.append(lambda: _deadline(db, identity))
    if path == "/":
        checks += [lambda: _reminders(db, user), lambda: _queue(db, identity)]
    gone = _dismissed(user, _now().date())
    for check in checks:
        try:
            t = check()
        except Exception:
            db.rollback()
            continue
        if t and t["id"] not in gone:
            return t
    return None


def state(db: Session, identity: Identity, user: User, path: str) -> dict:
    prefs = resolve(user.preferences or {})
    tips_on = prefs.get("brain_tips", "on") == "on"
    return {
        "tips": tips_on,
        "celebrations": prefs.get("brain_celebrations", "on") == "on",
        "tours_done": list((user.preferences or {}).get(TOURS_KEY) or []),
        "tip": tip_for(db, identity, user, path) if tips_on else None,
    }


def dismiss(db: Session, user: User, tip_id: str, forever: bool) -> None:
    """"Got it" on a one-off tip hides it for good (a year); "Not now" hides it for a week."""
    until = (_now().date() + timedelta(days=365 if forever else 7)).isoformat()
    prefs = dict(user.preferences or {})
    gone = {k: v for k, v in (prefs.get(DISMISSED_KEY) or {}).items() if v >= _now().date().isoformat()}  # drop expired
    gone[tip_id[:120]] = until
    prefs[DISMISSED_KEY] = dict(list(gone.items())[-200:])
    user.preferences = prefs
    db.commit()


def tour_done(db: Session, user: User, tour: str, done: bool = True) -> None:
    prefs = dict(user.preferences or {})
    tours = set(prefs.get(TOURS_KEY) or [])
    (tours.add if done else tours.discard)(tour[:40])
    prefs[TOURS_KEY] = sorted(tours)
    user.preferences = prefs
    db.commit()
