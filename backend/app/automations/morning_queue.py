"""SALES-013 (Morning Follow-Up Queue) - see docs/build-spec.txt.

Deliberately NOT a new producer: there's nothing new to extract here.
SALES-012 (signal_triggers.py) already turns budget_window/renewal_date/
promised_callback signals into `signal_trigger` review items once they're
due, and the pre-existing Follow-up Engine (followup_queue.py) already
turns due/overdue Activities into `followup_due` review items. This
module is purely a read-side aggregation: pull every still-pending item
from both, resolve which salesperson it belongs to (via Contact.
owner_user_id - the whole reason the record-manager backfill mattered),
rank them, and hand back one flat, owner-labeled list for the frontend to
group into "your list for today" - no new database writes, no new
review-queue kind.

An item whose contact/company has no resolvable owner_user_id (an
un-backfilled contact, or a followup_due item tied to a company rather
than a contact - companies don't carry ownership) is labeled "Unassigned"
rather than dropped, so nothing silently disappears from the queue.

RANKING (score = w_urgency*urgency + w_value*value, both 0-1, see
settings_registry.py's "Morning follow-up queue" group):

- urgency is always real - computed from the item's own due date
  (signal_trigger's payload["due_date"], followup_due's payload["due_at"])
  relative to today, or a flat moderate score for an undated signal that
  already crossed its own no-date trigger delay.
- value only ever reflects a genuine Opportunity.total_amount linked to
  the item's contact - there are only ~7 Opportunity rows total across
  every migrated Act! database, so this is a rare tie-breaker, never a
  required input, and an item with no Opportunity scores exactly 0 on
  value rather than a guessed figure. Default weights favor urgency
  heavily for exactly that reason.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.models import Company, Contact, Opportunity, ReviewQueueItem, User

_SOURCE_KINDS = ("signal_trigger", "followup_due", "personal_touchpoint_due")


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

    if contact_id:
        contact = db.get(Contact, contact_id)
        if contact:
            if contact.owner_user_id:
                owner = db.get(User, contact.owner_user_id)
                return (str(contact.owner_user_id), owner.name if owner else "Unassigned")
            if contact.company_id:
                company = db.get(Company, contact.company_id)
                if company and company.owner_user_id:
                    owner = db.get(User, company.owner_user_id)
                    return (str(company.owner_user_id), owner.name if owner else "Unassigned")

    if item.entity_type == "company" and item.entity_id:
        company = db.get(Company, item.entity_id)
        if company and company.owner_user_id:
            owner = db.get(User, company.owner_user_id)
            return (str(company.owner_user_id), owner.name if owner else "Unassigned")

    return None, "Unassigned"


def _item_contact_id(item: ReviewQueueItem) -> str | None:
    if item.entity_type == "contact" and item.entity_id:
        return str(item.entity_id)
    related = next((e for e in (item.payload.get("related_entities") or []) if e.get("type") == "contact"), None)
    return related.get("id") if related else None


def _urgency_score(item: ReviewQueueItem, today: date) -> float:
    """1.0 = due today or overdue, fading linearly to ~0 two weeks out.
    An undated signal_trigger item (payload["due_date"] is None) already
    only exists because it crossed its own no-date delay trigger - scored
    a flat, moderate 0.6 rather than 0 or 1, since there's no real date to
    rank it against."""
    due_raw = item.payload.get("due_date") or item.payload.get("due_at")
    if not due_raw:
        return 0.6
    try:
        due_date = datetime.fromisoformat(due_raw).date()
    except ValueError:
        return 0.6
    days_out = (due_date - today).days
    if days_out <= 0:
        return 1.0
    return max(0.0, min(1.0, 1 - days_out / 14))


def _value_scores(db: Session, contact_ids: set[str], value_cap: float) -> dict[str, float]:
    """{contact_id: normalized 0-1 value} for every contact with at least
    one Opportunity - a contact with none simply has no entry (callers
    default to 0), never a guessed figure. Only queried for the contacts
    actually on this page's items, not the whole table."""
    if not contact_ids or value_cap <= 0:
        return {}
    rows = (
        db.query(Opportunity.contact_id, Opportunity.total_amount)
        .filter(Opportunity.contact_id.in_(contact_ids), Opportunity.total_amount.isnot(None))
        .all()
    )
    best: dict[str, float] = {}
    for contact_id, amount in rows:
        normalized = max(0.0, min(1.0, float(amount) / value_cap))
        key = str(contact_id)
        if normalized > best.get(key, 0.0):
            best[key] = normalized
    return best


def build_today_queue(db: Session, owner_user_id: str | None = None, source_dbs: set[str] | None = None) -> list[dict]:
    """Every pending signal_trigger/followup_due item, each tagged with
    who it belongs to and ranked by urgency/value. If owner_user_id is
    given, scoped to that rep's own items (a rep's "my list for today");
    omitted, every item is returned grouped-ready (a manager's cross-team
    view). source_dbs, when given, further restricts to those databases -
    see the /today route's identity-based scoping; an item with no
    source_db recorded is left in either way (nothing to filter by)."""
    query = db.query(ReviewQueueItem).filter(
        ReviewQueueItem.kind.in_(_SOURCE_KINDS), ReviewQueueItem.status == "pending"
    )
    if source_dbs is not None:
        query = query.filter(
            (ReviewQueueItem.source_db.in_(source_dbs)) | (ReviewQueueItem.source_db.is_(None))
        )
    items = query.order_by(ReviewQueueItem.created_at.asc()).all()

    w_urgency = runtime_settings.get_float(db, "sales013_weight_urgency")
    w_value = runtime_settings.get_float(db, "sales013_weight_value")
    value_cap = runtime_settings.get_float(db, "sales013_value_cap")
    today = datetime.now(timezone.utc).date()

    contact_ids = {cid for item in items if (cid := _item_contact_id(item))}
    value_by_contact = _value_scores(db, contact_ids, value_cap)

    results = []
    for item in items:
        owner_id, owner_name = _resolve_owner(db, item)
        if owner_user_id and owner_id != owner_user_id:
            continue
        contact_id = _item_contact_id(item)
        urgency = _urgency_score(item, today)
        value = value_by_contact.get(contact_id, 0.0) if contact_id else 0.0
        score = w_urgency * urgency + w_value * value
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
            "rank_score": round(score, 4),
        })

    # Unassigned last, then alphabetical by rep, then highest-ranked first
    # within each rep's own list - a rep's own name reads top-to-bottom
    # the same every morning instead of shuffling by volume, but what
    # they see *within* their own list is genuinely priority-ordered.
    results.sort(key=lambda r: (r["owner_name"] == "Unassigned", r["owner_name"], -r["rank_score"]))
    return results
