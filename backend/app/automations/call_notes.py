"""Call notes: when the notetaker finishes a call, the notes land in the salesperson's review queue.
"Save to history" writes them onto the contact's history (and a reminder for each thing they said
they'd do); "Not needed" just closes the card. The notes stay on the call's own page either way."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automations.registry import ReviewAction, ReviewKind, register
from app.models import CallRecording, Company, Contact, ReviewQueueItem

KIND = "call_notes"
PLATFORM = {"google_meet": "Google Meet", "teams": "Microsoft Teams", "zoom": "Zoom"}
SENTIMENT = {"positive": "Interested", "neutral": "Neutral", "negative": "Not keen"}


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


def queue_for_review(db: Session, call: CallRecording) -> None:
    key = f"{KIND}:{call.id}"
    if db.scalar(select(ReviewQueueItem.id).where(ReviewQueueItem.kind == KIND, ReviewQueueItem.payload["dedupe_key"].astext == key)):
        return
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
    db.add(ReviewQueueItem(
        id=uuid.uuid4(), kind=KIND, status="pending",
        entity_type="contact" if contact else ("company" if company else None),
        entity_id=contact.id if contact else (company.id if company else None),
        payload={
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
        },
    ))


def save_to_history(db: Session, call: CallRecording, user_id: uuid.UUID | None, text: str | None = None) -> None:
    from app.models import Reminder
    from app.services.mail_merge import record_history
    if not call.contact_id:
        raise ValueError("This call isn't linked to a contact yet. Link it on the call's page, then save it.")
    if call.saved_to_history_at:
        return
    record_history(db, call.contact_id, "Meeting Held", call.title or "Call notes", text or notes_text(call), user_id)
    owner = user_id or call.user_id
    for a in (call.notes or {}).get("action_items") or []:
        if owner and a.get("task"):
            db.add(Reminder(id=uuid.uuid4(), user_id=owner, contact_id=call.contact_id, company_id=call.company_id,
                            note=f"{a['task']}" + (f" ({a['due']})" if a.get("due") else "") + f" - from the call: {call.title or 'call'}",
                            due_at=datetime.now(timezone.utc) + timedelta(days=1)))
    call.saved_to_history_at = datetime.now(timezone.utc)


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
