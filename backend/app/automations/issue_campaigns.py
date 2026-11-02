"""SALES-029 - the pitch campaign for each upcoming issue, put together automatically.

"Who should we pitch?" on an issue's page lists last year's advertisers on the same issue, the previous issue's
advertisers, and past advertisers whose business fits a planned feature - leaving out everyone already booked on it.
Each morning, for every issue whose advertising deadline is "Days before the deadline" away (or nearer, if it was
missed), that list is turned into ready campaigns: one card per salesperson with their companies, the best person
to email at each (the booking's contact, else someone in marketing; never anyone unsubscribed or bounced), and a
pitch email drafted with the issue's details. "Open as a mail merge" opens it to check and send. Each issue is done
once; someone who books after the card was made is still on it, so the card says when it was put together.
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.automations.brevo_sync import _owner, _person
from app.automations.registry import ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.automations.state import get_state, set_state
from app.db.session import SessionLocal
from app.models import Company, ReviewQueueItem, SalesEdition, SalesTitle, User
from app.sales.editorial import fmt_day, issue_label

logger = logging.getLogger("app.automations.issue_campaigns")

KIND = "issue_pitch_campaign"
STATE = "issue_campaigns"
PLAN_KINDS = ("issue", "guide", "event", "awards")
LIST_LIMIT = 15


def due_issues(db: Session, today: date) -> list[SalesEdition]:
    days = runtime_settings.get_int(db, "pitch_campaign_days_before")
    done = {r[0] for r in db.execute(select(ReviewQueueItem.payload["edition_id"].astext).where(ReviewQueueItem.kind == KIND)) if r[0]}
    done |= set(get_state(db, STATE).get("nobody") or [])
    eds = db.scalars(select(SalesEdition).where(SalesEdition.kind.in_(PLAN_KINDS), SalesEdition.ad_deadline.isnot(None),
                                                SalesEdition.ad_deadline >= today + timedelta(days=3),
                                                SalesEdition.ad_deadline <= today + timedelta(days=days))
                     .order_by(SalesEdition.ad_deadline))
    return [e for e in eds if str(e.id) not in done]


def draft(shared: dict) -> tuple[str, str]:
    mag = shared.get("brand") or shared.get("title")
    subject = f"{mag or 'Our next issue'}: {shared.get('issue') or 'the next issue'}"
    feats = f" It includes {shared['features']}." if shared.get("features") else ""
    out = f", out {shared['issue_date']}" if shared.get("issue_date") else ""
    deadline = f" The advertising deadline is {shared['ad_deadline']}." if shared.get("ad_deadline") else ""
    body = ("Dear {{salutation|colleague}},\n\n"
            f"We're putting together {shared.get('issue') or 'our next issue'} of {mag or 'the magazine'}{out}, "
            f"and I'd love {{{{company}}}} to be part of it again.{feats}{deadline}\n\n"
            "Would you like me to send over the options and prices?\n\nKind regards,\n{{my_name}}")
    return subject, body


def cards_for(db: Session, e: SalesEdition, today: date) -> list[ReviewQueueItem]:
    from app.api.routes.editorial import who_to_pitch
    from app.services import mail_merge as mm

    pitch = who_to_pitch(e.id, db)
    title = db.get(SalesTitle, e.title_id)
    shared = mm.shared_context(db, edition_id=e.id)
    subject, body = draft(shared)
    mag = shared.get("brand") or (title.name if title else "")
    label = f"{mag} {issue_label(e)}".strip()
    by_owner: dict = defaultdict(list)
    for p in [*pitch.lapsed, *pitch.previous, *pitch.feature_matches]:
        co = db.get(Company, p.company_id) if p.company_id else None
        owner = _owner(db, co) if co else None
        by_owner[owner.id if owner else None].append((p, co))
    cards = []
    for owner_id, rows in by_owner.items():
        owner = db.get(User, owner_id) if owner_id else None
        reach = [(p, co, person) for p, co in rows if co for person in [_person(db, co)] if person]
        nobody = [p.name for p, co in rows if not co or not _person(db, co)]
        details = [{"label": "Issue", "value": label, "href": f"/editorial/issues/{e.id}"},
                   {"label": "Advertising deadline", "value": fmt_day(e.ad_deadline)},
                   {"label": "Already booked", "value": f"{pitch.already_booked} - left out"}]
        for p, co, person in reach[:LIST_LIMIT]:
            details.append({"label": co.name, "value": f"{person.full_name or 'Contact'} · {p.reason}", "href": f"/companies/{co.id}"})
        if len(reach) > LIST_LIMIT:
            details.append({"label": "And", "value": f"{len(reach) - LIST_LIMIT} more - all listed in the mail merge"})
        if nobody:
            details.append({"label": "No one to email at", "value": ", ".join(sorted(nobody))[:500]})
        details.append({"label": "Worth knowing", "value": f"Put together on {fmt_day(today)}. Anyone who books after that is still "
                                                           "listed: untick them in the mail merge."})
        card = ReviewQueueItem(
            id=uuid.uuid4(), kind=KIND, source_db=None, status="pending",
            payload={
                "summary": f"{len(reach)} {'company' if len(reach) == 1 else 'companies'} to pitch for {label}",
                "details": details, "original_text": f"Subject: {subject}\n\n{body}", "original_label": "Drafted pitch",
                "edition_id": str(e.id), "owner_user_id": str(owner.id) if owner else None,
                "merge": {"contact_ids": [str(person.id) for _, _, person in reach], "subject": subject, "body": body,
                          "label": f"Pitch: {label}"[:300]},
                "hidden_actions": [] if reach else ["open_merge"],
                "related_entities": [{"type": "company", "id": str(co.id), "label": co.name} for _, co, _ in reach[:LIST_LIMIT]],
                "facets": {"magazine": mag or "Other",
                           "salesperson": (owner.name or owner.email) if owner else "No one",
                           "size": "Under 10" if len(reach) < 10 else "10 to 40" if len(reach) <= 40 else "Over 40"},
                "sort_date": e.ad_deadline.isoformat(),
            })
        db.add(card)
        cards.append(card)
    if not cards:   # nobody to pitch: remember the issue was looked at
        nobody = get_state(db, STATE).get("nobody") or []
        set_state(db, STATE, {"nobody": [*nobody, str(e.id)][-1000:]})
    return cards


def scan() -> None:
    today = date.today()
    db = SessionLocal()
    try:
        made = 0
        for e in due_issues(db, today):
            made += len(cards_for(db, e, today))
            db.commit()
        logger.info("issue campaigns: %d cards", made)
    finally:
        db.close()


def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "open_merge":
        item.payload = {**item.payload, "open_href": f"/mail-merge?review={item.id}"}
    elif action_id != "not_now":
        raise ValueError("That button isn't available on this card.")


register(ReviewKind(
    kind=KIND,
    label="Issue pitch campaigns",
    description="For an issue whose advertising deadline is coming up: the companies to pitch (last year's advertisers and others not yet "
                "booked), the person to email at each, and a pitch drafted, ready to send as a mail merge.",
    actions=[
        ReviewAction(id="open_merge", label="Open as a mail merge", style="primary", outcome="approved"),
        ReviewAction(id="not_now", label="Not this time", style="secondary", outcome="dismissed", reopenable=True),
    ],
    handler=_handle,
    audience="sales",
    facets=(("magazine", "Magazine"), ("salesperson", "Salesperson"), ("size", "How many")),
    date_sort_label="advertising deadline",
))

register_job(ScheduledJob(
    id="issue_campaign_scan",
    label="Issue pitch campaigns",
    description="Each weekday morning, puts together the pitch campaign for issues whose advertising deadline is coming up.",
    cron="25 7 * * 1-5",
    func=scan,
    enabled_flag="automations_issue_campaigns_enabled",
))
