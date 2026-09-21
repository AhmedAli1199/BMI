"""SALES-013 (Morning Follow-Up Queue) - see docs/build-spec.txt.

Deliberately NOT a new producer: there's nothing new to extract here.
SALES-012 (signal_triggers.py) already turns budget_window/renewal_date/
promised_callback signals into `signal_trigger` review items once they're
due, and the pre-existing Follow-up Engine (followup_queue.py) already
turns due/overdue Activities into `followup_due` review items. This
module is purely a read-side aggregation: pull every still-pending item
from both, resolve which salesperson it belongs to (via Contact.
owner_user_id - the whole reason the record-manager backfill mattered),
and hand back one flat, owner-labeled list for the frontend to group into
"your list for today" - no new database writes, no new review-queue kind.

An item whose contact/company has no resolvable owner_user_id (an
un-backfilled contact, or a followup_due item tied to a company rather
than a contact - companies don't carry ownership) is labeled "Unassigned"
rather than dropped, so nothing silently disappears from the queue.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Contact, ReviewQueueItem, User

_SOURCE_KINDS = ("signal_trigger", "followup_due")


def _resolve_owner(db: Session, item: ReviewQueueItem) -> tuple[str | None, str]:
    """(owner_user_id, owner_name) for one pending item, or (None,
    "Unassigned") when it can't be resolved."""
    contact_id = None
    if item.entity_type == "contact" and item.entity_id:
        contact_id = item.entity_id
    else:
        related = next((e for e in (item.payload.get("related_entities") or []) if e.get("type") == "contact"), None)
        if related and related.get("id"):
            contact_id = related["id"]

    if not contact_id:
        return None, "Unassigned"

    contact = db.get(Contact, contact_id)
    if not contact or not contact.owner_user_id:
        return None, "Unassigned"

    owner = db.get(User, contact.owner_user_id)
    return (str(contact.owner_user_id), owner.name if owner else "Unassigned")


def build_today_queue(db: Session, owner_user_id: str | None = None) -> list[dict]:
    """Every pending signal_trigger/followup_due item, each tagged with
    who it belongs to. If owner_user_id is given, scoped to that rep's own
    items (a rep's "my list for today"); omitted, every item is returned
    grouped-ready (a manager's cross-team view)."""
    items = (
        db.query(ReviewQueueItem)
        .filter(ReviewQueueItem.kind.in_(_SOURCE_KINDS), ReviewQueueItem.status == "pending")
        .order_by(ReviewQueueItem.created_at.asc())
        .all()
    )

    results = []
    for item in items:
        owner_id, owner_name = _resolve_owner(db, item)
        if owner_user_id and owner_id != owner_user_id:
            continue
        results.append({
            # Same shape as ReviewQueueItemOut (see api/schemas.py) so the
            # frontend can feed one of these straight into the same
            # ReviewItemCard the review queue itself uses - one less
            # rendering/action path to maintain.
            "id": str(item.id),
            "kind": item.kind,
            "entity_type": item.entity_type,
            "entity_id": str(item.entity_id) if item.entity_id else None,
            "payload": item.payload,
            "status": item.status,
            "resolved_action": item.resolved_action,
            "review_note": item.review_note,
            "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "owner_user_id": owner_id,
            "owner_name": owner_name,
        })

    # Unassigned last, then alphabetical by rep - a rep's own name reads
    # top-to-bottom the same every morning instead of shuffling by volume.
    results.sort(key=lambda r: (r["owner_name"] == "Unassigned", r["owner_name"]))
    return results
