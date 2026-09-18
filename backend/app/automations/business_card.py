"""SALES-001/002 (Business Card Reading & Extraction + Dedupe/Group
Assignment), merged into one automation - matches how the original spec
described them (001 feeds directly into 002) and avoids a pointless
staging table in between for what's really one user-facing action:
"I photographed some cards, tell me what you found."

Trigger: a rep uploads photo(s) via the CRM (see
app/api/routes/automations_intake.py's /business-cards endpoint) - not a
scheduled scan, since there's nothing to poll for. process_business_card_photo()
is called directly by that route.

Multi-card photos are supported - the vision prompt asks for an array, one
entry per card visible in the image, since a trade-show photo often has
several cards laid out together.

Every card becomes exactly one review item, whether it's a brand-new
contact or one that already looks like it exists (matched via
vision_intake.py's fuzzy name lookup, scoped to the uploading session's
publication so a match never crosses source_db). Nothing is written to
the CRM until a human confirms - same guardrail as every other automation
here.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.api.schemas import MANUAL_SOURCE_DB
from app.automations.llm import extract_json_from_image, is_configured
from app.automations.registry import ReviewAction, ReviewKind, register
from app.automations.vision_intake import MAX_IMAGE_BYTES, encode_image_data_url, find_similar_company, find_similar_contact
from app.models import Contact, Email, Note, Phone, ReviewQueueItem

_CARD_EXTRACTION_PROMPT = """You are reading one or more business cards photographed together in a
single image. For EACH distinct card visible, extract: first_name, last_name, company, job_title,
email, phone. If a field isn't visible or legible, use null for it - never guess or invent a value.
Set needs_review=true on any card where the name or company is unclear, handwritten illegibly, or
the card is only partially visible.

Return JSON of the exact shape: {"cards": [{"first_name": ..., "last_name": ..., "company": ...,
"job_title": ..., "email": ..., "phone": ..., "needs_review": bool}]}. If you see zero readable
cards, return {"cards": []}."""


def _add_note(db: Session, contact: Contact, body: str) -> None:
    db.add(Note(
        id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()),
        entity_type="contact", entity_id=contact.id,
        note_type="Trade Show", body=body, act_created_at=datetime.now(timezone.utc),
    ))


def _handle_new_contact(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "dismiss":
        return
    if action_id != "add_contact":
        raise ValueError(f"Unknown action {action_id!r} for business_card_new")

    card = item.payload.get("card") or {}
    source_db = item.payload.get("source_db") or MANUAL_SOURCE_DB
    first_name, last_name = card.get("first_name"), card.get("last_name")
    full_name = " ".join(filter(None, [first_name, last_name])) or None

    company_id = None
    company_name = card.get("company")
    if company_name:
        existing_company = find_similar_company(db, name=company_name, source_db=source_db)
        company_id = existing_company.id if existing_company else None

    contact = Contact(
        id=uuid.uuid4(), source_db=source_db, source_act_id=str(uuid.uuid4()),
        first_name=first_name, last_name=last_name, full_name=full_name,
        job_title=card.get("job_title"), company_id=company_id,
        company_name_freetext=None if company_id else company_name,
        custom_fields={},
    )
    db.add(contact)
    db.flush()

    if card.get("email"):
        db.add(Email(id=uuid.uuid4(), source_db=source_db, source_act_id=str(uuid.uuid4()),
                      contact_id=contact.id, address=card["email"], is_primary=True))
    if card.get("phone"):
        db.add(Phone(id=uuid.uuid4(), source_db=source_db, source_act_id=str(uuid.uuid4()),
                      contact_id=contact.id, number=card["phone"], is_primary=True))

    show = item.payload.get("show_context") or "trade show"
    _add_note(db, contact, f"Card collected at {show}.")


def _handle_existing_contact(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "dismiss":
        return
    if action_id != "log_seen":
        raise ValueError(f"Unknown action {action_id!r} for business_card_existing")
    contact = db.get(Contact, item.entity_id) if item.entity_id else None
    if not contact:
        raise ValueError("This contact no longer exists.")
    show = item.payload.get("show_context") or "trade show"
    _add_note(db, contact, f"Card collected again at {show} - already in the CRM, logged for the record.")


register(ReviewKind(
    kind="business_card_new",
    label="Business card - new contact",
    description="A photographed business card didn't match anyone already in the CRM.",
    actions=[
        ReviewAction(id="add_contact", label="Add as new contact", style="primary", outcome="approved"),
        ReviewAction(id="dismiss", label="Skip", style="destructive", outcome="rejected"),
    ],
    handler=_handle_new_contact,
))

register(ReviewKind(
    kind="business_card_existing",
    label="Business card - already in CRM",
    description="A photographed business card matched someone already in the CRM.",
    actions=[
        ReviewAction(id="log_seen", label="Log as seen", style="primary", outcome="approved"),
        ReviewAction(id="dismiss", label="Skip", style="destructive", outcome="rejected"),
    ],
    handler=_handle_existing_contact,
))


def process_business_card_photo(
    db: Session, image_bytes: bytes, content_type: str, *, source_db: str, show_context: str | None = None
) -> dict:
    """Called directly by the upload route - not a scheduled job. Returns a
    small summary dict for the route to hand back to the frontend
    immediately (how many cards found, how many queued, any that failed to
    read at all)."""
    if len(image_bytes) > MAX_IMAGE_BYTES:
        return {"cards_found": 0, "queued": 0, "error": "Image too large (max 8MB)."}
    if not is_configured():
        return {"cards_found": 0, "queued": 0, "error": "AI drafting isn't configured (no OpenAI key) - card reading needs it."}

    data_url = encode_image_data_url(image_bytes, content_type)
    result = extract_json_from_image(_CARD_EXTRACTION_PROMPT, data_url)
    if result is None:
        return {"cards_found": 0, "queued": 0, "error": "Couldn't read this image - try a clearer photo."}

    cards = result.get("cards", []) if isinstance(result, dict) else []
    queued = 0
    for card in cards:
        full_name = " ".join(filter(None, [card.get("first_name"), card.get("last_name")])) or None
        match = find_similar_contact(db, name=full_name, company_name=card.get("company"), source_db=source_db)

        kind = "business_card_existing" if match else "business_card_new"
        label = full_name or "(name not legible)"
        db.add(ReviewQueueItem(
            id=uuid.uuid4(),
            kind=kind,
            entity_type="contact" if match else None,
            entity_id=match.id if match else None,
            payload={
                "summary": f"{label}" + (f" at {card['company']}" if card.get("company") else "")
                           + (" - matched an existing contact" if match else " - new contact"),
                "details": [
                    {"key": "company", "label": "Company", "value": card.get("company") or "-"},
                    {"key": "job_title", "label": "Title", "value": card.get("job_title") or "-"},
                    {"key": "email", "label": "Email", "value": card.get("email") or "-"},
                    {"key": "phone", "label": "Phone", "value": card.get("phone") or "-"},
                ],
                "related_entities": (
                    [{"type": "contact", "id": str(match.id), "label": full_name or "existing contact"}]
                    if match else []
                ),
                "card": card,
                "source_db": source_db,
                "show_context": show_context,
                "confidence": 0.5 if card.get("needs_review") else 0.85,
            },
        ))
        queued += 1

    db.commit()
    return {"cards_found": len(cards), "queued": queued}
