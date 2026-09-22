"""CS-005 (Returned Copy Processing). A rep photographs a batch of
undeliverable-copy labels returned by the post office; this reads each
label, matches it to an existing contact or company, and proposes either
an address correction or a retirement (moved/closed), with a reason -
never guessed, never applied without a human confirming.

Same shape as business_card.py (upload -> vision -> fuzzy match -> queue),
sharing vision_intake.py's matching helpers. Kept as a separate module
rather than folded into business_card.py because the extraction schema,
the review actions, and the underlying "what does confirming this even
mean" are different enough (an address correction vs. a new-contact
create) that merging them would make both harder to read for no real
code savings.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.automations.llm import extract_json_from_image, is_vision_configured
from app.automations.registry import ExtraField, ReviewAction, ReviewKind, register
from app.automations.vision_intake import MAX_IMAGE_BYTES, encode_image_data_url, find_similar_company, find_similar_contact
from app.models import Address, Company, Contact, ReviewQueueItem

_LABEL_EXTRACTION_PROMPT = """You are reading a single returned-mail label (an undeliverable
magazine/copy returned by the post office). Extract: name, company, address_line1, address_line2,
city, state, postal_code, country, and reference (any customer/subscriber reference number printed
on the label). Use null for anything not present or not legible - never invent a value.

Return JSON of the exact shape: {"name": ..., "company": ..., "address_line1": ..., "address_line2":
..., "city": ..., "state": ..., "postal_code": ..., "country": ..., "reference": ..., "legible": bool}.
Set legible=false if the label is too damaged/blurry to extract anything useful."""


def _entity_and_address(db: Session, item: ReviewQueueItem) -> tuple[Contact | Company | None, Address | None]:
    entity_type = item.payload.get("matched_entity_type")
    entity_id = item.payload.get("matched_entity_id")
    if not entity_type or not entity_id:
        return None, None
    model = Contact if entity_type == "contact" else Company
    entity = db.get(model, uuid.UUID(str(entity_id)))
    if not entity:
        return None, None
    addresses = db.query(Address).filter(
        getattr(Address, f"{entity_type}_id") == entity.id
    ).order_by(Address.is_primary.desc()).all()
    return entity, addresses[0] if addresses else None


def _handle_returned_copy(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    entity, address = _entity_and_address(db, item)
    if not entity:
        raise ValueError("The matched contact/company no longer exists.")
    label = item.payload.get("label") or {}

    if action_id == "correct_address":
        entity_type = item.payload["matched_entity_type"]
        if address:
            address.line1 = label.get("address_line1") or address.line1
            address.line2 = label.get("address_line2") or address.line2
            address.city = label.get("city") or address.city
            address.state = label.get("state") or address.state
            address.postal_code = label.get("postal_code") or address.postal_code
            address.country = label.get("country") or address.country
        else:
            db.add(Address(
                id=uuid.uuid4(), source_db=entity.source_db, source_act_id=str(uuid.uuid4()),
                **{f"{entity_type}_id": entity.id},
                type_label="Business", is_primary=True,
                line1=label.get("address_line1"), line2=label.get("address_line2"),
                city=label.get("city"), state=label.get("state"),
                postal_code=label.get("postal_code"), country=label.get("country"),
            ))

    elif action_id == "retire":
        reason = input_data.get("note", "").strip() or "Returned copy - address no longer valid"
        entity.custom_fields = {
            **(entity.custom_fields or {}),
            "_retired": True,
            "_retired_reason": reason,
            "_retired_at": datetime.now(timezone.utc).isoformat(),
        }

    elif action_id == "dismiss":
        pass

    else:
        raise ValueError(f"Unknown action {action_id!r} for returned_copy")


register(ReviewKind(
    kind="returned_copy",
    label="Returned Print Copies",
    description="Undeliverable printed copies returned from the post room to update addresses or retire stale subscriber records.",
    actions=[
        ReviewAction(id="correct_address", label="Update address", style="primary", outcome="approved"),
        ReviewAction(
            id="retire", label="Retire (moved/closed)", style="secondary", outcome="approved",
            extra_fields=[ExtraField(key="note", label="Reason", placeholder="e.g. company moved", required=False)],
        ),
        ReviewAction(id="dismiss", label="Dismiss (no match)", style="secondary", outcome="rejected"),
    ],
    handler=_handle_returned_copy,
))


def process_returned_copy_photo(
    db: Session, image_bytes: bytes, content_type: str, *, source_db: str
) -> dict:
    """Called directly by the upload route - see business_card.py's
    process_business_card_photo() for the same shape and reasoning."""
    if len(image_bytes) > MAX_IMAGE_BYTES:
        return {"queued": 0, "error": "Image too large (max 8MB)."}
    if not is_vision_configured():
        return {"queued": 0, "error": "Vision AI isn't configured (no API key for the selected provider) - label reading needs it."}

    data_url = encode_image_data_url(image_bytes, content_type)
    label = extract_json_from_image(_LABEL_EXTRACTION_PROMPT, data_url, purpose="returned_copy.label_extraction")
    if label is None or not isinstance(label, dict):
        return {"queued": 0, "error": "Couldn't read this label - try a clearer photo."}
    if label.get("legible") is False:
        return {"queued": 0, "error": "Label too damaged/blurry to read."}

    contact = find_similar_contact(db, name=label.get("name"), company_name=label.get("company"), source_db=source_db)
    company = None if contact else find_similar_company(db, name=label.get("company"), source_db=source_db)
    matched = contact or company
    matched_type = "contact" if contact else ("company" if company else None)

    if not matched:
        db.add(ReviewQueueItem(
            id=uuid.uuid4(), kind="returned_copy", entity_type=None, entity_id=None,
            payload={
                "summary": f"Returned copy for \"{label.get('name') or label.get('company') or '(unreadable)'}\""
                           " - no match found in the CRM",
                "details": [
                    {"key": "address", "label": "Address on label",
                     "value": ", ".join(filter(None, [label.get("address_line1"), label.get("city"), label.get("postal_code")])) or "-"},
                ],
                "label": label, "matched_entity_type": None, "matched_entity_id": None,
                "confidence": None,
            },
        ))
        db.commit()
        return {"queued": 1, "matched": False}

    matched_label = matched.full_name if contact else matched.name
    db.add(ReviewQueueItem(
        id=uuid.uuid4(), kind="returned_copy",
        entity_type=matched_type, entity_id=matched.id,
        payload={
            "summary": f"Returned copy for {matched_label or '(unnamed)'}",
            "details": [
                {"key": "new_address", "label": "Address on label",
                 "value": ", ".join(filter(None, [label.get("address_line1"), label.get("city"), label.get("postal_code")])) or "-"},
                {"key": "reference", "label": "Reference", "value": label.get("reference") or "-"},
            ],
            "related_entities": [{"type": matched_type, "id": str(matched.id), "label": matched_label or "matched record"}],
            "label": label, "matched_entity_type": matched_type, "matched_entity_id": str(matched.id),
            "confidence": 0.75,
        },
    ))
    db.commit()
    return {"queued": 1, "matched": True}
