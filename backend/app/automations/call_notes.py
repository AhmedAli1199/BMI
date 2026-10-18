"""Call notes: when the notetaker finishes a call, the notes land in the salesperson's review queue.
"Save to history" writes them onto the contact's history (and a reminder for each thing they said
they'd do); "Not needed" just closes the card. The notes stay on the call's own page either way."""
from __future__ import annotations

import calendar
import re
import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automations.registry import ReviewAction, ReviewKind, register
from app.models import CallRecording, Company, Contact, ReviewQueueItem

KIND = "call_notes"
PLATFORM = {"google_meet": "Google Meet", "teams": "Microsoft Teams", "zoom": "Zoom"}
SENTIMENT = {"positive": "Interested", "neutral": "Neutral", "negative": "Not keen"}
LONDON = ZoneInfo("Europe/London")


# ---- When an action item is due ---------------------------------------------------------------------
# The notes give each action item's "due" in the words used in the call ("by Friday", "next week", "14 Nov").
# The common ones become a date, counted from the day of the call; anything else falls back to the next
# working day.
_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_MONTHS = {**{m.lower(): i for i, m in enumerate(calendar.month_abbr) if m},
           **{m.lower(): i for i, m in enumerate(calendar.month_name) if m}, "sept": 9}
_MON = "(" + "|".join(sorted(_MONTHS, key=len, reverse=True)) + r")\.?"
_NUMBERS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "a couple of": 2, "a few": 3}
_COUNT = r"(\d+|" + "|".join(sorted(_NUMBERS, key=len, reverse=True)) + ")"


def next_working_day(d: date) -> date:
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _on(year: int | None, month: int, day: int, base: date) -> date | None:
    """A day and month; with no year, the next one from the call (14 Jan said in December is next January)."""
    try:
        d = date(year or base.year, month, day)
        if year is None and d < base:
            d = date(base.year + 1, month, day)
        return d
    except ValueError:
        return None


def due_from_text(text: str | None, base: date) -> date | None:
    """The date in the words used for when something is due, counted from `base` (the day of the call).
    None when we can't tell."""
    t = re.sub(r"\s+", " ", (text or "").lower()).strip()
    if not t:
        return None
    if re.search(r"\b(asap|as soon as possible|today|tonight|end of (the )?day|eod|this (morning|afternoon|evening))\b", t):
        return base
    if re.search(r"\btomorrow\b", t):
        return base + timedelta(days=1)
    if m := re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", t):
        return _on(int(m[1]), int(m[2]), int(m[3]), base)
    if m := re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2}|\d{4}))?\b", t):          # UK: day/month(/year)
        y = int(m[3]) if m[3] else None
        return _on(y + 2000 if y and y < 100 else y, int(m[2]), int(m[1]), base)
    if m := re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?(?: of)? " + _MON + r"(?:,? (\d{4}))?\b", t):   # 14 Nov, 14th of November
        return _on(int(m[3]) if m[3] else None, _MONTHS[m[2]], int(m[1]), base)
    if m := re.search(r"\b" + _MON + r" (\d{1,2})(?:st|nd|rd|th)?\b(?:,? (\d{4}))?", t):           # Nov 14
        return _on(int(m[3]) if m[3] else None, _MONTHS[m[1]], int(m[2]), base)
    if m := re.search(r"\bin " + _COUNT + r" (working |business )?(day|week|month)s?\b", t):          # in 3 days, in two weeks
        n = int(m[1]) if m[1].isdigit() else _NUMBERS[m[1]]
        if m[3] == "day" and m[2]:
            d = base
            for _ in range(n):
                d = next_working_day(d)
            return d
        if m[3] in ("day", "week"):
            return base + timedelta(days=n * (7 if m[3] == "week" else 1))
        y, mo = divmod(base.month - 1 + n, 12)
        return date(base.year + y, mo + 1, min(base.day, calendar.monthrange(base.year + y, mo + 1)[1]))
    for i, name in enumerate(_DAYS):                                                                 # (by / next) Friday
        if re.search(rf"\b{name[:3]}({name[3:]})?\b", t):
            return base + timedelta(days=(i - base.weekday()) % 7 or 7)
    if re.search(r"\b(end of (the |this )?week|this week)\b", t):
        return base + timedelta(days=max(0, 4 - base.weekday()))                                    # that Friday
    if re.search(r"\bnext week\b", t):
        return base + timedelta(days=7 - base.weekday())                                            # the Monday
    if re.search(r"\b(end of (the |this )?month|this month)\b", t):
        return date(base.year, base.month, calendar.monthrange(base.year, base.month)[1])
    if re.search(r"\bnext month\b", t):
        return date(base.year + (base.month == 12), base.month % 12 + 1, 1)
    if m := re.search(r"\b(by|in|before|for|early|mid|late|end of)[ -](?:the )?" + _MON + r"\b", t):   # by November, end of Nov
        mo = _MONTHS[m[2]]
        y = base.year + (mo < base.month)
        last = calendar.monthrange(y, mo)[1]
        return date(y, mo, last if m[1] in ("late", "end of") else 15 if m[1] == "mid" else 1)
    return None


def reminder_due(call: CallRecording, due_text: str | None, today: date | None = None) -> datetime:
    """9am UK time on the day the action item is due (never before today); the next working day when the item
    has no date we can read."""
    today = today or datetime.now(LONDON).date()
    when = call.ended_at or call.started_at or call.created_at
    base = when.astimezone(LONDON).date() if when else today
    d = due_from_text(due_text, base)
    d = max(d, today) if d else next_working_day(today)
    return datetime.combine(d, time(9, 0), tzinfo=LONDON).astimezone(timezone.utc)


def notes_text(call: CallRecording) -> str:
    n = call.notes or {}
    parts = [n.get("summary") or ""]
    if n.get("next_step"):
        parts.append(f"Next step: {n['next_step']}")
    for title, key in (("Key points", "key_points"), ("Decisions", "decisions"), ("Money mentioned", "money_mentioned"),
                       ("Dates mentioned", "dates_mentioned")):
        if n.get(key):
            parts.append(f"{title}:\n" + "\n".join(f"- {x}" for x in n[key]))
    if n.get("action_items"):
        parts.append("To do:\n" + "\n".join(
            f"- {a.get('task')}" + (f" ({a['owner']})" if a.get("owner") else "") + (f", {a['due']}" if a.get("due") else "")
            for a in n["action_items"]))
    if call.participants:
        parts.append("In the call: " + ", ".join(call.participants))
    return "\n\n".join(p for p in parts if p)


def _card(db: Session, call: CallRecording) -> tuple[str | None, uuid.UUID | None, dict]:
    """The card's record and payload, from the call as it is now (who it's linked to can change after the call)."""
    key = f"{KIND}:{call.id}"
    n = call.notes or {}
    contact = db.get(Contact, call.contact_id) if call.contact_id else None
    company = db.get(Company, call.company_id) if call.company_id else None
    details = [{"label": "Call", "value": call.title or "Call", "href": f"/calls/{call.id}"}]
    if contact:
        details.append({"label": "Contact", "value": (contact.full_name or 'Contact'), "href": f"/contacts/{contact.id}"})
    if company:
        details.append({"label": "Company", "value": company.name, "href": f"/companies/{company.id}"})
    details.append({"label": "Summary", "value": n.get("summary") or "No summary"})
    if n.get("next_step"):
        details.append({"label": "Next step", "value": n["next_step"]})
    if n.get("action_items"):
        details.append({"label": "To do", "value": "\n".join(f"{a.get('task')}" + (f" ({a['owner']})" if a.get("owner") else "") for a in n["action_items"])})
    if n.get("money_mentioned"):
        details.append({"label": "Money mentioned", "value": "\n".join(n["money_mentioned"])})
    if call.participants:
        details.append({"label": "In the call", "value": ", ".join(call.participants)})
    who = (contact.full_name or 'Contact') if contact else (company.name if company else None)
    payload = {
        "summary": f"Notes from your call{' with ' + who if who else ''}: {call.title or 'call'}",
        "details": details,
        "call_id": str(call.id),
        "original_text": notes_text(call),
        "related_entities": ([{"type": "company", "id": str(company.id), "label": company.name}] if company else []),
        "facets": {"platform": PLATFORM.get(call.platform or "", "Other"),
                   "interest": SENTIMENT.get(n.get("sentiment") or "neutral", "Neutral"),
                   "linked": "Linked to a contact" if contact else "Not linked to a contact"},
        "sort_date": (call.ended_at or call.created_at or datetime.now(timezone.utc)).date().isoformat(),
        "owner_user_id": str(call.user_id) if call.user_id else None,
        "dedupe_key": key,
    }
    return ("contact" if contact else ("company" if company else None),
            contact.id if contact else (company.id if company else None), payload)


def _cards(db: Session, call: CallRecording, status: str | None = None) -> list[ReviewQueueItem]:
    q = select(ReviewQueueItem).where(ReviewQueueItem.kind == KIND, ReviewQueueItem.payload["dedupe_key"].astext == f"{KIND}:{call.id}")
    return list(db.scalars(q.where(ReviewQueueItem.status == status) if status else q))


def queue_for_review(db: Session, call: CallRecording) -> None:
    if _cards(db, call):
        return
    entity_type, entity_id, payload = _card(db, call)
    db.add(ReviewQueueItem(id=uuid.uuid4(), kind=KIND, status="pending", entity_type=entity_type, entity_id=entity_id, payload=payload))


def refresh_card(db: Session, call: CallRecording) -> None:
    """The call was linked to a contact or company after its card was made: put them on the waiting card."""
    for item in _cards(db, call, "pending"):
        item.entity_type, item.entity_id, payload = _card(db, call)
        item.payload = {**(item.payload or {}), **payload}


def save_to_history(db: Session, call: CallRecording, user_id: uuid.UUID | None, text: str | None = None) -> None:
    from app.models import Reminder
    from app.services.mail_merge import record_history
    if not call.contact_id:
        raise ValueError("This call isn't linked to a contact yet. Link it on the call's page, then save it.")
    if not call.saved_to_history_at:
        record_history(db, call.contact_id, "Meeting Held", call.title or "Call notes", text or notes_text(call), user_id)
        owner = user_id or call.user_id
        for a in (call.notes or {}).get("action_items") or []:
            if owner and a.get("task"):
                db.add(Reminder(id=uuid.uuid4(), user_id=owner, contact_id=call.contact_id, company_id=call.company_id,
                                note=f"{a['task']}" + (f" ({a['due']})" if a.get("due") else "") + f" - from the call: {call.title or 'call'}",
                                due_at=reminder_due(call, a.get("due"))))
        call.saved_to_history_at = datetime.now(timezone.utc)
    # Saved from the call's page: its waiting card is done too (approved, as if "Save to history" was pressed there).
    for item in _cards(db, call, "pending"):
        item.status, item.resolved_action = "approved", "save"
        item.reviewed_at, item.reviewed_by_user_id = datetime.now(timezone.utc), user_id


def _handle(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    call = db.get(CallRecording, uuid.UUID(item.payload["call_id"]))
    if not call:
        raise ValueError("This call no longer exists.")
    if action_id == "save":
        actor = input_data.get("_actor_user_id")
        save_to_history(db, call, uuid.UUID(actor) if actor else None, input_data.get("text") or None)
        return
    if action_id == "dismiss":
        return
    raise ValueError("That action isn't available for call notes.")


register(ReviewKind(
    kind=KIND,
    label="Call notes",
    description="Notes the notetaker wrote after a call, ready to save onto the contact's history.",
    actions=[
        ReviewAction(id="save", label="Save to history", style="primary", outcome="approved"),
        ReviewAction(id="dismiss", label="Not needed", style="secondary", outcome="rejected", reopenable=True),
    ],
    handler=_handle,
    audience="sales",
    facets=(("platform", "Call type"), ("interest", "Their interest"), ("linked", "Contact")),
    date_sort_label="call date",
))
