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
contact or one that already looks like it exists. Matching follows the
spec's priority order: an exact email match first (skipped for a
generic/shared inbox address like info@ or sales@, which tells us nothing
about who the card belongs to), falling back to vision_intake.py's fuzzy
name+company lookup - scoped to the uploading session's publication so a
match never crosses source_db. Nothing is written to the CRM until a
human confirms - same guardrail as every other automation here.

A matched existing contact gets its card fields diffed against what's
already stored (job title, email, phone, company) - only fields that
actually changed are surfaced, and applying them is its own explicit
action, never automatic. A brand-new contact gets up to three "suggested
groups" from the same curated allowlist SALES-011 uses (see
group_allowlist.py) - the reviewer can accept, edit, or clear them before
confirming.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.schemas import MANUAL_SOURCE_DB
from app.automations.contact_match import find_contact_by_email
from app.automations.group_allowlist import ALLOWLISTED_GROUPS, suggest_groups
from app.automations.llm import extract_json_from_image, is_vision_configured
from app.automations.registry import ExtraField, ReviewAction, ReviewKind, get_action, get_kind, register
from app.automations.teams_notify import post_summary
from app.automations.vision_intake import MATCH_THRESHOLD, MAX_IMAGE_BYTES, encode_image_data_url, find_similar_company, find_similar_contact
from app.models import Company, Contact, Email, Group, GroupMembership, Note, Phone, ReviewQueueItem

# Shared/generic inbox addresses tell us nothing about who a card belongs
# to - "info@bigcorp.com" matching some unrelated existing contact who
# once used that inbox would be a false positive, so these never drive an
# email match; the name+company heuristic still applies as normal.
_GENERIC_EMAIL_PREFIXES = {"info", "enquiries", "enquiry", "sales", "contact", "admin", "hello", "office", "support"}


def _is_generic_email(email: str | None) -> bool:
    if not email or "@" not in email:
        return False
    return email.split("@", 1)[0].strip().lower() in _GENERIC_EMAIL_PREFIXES


def _match_existing_contact(db: Session, *, name: str | None, company_name: str | None, email: str | None, source_db: str) -> Contact | None:
    """Email match first (spec's priority order), then the fuzzy name+company
    heuristic - matching bounce_handling.py/email_summary.py's own
    "try the strong signal first, fall back to the weak one" shape."""
    if email and not _is_generic_email(email):
        by_email = find_contact_by_email(db, email)
        if by_email and by_email.source_db == source_db:
            return by_email
    return find_similar_contact(db, name=name, company_name=company_name, source_db=source_db)


def _primary_or_first(db: Session, model, contact_id):
    return (
        db.query(model).filter(model.contact_id == contact_id, model.is_primary.is_(True)).first()
        or db.query(model).filter(model.contact_id == contact_id).first()
    )


def _current_company_name(db: Session, contact: Contact) -> str | None:
    if contact.company_id:
        company = db.get(Company, contact.company_id)
        return company.name if company else None
    return contact.company_name_freetext


def _diff_card_against_contact(db: Session, contact: Contact, card: dict) -> list[dict]:
    """What the card says that's actually different from what's already
    stored - only non-empty card values that disagree with the stored
    value are surfaced, so a blank/illegible field on the card never looks
    like "delete this."""
    changed: list[dict] = []

    if card.get("job_title") and card["job_title"].strip().lower() != (contact.job_title or "").strip().lower():
        changed.append({"key": "job_title", "label": "Job title", "old": contact.job_title or "-", "new": card["job_title"]})

    email_row = _primary_or_first(db, Email, contact.id)
    stored_email = (email_row.address if email_row else None) or ""
    if card.get("email") and card["email"].strip().lower() != stored_email.strip().lower():
        changed.append({"key": "email", "label": "Email", "old": stored_email or "-", "new": card["email"]})

    phone_row = _primary_or_first(db, Phone, contact.id)
    stored_phone = (phone_row.number if phone_row else None) or ""
    if card.get("phone") and card["phone"].strip() != stored_phone.strip():
        changed.append({"key": "phone", "label": "Phone", "old": stored_phone or "-", "new": card["phone"]})

    stored_company = _current_company_name(db, contact)
    if card.get("company") and card["company"].strip().lower() != (stored_company or "").strip().lower():
        changed.append({"key": "company", "label": "Company", "old": stored_company or "-", "new": card["company"]})

    return changed


def _apply_field_change(db: Session, contact: Contact, source_db: str, field: dict, card: dict) -> None:
    key = field.get("key")
    if key == "job_title":
        contact.job_title = card.get("job_title")
    elif key == "email" and card.get("email"):
        row = db.query(Email).filter(Email.contact_id == contact.id, Email.is_primary.is_(True)).first()
        if row:
            row.address = card["email"]
        else:
            db.add(Email(id=uuid.uuid4(), source_db=contact.source_db, source_act_id=str(uuid.uuid4()),
                          contact_id=contact.id, address=card["email"], is_primary=True))
    elif key == "phone" and card.get("phone"):
        row = db.query(Phone).filter(Phone.contact_id == contact.id, Phone.is_primary.is_(True)).first()
        if row:
            row.number = card["phone"]
        else:
            db.add(Phone(id=uuid.uuid4(), source_db=contact.source_db, source_act_id=str(uuid.uuid4()),
                          contact_id=contact.id, number=card["phone"], is_primary=True))
    elif key == "company" and card.get("company"):
        matched_company = find_similar_company(db, name=card["company"], source_db=source_db)
        contact.company_id = matched_company.id if matched_company else None
        contact.company_name_freetext = None if matched_company else card["company"]


def _cards_look_like_duplicates(db: Session, a: dict, b: dict) -> bool:
    """Two cards from the SAME upload that are almost certainly the same
    person - a trade-show table sometimes hands over two cards for one
    person (a personal one and a company one), or a card gets photographed
    twice by mistake. Deliberately conservative: a name match alone isn't
    enough if the two cards name different companies (the spec's own "same
    person, different company - not a dupe" edge case)."""
    name_a = " ".join(filter(None, [a.get("first_name"), a.get("last_name")])).strip()
    name_b = " ".join(filter(None, [b.get("first_name"), b.get("last_name")])).strip()
    if not name_a or not name_b:
        return False
    similarity = db.execute(text("SELECT similarity(:a, :b)"), {"a": name_a, "b": name_b}).scalar() or 0.0
    if similarity < MATCH_THRESHOLD:
        return False
    company_a, company_b = (a.get("company") or "").strip().lower(), (b.get("company") or "").strip().lower()
    if company_a and company_b and company_a != company_b:
        return False
    return True


def _dedupe_within_batch(db: Session, cards: list[dict]) -> tuple[list[dict], int]:
    """Collapses cards that look like the same person into one, filling
    any field the kept card is missing from the one it absorbed. Returns
    (deduped cards, how many were folded in)."""
    kept: list[dict] = []
    skipped = 0
    for card in cards:
        match = next((k for k in kept if _cards_look_like_duplicates(db, k, card)), None)
        if match:
            for key in ("email", "phone", "job_title", "company"):
                if not match.get(key) and card.get(key):
                    match[key] = card[key]
            skipped += 1
            continue
        kept.append(card)
    return kept, skipped


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

    # Whatever the reviewer typed (pre-filled from suggestions computed
    # against the company just matched/created above) is only ever applied
    # if it resolves to a real, allowlisted group - a typo or a
    # non-allowlisted name is silently skipped, never created as a new group.
    requested_names = {n.strip().lower() for n in (input_data.get("groups") or "").split(",") if n.strip()}
    for group_name in requested_names:
        if group_name not in ALLOWLISTED_GROUPS.get(source_db, set()):
            continue
        group = db.query(Group).filter(Group.source_db == source_db, Group.name.ilike(group_name)).first()
        if group:
            db.add(GroupMembership(id=uuid.uuid4(), group_id=group.id, contact_id=contact.id))

    show = item.payload.get("show_context") or "trade show"
    _add_note(db, contact, f"Card collected at {show}.")


def _handle_existing_contact(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    if action_id == "dismiss":
        return
    contact = db.get(Contact, item.entity_id) if item.entity_id else None
    if not contact:
        raise ValueError("This contact no longer exists.")
    show = item.payload.get("show_context") or "trade show"

    if action_id == "log_seen":
        _add_note(db, contact, f"Card collected again at {show} - already in the CRM, logged for the record.")
    elif action_id == "update_contact":
        changed = item.payload.get("changed_fields") or []
        if not changed:
            raise ValueError("No changes were detected on this card to apply.")
        card = item.payload.get("card") or {}
        source_db = item.payload.get("source_db") or contact.source_db
        for field in changed:
            _apply_field_change(db, contact, source_db, field, card)
        applied = ", ".join(f["label"].lower() for f in changed)
        _add_note(db, contact, f"Details updated from a card collected again at {show}: {applied}.")
    else:
        raise ValueError(f"Unknown action {action_id!r} for business_card_existing")


register(ReviewKind(
    kind="business_card_new",
    label="New Business Card Leads",
    description="Trade show and event business cards detected as new prospective contacts.",
    actions=[
        ReviewAction(
            id="add_contact", label="Create contact", style="primary", outcome="approved",
            extra_fields=[
                ExtraField(key="groups", label="Groups to add (comma-separated)", placeholder="e.g. London, Airline Catering", required=False),
            ],
        ),
        ReviewAction(id="dismiss", label="Skip", style="secondary", outcome="rejected"),
    ],
    handler=_handle_new_contact,
))

register(ReviewKind(
    kind="business_card_existing",
    label="Business Card Contact Updates",
    description="Trade show cards matching existing contacts with updated titles, phones, or details.",
    actions=[
        ReviewAction(id="update_contact", label="Apply updated details", style="primary", outcome="approved"),
        ReviewAction(id="log_seen", label="Log event meeting (keep existing)", style="secondary", outcome="approved"),
        ReviewAction(id="dismiss", label="Skip", style="secondary", outcome="rejected"),
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
    if not is_vision_configured():
        return {"cards_found": 0, "queued": 0, "error": "Vision AI isn't configured (no API key for the selected provider) - card reading needs it."}

    data_url = encode_image_data_url(image_bytes, content_type)
    result = extract_json_from_image(_CARD_EXTRACTION_PROMPT, data_url, purpose="business_card.extraction")
    if result is None:
        return {"cards_found": 0, "queued": 0, "error": "Couldn't read this image - try a clearer photo."}

    raw_cards = result.get("cards", []) if isinstance(result, dict) else []
    cards, skipped_duplicates = _dedupe_within_batch(db, raw_cards)
    batch_id = str(uuid.uuid4())
    queued = 0
    for card in cards:
        full_name = " ".join(filter(None, [card.get("first_name"), card.get("last_name")])) or None
        match = _match_existing_contact(
            db, name=full_name, company_name=card.get("company"), email=card.get("email"), source_db=source_db,
        )

        kind = "business_card_existing" if match else "business_card_new"
        label = full_name or "(name not legible)"
        details = [
            {"key": "company", "label": "Company", "value": card.get("company") or "-"},
            {"key": "job_title", "label": "Title", "value": card.get("job_title") or "-"},
            {"key": "email", "label": "Email", "value": card.get("email") or "-"},
            {"key": "phone", "label": "Phone", "value": card.get("phone") or "-"},
        ]

        extra_payload: dict = {}
        if match:
            changed_fields = _diff_card_against_contact(db, match, card)
            extra_payload["changed_fields"] = changed_fields
            if changed_fields:
                details.append({
                    "key": "changes", "label": "Changed since last seen",
                    "value": "; ".join(f"{f['label']}: {f['old']} → {f['new']}" for f in changed_fields),
                })
        else:
            company_match = find_similar_company(db, name=card.get("company"), source_db=source_db) if card.get("company") else None
            suggested = suggest_groups(db, source_db, company_match.id) if company_match else []
            extra_payload["suggested_groups"] = [g.name for g in suggested]
            if suggested:
                details.append({"key": "suggested_groups", "label": "Suggested groups", "value": ", ".join(g.name for g in suggested)})

        db.add(ReviewQueueItem(
            id=uuid.uuid4(),
            kind=kind,
            entity_type="contact" if match else None,
            entity_id=match.id if match else None,
            payload={
                "summary": f"{label}" + (f" at {card['company']}" if card.get("company") else "")
                           + (" - matched an existing contact" if match else " - new contact"),
                "details": details,
                "related_entities": (
                    [{"type": "contact", "id": str(match.id), "label": full_name or "existing contact"}]
                    if match else []
                ),
                "card": card,
                "source_db": source_db,
                "show_context": show_context,
                "batch_id": batch_id,
                "confidence": 0.5 if card.get("needs_review") else 0.85,
                **extra_payload,
            },
        ))
        queued += 1

    db.commit()
    return {
        "cards_found": len(raw_cards), "queued": queued,
        "skipped_duplicates": skipped_duplicates, "batch_id": batch_id,
    }


def resolve_batch(db: Session, batch_id: str) -> dict:
    """SALES-002's "one review-list confirmation writes the batch": resolves
    every still-pending business-card item from this batch_id with its
    sensible default action - "Add as new contact" (using the groups
    already suggested at queue time) for a new card, "Apply detected
    changes" for an existing match with real diffs, "Log as seen" for one
    with none. A reviewer who already resolved specific items individually
    (to override a suggestion, or to skip one) leaves those untouched -
    this only ever picks up what's still pending. One bad row never sinks
    the batch: it's counted as failed and the rest still go through."""
    items = (
        db.query(ReviewQueueItem)
        .filter(
            ReviewQueueItem.status == "pending",
            ReviewQueueItem.kind.in_(["business_card_new", "business_card_existing"]),
            ReviewQueueItem.payload["batch_id"].astext == batch_id,
        )
        .all()
    )
    if not items:
        raise ValueError(f"No pending business-card items found for batch {batch_id!r} - it may already be confirmed.")

    added = updated = logged = failed = 0
    failures: list[dict] = []
    for item in items:
        if item.kind == "business_card_new":
            action_id = "add_contact"
            input_data = {"groups": ", ".join(item.payload.get("suggested_groups") or [])}
        else:
            has_changes = bool(item.payload.get("changed_fields"))
            action_id = "update_contact" if has_changes else "log_seen"
            input_data = {}

        kind_def = get_kind(item.kind)
        action = get_action(item.kind, action_id)
        try:
            kind_def.handler(db, item, action_id, input_data)
        except ValueError as exc:
            failed += 1
            failures.append({"item_id": str(item.id), "error": str(exc)})
            continue

        item.status = action.outcome
        item.resolved_action = action_id
        item.reviewed_at = datetime.now(timezone.utc)
        item.review_note = "Resolved via batch confirm (SALES-002)."

        if item.kind == "business_card_new":
            added += 1
        elif action_id == "update_contact":
            updated += 1
        else:
            logged += 1

    db.commit()

    show = items[0].payload.get("show_context") or "a trade show"
    summary_line = (
        f"Business card batch confirmed for {show}: {added} added, {updated} updated, "
        f"{logged} logged (no changes), {failed} failed."
    )
    post_summary(db, summary_line)

    return {
        "batch_id": batch_id, "added": added, "updated": updated,
        "logged": logged, "failed": failed, "failures": failures,
    }
