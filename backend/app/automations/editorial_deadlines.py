"""Advertising deadline reminders from the editorial plan.

Each morning, for every issue whose advertising deadline is N days away (N from
`editorial_deadline_alert_days`), the brand's publishers and the salespeople who
sold that title in the last year get one in-app notification: the deadline, what's
booked so far, and how many of last year's advertisers haven't rebooked - linking
to the issue page, where "Who should we pitch?" lists them.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.automations.scheduler import ScheduledJob, register_job
from app.db.session import SessionLocal
from app.models import AutomationState, SalesEdition, SalesOrder, SalesRep, SalesTitle
from app.sales import brands as B
from app.sales.analytics import BOOKED
from app.sales.editorial import fmt_day, issue_label

logger = logging.getLogger(__name__)

PLAN_KINDS = ("issue", "guide", "event", "awards")


def _days(db: Session) -> list[int]:
    out = []
    for x in runtime_settings.get_csv(db, "editorial_deadline_alert_days"):
        try:
            n = int(str(x).strip())
        except ValueError:
            continue
        if 0 <= n <= 120:
            out.append(n)
    return sorted(set(out), reverse=True)


def _recipients(db: Session, brand: B.Brand, title_id: uuid.UUID, today: date) -> set[uuid.UUID]:
    """The brand's publishers plus anyone who sold this title in the last year (linked rep -> user)."""
    codes = set(brand.editors)
    reps = {r.id: r for r in db.scalars(select(SalesRep).where(SalesRep.user_id.isnot(None)))}
    users = {r.user_id for r in reps.values() if r.code in codes}
    sold = db.scalars(select(SalesOrder.rep_id).join(SalesEdition, SalesOrder.edition_id == SalesEdition.id)
                      .where(SalesEdition.title_id == title_id, SalesOrder.status == BOOKED,
                             SalesOrder.booked_on >= today - timedelta(days=365)).distinct())
    users |= {reps[r].user_id for r in sold if r in reps}
    return {u for u in users if u}


def _lapsed(db: Session, e: SalesEdition) -> int:
    """Last year's advertisers on the equivalent issue who haven't booked this one."""
    if not e.edition_date:
        return 0
    ly = db.scalars(select(SalesEdition).where(SalesEdition.title_id == e.title_id, SalesEdition.year == e.year - 1, SalesEdition.kind == e.kind,
                                               SalesEdition.edition_date.isnot(None))
                    .order_by(func.abs(SalesEdition.edition_date - (e.edition_date - timedelta(days=365))))).first()
    if not ly:
        return 0

    def names(eid):
        return {(str(o.company_id) if o.company_id else o.client_name.strip().lower())
                for o in db.scalars(select(SalesOrder).where(SalesOrder.edition_id == eid, SalesOrder.status == BOOKED))}
    return len(names(ly.id) - names(e.id))


def remind(db: Session, today: date | None = None) -> int:
    """Sends the due reminders; returns how many notifications were created. Safe to run more than once a day."""
    from app.services.notify import create_notification

    today = today or date.today()
    days = _days(db)
    if not days:
        return 0
    targets = [today + timedelta(days=n) for n in days]
    eds = db.scalars(select(SalesEdition).where(SalesEdition.kind.in_(PLAN_KINDS), SalesEdition.ad_deadline.in_(targets)))
    sent = 0
    for e in eds:
        t = db.get(SalesTitle, e.title_id)
        brand = B.brand_for_title_slug(t.slug) if t else None
        if not brand:
            continue
        key = f"editorial_deadline:{e.id}:{e.ad_deadline.isoformat()}:{(e.ad_deadline - today).days}"
        if db.get(AutomationState, key):
            continue
        n = (e.ad_deadline - today).days
        booked = db.execute(select(func.count(), func.coalesce(func.sum(SalesOrder.value_gbp), 0))
                            .where(SalesOrder.edition_id == e.id, SalesOrder.status == BOOKED)).one()
        lapsed = _lapsed(db, e)
        when = "today" if n == 0 else ("tomorrow" if n == 1 else f"in {n} days")
        title = f"{t.name} {issue_label(e)}: advertising deadline {when}"
        body = (f"Advertising closes {fmt_day(e.ad_deadline)}. {booked[0]} booking{'s' if booked[0] != 1 else ''} so far "
                f"(£{float(booked[1]):,.0f} before VAT).")
        if lapsed:
            body += f" {lapsed} of last year's advertisers haven't rebooked yet - see who to pitch on the issue page."
        for uid in _recipients(db, brand, t.id, today):
            create_notification(db, uid, "editorial_deadline", title, body, f"/editorial/issues/{e.id}", email=False)
            sent += 1
        db.add(AutomationState(key=key, value={"sent": today.isoformat()}))
    db.commit()
    return sent


def scan_editorial_deadlines() -> None:
    db = SessionLocal()
    try:
        n = remind(db)
        logger.info("editorial deadline reminders: %s notifications", n)
    finally:
        db.close()


register_job(ScheduledJob(
    id="editorial_deadline_alerts",
    label="Advertising deadline reminders",
    description="Reminds each brand's publishers and salespeople as an issue's advertising deadline approaches, with how many of last year's advertisers haven't rebooked.",
    cron="15 7 * * *",
    func=scan_editorial_deadlines,
    enabled_flag="automations_editorial_deadline_alerts_enabled",
))
