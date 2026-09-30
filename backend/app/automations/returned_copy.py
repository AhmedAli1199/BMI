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

_LABEL_EXTRACTION_PROMPT = """You are reading one or more returned-mail items (undeliverable magazine copies, envelopes, or mailing labels returned to the publisher by the post office).

CRITICAL INSTRUCTIONS:
1. Do NOT extract "BMI Publishing" or "14 Lumley Gardens, Cheam, Sutton" - that is the PUBLISHER'S OWN RETURN ADDRESS printed on the mailer.
2. For EACH distinct returned copy, envelope, or mailing label visible in the photo, extract the recipient/subscriber details:
   - name: Full name of the recipient/subscriber (e.g. "Michelle Waters", "The Manager"). If no person name is given, use null.
   - company: Company or organisation name (e.g. "Travel Counsellors", "Templeworld Ltd").
   - address_line1: Street address line (e.g. "Westmead, Aqueduct Lane", "13 The Avenue").
   - address_line2: Secondary address line or locality if present (e.g. "Alvechurch").
   - city: Town or City (e.g. "Birmingham", "Richmond").
   - state: County, Region, or State (e.g. "West Midlands", "Surrey").
   - postal_code: Postcode or ZIP code (e.g. "B48 7BS", "TW9 2AL").
   - country: Country if present (e.g. "United Kingdom").
   - reference: Any subscriber reference, barcode number, or print run code printed on the label (e.g. "27194 / 01 / 0004602 / 34400 / 024F1BHD1000336 /" or "34836 / 01 / 0002632 / 37800 / 024F1Y9YF00078 /").
   - return_reason: Any handwritten, stamped, or sticker return reason (e.g. "Please return", "Gone away", "Moved", "Refused").
3. Postal markings: Ignore pen strokes, crossing-out lines, stamps, and handwritten notes that overlap the printed address - extract whatever printed recipient details remain readable beneath or around them.
4. If the photo contains multiple envelopes or labels, extract an entry for each one.
5. If the image is rotated (sideways or upside down), still extract the text accurately.

Return JSON of the exact shape:
{
  "labels": [
    {
      "name": ... | null,
      "company": ... | null,
      "address_line1": ... | null,
      "address_line2": ... | null,
      "city": ... | null,
      "state": ... | null,
      "postal_code": ... | null,
      "country": ... | null,
      "reference": ... | null,
      "return_reason": ... | null
    }
  ]
}
If no returned mail labels or recipient addresses are visible at all, return {"labels": []}."""


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
    if action_id == "dismiss":
        return

    entity, address = _entity_and_address(db, item)
    # If not automatically matched, check if reviewer provided a manual contact_id
    if not entity and input_data.get("contact_id"):
        entity = db.get(Contact, uuid.UUID(str(input_data["contact_id"])))
        if entity:
            addresses = db.query(Address).filter(Address.contact_id == entity.id).order_by(Address.is_primary.desc()).all()
            address = addresses[0] if addresses else None
            item.entity_type, item.entity_id = "contact", entity.id
            item.payload["matched_entity_type"] = "contact"
            item.payload["matched_entity_id"] = str(entity.id)

    if not entity:
        raise ValueError("No matched contact/company found on this record to update or retire.")
    label = item.payload.get("label") or {}

    if action_id == "correct_address":
        entity_type = item.payload.get("matched_entity_type") or "contact"
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
    """Called directly by the upload route - reads one or more returned-mail
    labels photographed together, matches each against contacts/companies in
    the selected database, and queues review items for human confirmation."""
    if len(image_bytes) > MAX_IMAGE_BYTES:
        return {"labels_found": 0, "queued": 0, "error": "Image too large (max 8MB)."}
    if not is_vision_configured():
        return {"labels_found": 0, "queued": 0, "error": "Vision AI isn't configured (no API key for the selected provider) - label reading needs it."}

    data_url = encode_image_data_url(image_bytes, content_type)
    result = extract_json_from_image(_LABEL_EXTRACTION_PROMPT, data_url, purpose="returned_copy.label_extraction")

    # Handle multiple returned format shapes gracefully:
    # 1. {"labels": [...]}
    # 2. Top-level list: [{...}, {...}]
    # 3. Single legacy dict: {"name": ..., "company": ...}
    raw_labels: list[dict] = []
    if isinstance(result, dict):
        if "labels" in result and isinstance(result["labels"], list):
            raw_labels = [item for item in result["labels"] if isinstance(item, dict)]
        elif any(k in result for k in ("name", "company", "address_line1", "postal_code")):
            raw_labels = [result]
    elif isinstance(result, list):
        raw_labels = [item for item in result if isinstance(item, dict)]

    # Filter out empty or publisher-only items
    valid_labels: list[dict] = []
    for l in raw_labels:
        comp = (l.get("company") or "").strip().lower()
        addr = (l.get("address_line1") or "").strip().lower()
        # Skip if the model accidentally captured BMI Publishing itself
        if "bmi publishing" in comp or "14 lumley" in addr:
            continue
        has_recipient = any(
            (l.get(k) or "").strip()
            for k in ("name", "company", "address_line1", "postal_code", "reference")
        )
        if has_recipient:
            valid_labels.append(l)

    if not valid_labels:
        return {
            "labels_found": 0,
            "queued": 0,
            "error": "Couldn't detect any readable returned-mail labels in this photo - please try a clearer photo.",
        }

    queued = 0
    matched_count = 0
    for label in valid_labels:
        contact = find_similar_contact(
            db, name=label.get("name"), company_name=label.get("company"), source_db=source_db
        )
        company = None if contact else find_similar_company(db, name=label.get("company"), source_db=source_db)
        matched = contact or company
        matched_type = "contact" if contact else ("company" if company else None)

        address_parts = [
            label.get("address_line1"),
            label.get("address_line2"),
            label.get("city"),
            label.get("state"),
            label.get("postal_code"),
            label.get("country"),
        ]
        formatted_address = ", ".join(filter(None, address_parts)) or "-"

        details = [
            {"key": "address", "label": "Address on label", "value": formatted_address},
        ]
        if label.get("company"):
            details.append({"key": "company", "label": "Company on label", "value": label["company"]})
        if label.get("name"):
            details.append({"key": "name", "label": "Recipient name", "value": label["name"]})
        if label.get("reference"):
            details.append({"key": "reference", "label": "Reference / Code", "value": label["reference"]})
        if label.get("return_reason"):
            details.append({"key": "return_reason", "label": "Return note / reason", "value": label["return_reason"]})

        if not matched:
            display_name = label.get("name") or label.get("company") or "Unknown recipient"
            db.add(ReviewQueueItem(
                id=uuid.uuid4(), kind="returned_copy", source_db=source_db, entity_type=None, entity_id=None,
                payload={
                    "summary": f"Returned copy for \"{display_name}\" - no match found in {source_db}",
                    "details": details,
                    "label": label,
                    "matched_entity_type": None,
                    "matched_entity_id": None,
                    "confidence": None,
                    "source_db": source_db,
                },
            ))
            queued += 1
        else:
            matched_count += 1
            matched_label = matched.full_name if contact else matched.name
            db.add(ReviewQueueItem(
                id=uuid.uuid4(), kind="returned_copy", source_db=source_db,
                entity_type=matched_type, entity_id=matched.id,
                payload={
                    "summary": f"Returned copy for {matched_label or '(unnamed)'}",
                    "details": details,
                    "related_entities": [{"type": matched_type, "id": str(matched.id), "label": matched_label or "matched record"}],
                    "label": label,
                    "matched_entity_type": matched_type,
                    "matched_entity_id": str(matched.id),
                    "confidence": 0.85 if contact else 0.75,
                    "source_db": source_db,
                },
            ))
            queued += 1

    db.commit()
    return {
        "labels_found": len(valid_labels),
        "queued": queued,
        "matched": matched_count > 0,
        "matched_count": matched_count,
    }
