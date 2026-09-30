"""SALES-028 - weekly management summary & behind-last-cycle alerts.

Two jobs, both read-only over the order register (nothing here writes to
sales tables, the CRM or Xero):

- management_alerts_scan (daily): any edition still selling that has
  booked >= sales_pace_threshold_pct below its equivalent edition at the
  same point before publication (see app/sales/analytics.py::edition_pace,
  the same calculation the dashboard uses) fires one alert to leadership.
  Alerts are rule-computed - no model is involved, so the wording can't
  drift from the numbers. Thin comparisons are never judged (minimum £ and
  minimum bookings), and an edition isn't re-alerted inside the cooldown.
- weekly_management_summary (Mondays): a one-page brief. Every figure
  comes from the same functions the dashboard uses; the only thing a model
  may write is the short headline paragraph, and even that is thrown away
  if it contains a number that isn't in the source figures. Every section
  is always present - a templated version is used whenever the model isn't
  configured, fails, or is rejected.

Delivery is in-app notifications to the recipients (which also go out as
email once the automation mailbox is set up) plus the Teams webhook if one
is configured. Nothing is sent to anyone outside the recipient list.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.automations.llm import draft_text, is_configured
from app.automations.scheduler import ScheduledJob, register_job
from app.automations.teams_notify import post_summary
from app.core.config import settings
from app.db.session import SessionLocal
from app.models import ManagementAlert, ReviewQueueItem, SalesOrder, User, WeeklySummary
from app.sales.analytics import BOOKED, edition_pace
from app.services.notify import create_notification

logger = logging.getLogger("app.automations.management_reports")


def _money(v: float | None) -> str:
    return "—" if v is None else f"£{v:,.0f}"


def _pct(v: float) -> str:
    return f"{abs(v) * 100:.0f}%"


def recipients(db: Session) -> list[User]:
    emails = [e.lower() for e in runtime_settings.get_csv(db, "management_recipients")]
    q = select(User).where(User.is_active.is_(True))
    q = q.where(func.lower(User.email).in_(emails)) if emails else q.where(User.role == "admin")
    return list(db.scalars(q.order_by(User.name)))


# ---- Alerts ----------------------------------------------------------------------

def run_alerts(db: Session, today: date | None = None, *, notify: bool = True) -> list[ManagementAlert]:
    from app.api.routes.sales import edition_label
    from app.models import SalesTitle

    today = today or date.today()
    threshold = runtime_settings.get_float(db, "sales_pace_threshold_pct")
    cooldown = timedelta(days=runtime_settings.get_int(db, "sales_alert_cooldown_days"))
    now = datetime.now(timezone.utc)
    titles = {t.id: t for t in db.scalars(select(SalesTitle))}
    rows = edition_pace(
        db, today, threshold=threshold,
        min_prior_gbp=runtime_settings.get_float(db, "sales_pace_min_prior_gbp"),
        min_prior_orders=runtime_settings.get_int(db, "sales_pace_min_prior_orders"),
    )
    fired: list[ManagementAlert] = []
    for r in rows:
        if r["state"] != "behind":
            continue
        ed, prev = r["edition"], r["prev"]
        recent = db.scalar(select(func.max(ManagementAlert.fired_at)).where(ManagementAlert.subject_id == ed.id))
        if recent and now - recent < cooldown:
            continue
        label = edition_label(titles[ed.title_id], ed)
        prev_label = edition_label(titles[prev.title_id], prev)
        when = f"{'runs' if ed.kind == 'event' else 'publishes'} {ed.edition_date:%d %b %Y}"
        message = (
            f"{label} ({when}) has {_money(r['booked'])} booked across {r['orders']} booking(s). At the same point before "
            f"{prev_label} it had {_money(r['prev_point_gbp'])} across {r['prev_point_orders']} - "
            f"{_money(abs(r['gap_gbp']))} ({_pct(r['gap_pct'])}) behind."
        )
        alert = ManagementAlert(
            id=uuid.uuid4(), subject_type="edition", subject_id=ed.id, subject_label=label, comparison_label=prev_label,
            prior_value=r["prev_point_gbp"], current_value=r["booked"], gap=r["gap_gbp"], gap_pct=r["gap_pct"],
            threshold=threshold, message=message, fired_at=now,
            records_ref=[{"type": "edition", "id": str(ed.id), "label": label}, {"type": "edition", "id": str(prev.id), "label": prev_label}],
        )
        db.add(alert)
        fired.append(alert)
    db.flush()
    if fired and notify:
        to = recipients(db)
        for a in fired:
            for user in to:
                create_notification(db, user.id, "management_alert", f"Behind last cycle: {a.subject_label}", a.message,
                                    link=f"/sales/editions/{a.subject_id}")
        post_summary(db, "Behind last cycle:\n" + "\n".join(f"- {a.message}" for a in fired))
    return fired


def scan_management_alerts() -> None:
    db = SessionLocal()
    try:
        fired = run_alerts(db)
        db.commit()
        logger.info("management alerts: %d fired", len(fired))
    finally:
        db.close()


# ---- Weekly summary ----------------------------------------------------------------

_NUMBER = re.compile(r"£\s?[\d,]+(?:\.\d+)?|\d+(?:\.\d+)?%|\d[\d,]*(?:\.\d+)?")


def _numbers(text: str) -> set[str]:
    return {re.sub(r"[£\s,]", "", m) for m in _NUMBER.findall(text)}


def build_snapshot(db: Session, today: date) -> dict:
    """Every figure the brief may use, computed by the same functions the
    dashboard and overview pages call, so the two can never disagree."""
    from app.api.routes.sales import dashboard, overview

    ov = overview(year=today.year, db=db)
    dash = dashboard(db=db)

    def booked_between(start: date, end: date) -> tuple[int, float]:
        n, v = db.execute(select(func.count(), func.coalesce(func.sum(SalesOrder.value_gbp), 0)).where(
            SalesOrder.status == BOOKED, SalesOrder.booked_on >= start, SalesOrder.booked_on < end)).one()
        return n, float(v)

    wk_n, wk_v = booked_between(today - timedelta(days=7), today + timedelta(days=1))
    pv_n, pv_v = booked_between(today - timedelta(days=14), today - timedelta(days=7))

    def pending(kind: str) -> int:
        return db.scalar(select(func.count()).select_from(ReviewQueueItem).where(
            ReviewQueueItem.kind == kind, ReviewQueueItem.status == "pending")) or 0

    def pace_item(p) -> dict:
        return {"label": p.edition.label, "id": str(p.edition.id), "booked": p.booked_gbp, "prev_point": p.previous_point_gbp,
                "gap_gbp": p.gap_gbp, "gap_pct": p.gap_pct, "date": p.edition_date.isoformat() if p.edition_date else None}

    since = datetime.now(timezone.utc) - timedelta(days=7)
    alerts = db.scalars(select(ManagementAlert).where(ManagementAlert.fired_at >= since).order_by(ManagementAlert.fired_at.desc())).all()
    return {
        "as_of": today.isoformat(), "year": ov.year,
        "booked_gbp": ov.booked_gbp, "last_year_same_point_gbp": ov.last_year_same_point_gbp,
        "invoiced_gbp": ov.invoiced_gbp, "uninvoiced_count": ov.uninvoiced_count, "uninvoiced_gbp": ov.uninvoiced_gbp,
        "advertisers": ov.advertisers, "new_advertisers": ov.new_advertisers, "renewal_candidates": ov.renewal_candidates,
        "titles": [{"name": t.title.name, "booked": t.booked_gbp, "last_year_same_point": t.last_year_same_point_gbp,
                    "orders": t.orders} for t in ov.by_title if t.orders or t.last_year_same_point_gbp][:8],
        "week": {"orders": wk_n, "value": wk_v, "prev_orders": pv_n, "prev_value": pv_v},
        "behind": [pace_item(p) for p in dash.pace if p.state == "behind"][:6],
        "ahead": [pace_item(p) for p in dash.pace if p.state == "ahead"][:4],
        "not_comparable": sum(1 for p in dash.pace if p.state == "not_comparable"),
        "alerts": [{"label": a.subject_label, "message": a.message} for a in alerts],
        "unattributed": {"orders": dash.unattributed.orders, "value": dash.unattributed.value_gbp},
        "pending": {"invoice": pending("sor_invoice_missing"), "renewal": pending("renewal_due"), "client_match": pending("sor_client_match")},
        "threshold_pct": dash.threshold_pct,
    }


def _sections(s: dict, headline: str) -> list[dict]:
    rev_delta = None
    if s["last_year_same_point_gbp"]:
        rev_delta = (s["booked_gbp"] - s["last_year_same_point_gbp"]) / s["last_year_same_point_gbp"]
    revenue = {"key": "revenue", "title": "Revenue", "paragraphs": [
        f"{_money(s['booked_gbp'])} booked for {s['year']} so far"
        + (f", {_pct(rev_delta)} {'ahead of' if rev_delta >= 0 else 'behind'} the {_money(s['last_year_same_point_gbp'])} at this point last year." if rev_delta is not None else ".")
        + f" {_money(s['invoiced_gbp'])} has been invoiced; {s['uninvoiced_count']} booking(s) worth {_money(s['uninvoiced_gbp'])} are still awaiting an invoice."
    ], "bullets": [
        {"text": f"{t['name']}: {_money(t['booked'])} ({t['orders']} bookings) vs {_money(t['last_year_same_point'])} at this point last year", "href": "/sales"}
        for t in s["titles"]
    ]}
    w = s["week"]
    activity = {"key": "activity", "title": "Activity", "paragraphs": [
        f"{w['orders']} booking(s) worth {_money(w['value'])} in the last 7 days, against {w['prev_orders']} worth {_money(w['prev_value'])} the week before.",
        f"{s['advertisers']} advertisers booked so far this year, {s['new_advertisers']} of them new; {s['renewal_candidates']} of last year's haven't rebooked yet.",
    ], "bullets": []}

    def ed_bullet(e: dict, word: str) -> dict:
        return {"text": f"{e['label']}: {_money(e['booked'])} booked vs {_money(e['prev_point'])} at the same point last cycle ({_pct(e['gap_pct'])} {word})", "href": f"/sales/editions/{e['id']}"}

    watch_paras = [f"Editions are compared with their equivalent last cycle at the same distance before publication; {_pct(s['threshold_pct'])} or more below counts as behind."]
    if not s["behind"] and not s["ahead"]:
        watch_paras.append("No edition is currently far enough ahead or behind to call.")
    if s["not_comparable"]:
        watch_paras.append(f"{s['not_comparable']} edition(s) are too early to compare fairly.")
    watch = {"key": "editions", "title": "Editions to watch", "paragraphs": watch_paras,
             "bullets": [ed_bullet(e, "behind") for e in s["behind"]] + [ed_bullet(e, "ahead") for e in s["ahead"]]}
    alerts = {"key": "alerts", "title": "Alerts this week",
              "paragraphs": [] if s["alerts"] else ["No new behind-last-cycle alerts this week."],
              "bullets": [{"text": a["message"], "href": None} for a in s["alerts"]]}
    delivery = {"key": "delivery", "title": "Sold-work delivery", "paragraphs": [
        "Stalled-delivery tracking isn't set up yet, so there is nothing to report here."], "bullets": []}
    decisions = []
    if s["pending"]["invoice"]:
        decisions.append({"text": f"{s['pending']['invoice']} booking(s) past publication with no invoice number are waiting for someone to raise the invoice.", "href": "/sales/invoicing"})
    if s["pending"]["renewal"]:
        decisions.append({"text": f"{s['pending']['renewal']} renewal email draft(s) are waiting for a salesperson to review.", "href": "/automations/review"})
    if s["pending"]["client_match"]:
        decisions.append({"text": f"{s['pending']['client_match']} order-register client(s) need matching to a CRM company.", "href": "/automations/review"})
    if s["unattributed"]["orders"]:
        decisions.append({"text": f"{s['unattributed']['orders']} booking(s) worth {_money(s['unattributed']['value'])} aren't credited to any salesperson.", "href": "/sales/dashboard"})
    if s["behind"]:
        decisions.append({"text": f"{len(s['behind'])} edition(s) are behind last cycle - is extra sales effort needed?", "href": "/sales/dashboard"})
    dec = {"key": "decisions", "title": "Needs a decision", "paragraphs": [] if decisions else ["Nothing is waiting on a decision."], "bullets": decisions}
    head = {"key": "headline", "title": "Headline", "paragraphs": [headline], "bullets": []}
    return [head, revenue, activity, watch, alerts, delivery, dec]


def _template_headline(s: dict) -> str:
    parts = [f"{_money(s['booked_gbp'])} booked for {s['year']} so far"]
    if s["last_year_same_point_gbp"]:
        d = (s["booked_gbp"] - s["last_year_same_point_gbp"]) / s["last_year_same_point_gbp"]
        parts[0] += f" ({_pct(d)} {'ahead of' if d >= 0 else 'behind'} the same point last year)"
    parts.append(f"{s['week']['orders']} booking(s) taken in the last 7 days")
    parts.append(f"{len(s['behind'])} edition(s) behind last cycle" if s["behind"] else "no edition behind last cycle")
    return "; ".join(parts) + "."


_HEADLINE_SYSTEM = (
    "You write the two-to-three sentence headline of a weekly sales brief for a magazine publisher's leadership team. "
    "You are given JSON of the week's figures. Write plain, neutral British English. Use ONLY figures that appear in the JSON, "
    "written exactly as a rounded £ amount or whole percentage; do not calculate new numbers, do not mention dates, and do not "
    "name or rank individual salespeople. Say what is going well, what needs attention, and stop. No greetings, no bullet points."
)


def _ai_headline(db: Session, snapshot: dict, facts_text: str) -> str | None:
    if not is_configured():
        return None
    import json

    text = draft_text(_HEADLINE_SYSTEM, json.dumps(snapshot, default=str), max_tokens=250, purpose="management_summary.headline")
    if not text or not text.strip():
        return None
    text = text.strip()
    if not _numbers(text) <= _numbers(facts_text):
        logger.warning("management summary: model headline contained figures not in the source data - using the template")
        return None
    return text


def _markdown(week_of: date, sections: list[dict]) -> str:
    out = [f"# Weekly sales summary - week of {week_of:%d %B %Y}", ""]
    for sec in sections:
        out += [f"## {sec['title']}", ""]
        out += [p + "\n" for p in sec["paragraphs"]]
        out += [f"- {b['text']}" for b in sec["bullets"]]
        if sec["bullets"]:
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def generate_weekly_summary(db: Session, today: date | None = None, *, notify: bool = True) -> tuple[WeeklySummary, bool]:
    """Writes (or rewrites) this week's brief. Returns (summary, created) -
    recipients are only notified when it is created, so a manual re-run
    never re-sends."""
    today = today or date.today()
    week_of = today - timedelta(days=today.weekday())
    snap = build_snapshot(db, today)
    template_sections = _sections(snap, _template_headline(snap))
    facts = " ".join(p for s in template_sections for p in s["paragraphs"] + [b["text"] for b in s["bullets"]])
    ai = _ai_headline(db, snap, facts)
    sections = _sections(snap, ai) if ai else template_sections
    row = db.scalar(select(WeeklySummary).where(WeeklySummary.week_of == week_of))
    created = row is None
    if created:
        row = WeeklySummary(id=uuid.uuid4(), week_of=week_of)
        db.add(row)
    row.sections, row.metrics_snapshot = sections, snap
    row.brief_markdown = _markdown(week_of, sections)
    row.source = "ai" if ai else "template"
    row.generated_at = datetime.now(timezone.utc)
    db.flush()
    if created and notify:
        headline = sections[0]["paragraphs"][0]
        for user in recipients(db):
            create_notification(db, user.id, "weekly_summary", f"Weekly sales summary - week of {week_of:%d %b}", headline, link="/sales/summaries")
        post_summary(db, f"Weekly sales summary: {headline} {settings.app_base_url.rstrip('/')}/sales/summaries")
    return row, created


def weekly_management_summary() -> None:
    db = SessionLocal()
    try:
        row, created = generate_weekly_summary(db)
        db.commit()
        logger.info("weekly management summary for %s: %s (%s)", row.week_of, "created" if created else "refreshed", row.source)
    finally:
        db.close()


register_job(ScheduledJob(
    id="management_alerts_scan",
    label="Behind-last-cycle alerts",
    description="Daily: alerts leadership when an issue or event has booked far less than its equivalent edition had at the same point last cycle (SALES-028).",
    cron="15 7 * * 1-5",
    func=scan_management_alerts,
    enabled_flag="automations_management_alerts_enabled",
))
register_job(ScheduledJob(
    id="weekly_management_summary",
    label="Weekly management summary",
    description="Monday morning: writes the one-page leadership brief from the order register and notifies the recipients (SALES-028).",
    cron="0 7 * * 1",
    func=weekly_management_summary,
    enabled_flag="automations_weekly_summary_enabled",
))
