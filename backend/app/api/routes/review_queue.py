from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Float, cast, func, select
from sqlalchemy.orm import Session

from app.api.schemas import (
    BulkReviewActionRequest,
    BulkReviewActionResult,
    ReviewActionOut,
    ReviewActionRequest,
    ReviewKindOut,
    ReviewQueueCounts,
    ReviewQueueItemOut,
    ReviewQueuePage,
)
from app.automations import all_kinds, get_action, get_kind
from app.db.session import get_db
from app.models import ReviewQueueItem

router = APIRouter(prefix="/review-queue", tags=["review-queue"])


@router.get("/kinds", response_model=list[ReviewKindOut])
def list_kinds() -> list[ReviewKindOut]:
    """Every registered automation kind and its available actions - the
    frontend's generic review screen renders entirely from this, so a new
    automation shows up with zero frontend changes once it registers here.
    """
    return [
        ReviewKindOut(
            kind=k.kind,
            label=k.label,
            description=k.description,
            actions=[
                ReviewActionOut(
                    id=a.id, label=a.label, style=a.style, outcome=a.outcome,
                    requires_note=a.requires_note, requires_contact_picker=a.requires_contact_picker,
                    extra_fields=[
                        {
                            "key": f.key, "label": f.label, "placeholder": f.placeholder,
                            "required": f.required, "field_type": f.field_type,
                        }
                        for f in a.extra_fields
                    ],
                    confirm_message=a.confirm_message,
                    requires_related_entity_choice=a.requires_related_entity_choice,
                )
                for a in k.actions
            ],
        )
        for k in all_kinds()
    ]


@router.get("/counts", response_model=list[ReviewQueueCounts])
def list_counts(db: Session = Depends(get_db)) -> list[ReviewQueueCounts]:
    """Pending/approved/rejected count per kind - pending drives the filter-chip
    badges (shown even for a kind with zero items, so reviewers know it exists),
    approved/rejected drive the overview's "handled so far" throughput stat."""
    rows = db.execute(
        select(ReviewQueueItem.kind, ReviewQueueItem.status, func.count())
        .group_by(ReviewQueueItem.kind, ReviewQueueItem.status)
    ).all()
    by_kind: dict[str, dict[str, int]] = {}
    for kind, status, count in rows:
        by_kind.setdefault(kind, {})[status] = count
    return [
        ReviewQueueCounts(
            kind=k.kind,
            pending=by_kind.get(k.kind, {}).get("pending", 0),
            approved=by_kind.get(k.kind, {}).get("approved", 0),
            rejected=by_kind.get(k.kind, {}).get("rejected", 0),
        )
        for k in all_kinds()
    ]


@router.get("", response_model=ReviewQueuePage)
def list_review_items(
    kind: str | None = Query(None),
    status: str | None = Query("pending"),
    sort: str = Query("recent"),  # "recent" (default) | "confidence_asc" | "confidence_desc"
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ReviewQueuePage:
    stmt = select(ReviewQueueItem)
    if kind:
        stmt = stmt.where(ReviewQueueItem.kind == kind)
    if status:
        stmt = stmt.where(ReviewQueueItem.status == status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    # confidence lives inside the JSONB payload, not a real column - not
    # every kind sets it, so a missing value always sorts to the end
    # regardless of direction (nulls_last both ways), rather than an
    # unscored item confusingly dominating an ascending sort.
    if sort in ("confidence_asc", "confidence_desc"):
        confidence_expr = cast(ReviewQueueItem.payload["confidence"].astext, Float)
        order = confidence_expr.asc() if sort == "confidence_asc" else confidence_expr.desc()
        stmt = stmt.order_by(order.nulls_last())
    else:
        stmt = stmt.order_by(ReviewQueueItem.created_at.desc())

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = db.scalars(stmt).all()
    return ReviewQueuePage(
        items=[ReviewQueueItemOut.model_validate(i) for i in items],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{item_id}", response_model=ReviewQueueItemOut)
def get_review_item(item_id: uuid.UUID, db: Session = Depends(get_db)) -> ReviewQueueItemOut:
    item = db.get(ReviewQueueItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
    return ReviewQueueItemOut.model_validate(item)


@router.post("/{item_id}/actions/{action_id}", response_model=ReviewQueueItemOut)
def resolve_review_item(
    item_id: uuid.UUID, action_id: str, payload: ReviewActionRequest, db: Session = Depends(get_db)
) -> ReviewQueueItemOut:
    item = db.get(ReviewQueueItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
    if item.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Already resolved ({item.status}, action: {item.resolved_action}) - someone else may have just handled this.",
        )

    kind_def = get_kind(item.kind)
    if not kind_def:
        raise HTTPException(status_code=500, detail=f"No automation is registered for kind {item.kind!r}")
    action = get_action(item.kind, action_id)
    if not action:
        raise HTTPException(status_code=400, detail=f"{action_id!r} is not a valid action for {item.kind!r}")

    if action.requires_note and not (payload.note or "").strip():
        raise HTTPException(status_code=400, detail="This action requires a note.")
    if action.requires_contact_picker and not payload.contact_id:
        raise HTTPException(status_code=400, detail="This action requires picking a contact.")
    if action.requires_related_entity_choice:
        related_ids = {e.get("id") for e in item.payload.get("related_entities", []) if e.get("type") == "contact"}
        if not payload.chosen_entity_id or str(payload.chosen_entity_id) not in related_ids:
            raise HTTPException(status_code=400, detail="Pick which record this action applies to.")
    for f in action.extra_fields:
        if f.field_type == "bool":
            continue  # unchecked is a valid answer, not a missing one
        if f.required and not (payload.fields.get(f.key) or "").strip():
            raise HTTPException(status_code=400, detail=f"{f.label} is required.")

    input_data: dict = dict(payload.fields)
    if payload.note:
        input_data["note"] = payload.note
    if payload.contact_id:
        input_data["contact_id"] = payload.contact_id
    if payload.chosen_entity_id:
        input_data["chosen_entity_id"] = str(payload.chosen_entity_id)

    try:
        kind_def.handler(db, item, action_id, input_data)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e

    item.status = action.outcome
    item.resolved_action = action_id
    item.review_note = payload.note
    item.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return ReviewQueueItemOut.model_validate(item)


@router.post("/bulk-actions/{action_id}", response_model=BulkReviewActionResult)
def bulk_resolve_review_items(
    action_id: str,
    kind: str = Query(..., description="Bulk actions always target one kind's action list - the same kind the queue view is filtered to."),
    payload: BulkReviewActionRequest = BulkReviewActionRequest(),
    db: Session = Depends(get_db),
) -> BulkReviewActionResult:
    """Applies one action to every currently-pending item of one kind - the
    "approve all" / "dismiss all" the reviewer sees for whatever the queue
    is filtered to right now. Deliberately scoped to a single kind (never
    "every pending item across every kind"): actions are defined per kind,
    so there's no single action_id that would even mean the same thing
    across two different kinds - the frontend calls this once per kind
    it's showing, exactly matching what "respect the current filter" means
    when more than one kind is visible at once.

    Only usable for an action that needs no *per-item* input - no contact
    picker, no related-entity choice, no required extra field, and a note
    only if one was supplied here (applied identically to every item, same
    as the single-item flow already allows). An action like "create
    contact" (needs a name typed per item) or "confirm replacement" (needs
    a contact picked per item) can't be meaningfully batched and is
    rejected up front with a clear reason, rather than silently skipping
    every item it can't handle.

    Each item is applied in its own savepoint (db.begin_nested) so one bad
    item (e.g. its referenced contact was deleted since queuing) fails and
    rolls back only itself - it never discards the items already resolved
    successfully in the same batch, the way a single db.rollback() on a
    shared session would.
    """
    kind_def = get_kind(kind)
    if not kind_def:
        raise HTTPException(status_code=404, detail=f"No automation is registered for kind {kind!r}")
    action = get_action(kind, action_id)
    if not action:
        raise HTTPException(status_code=400, detail=f"{action_id!r} is not a valid action for {kind!r}")

    if action.requires_contact_picker or action.requires_related_entity_choice:
        raise HTTPException(status_code=400, detail=f"\"{action.label}\" needs a per-item choice and can't be applied in bulk.")
    if any(f.required for f in action.extra_fields if f.field_type != "bool"):
        raise HTTPException(status_code=400, detail=f"\"{action.label}\" needs per-item input and can't be applied in bulk.")
    if action.requires_note and not (payload.note or "").strip():
        raise HTTPException(status_code=400, detail=f"\"{action.label}\" requires a note - add one to apply it in bulk.")

    input_data: dict = {}
    if payload.note:
        input_data["note"] = payload.note

    items = db.scalars(
        select(ReviewQueueItem).where(ReviewQueueItem.kind == kind, ReviewQueueItem.status == "pending")
    ).all()

    succeeded = 0
    errors: list[str] = []
    for item in items:
        try:
            with db.begin_nested():
                kind_def.handler(db, item, action_id, input_data)
                item.status = action.outcome
                item.resolved_action = action_id
                item.review_note = payload.note
                item.reviewed_at = datetime.now(timezone.utc)
            succeeded += 1
        except ValueError as e:
            if len(errors) < 20:  # cap - a batch that's failing wholesale doesn't need a 500-line response
                errors.append(f"{item.id}: {e}")

    db.commit()
    return BulkReviewActionResult(matched=len(items), succeeded=succeeded, failed=len(items) - succeeded, errors=errors)


@router.post("/{item_id}/reopen", response_model=ReviewQueueItemOut)
def reopen_review_item(item_id: uuid.UUID, db: Session = Depends(get_db)) -> ReviewQueueItemOut:
    """Puts a rejected item back into the pending queue - the safety net
    for "I dismissed a batch of these too quickly and want a second look
    at one." Deliberately rejected-only: an *approved* item's handler
    already made a real CRM write (a merge, an unsubscribe, a new
    contact), and reopening it wouldn't undo that - it would just let
    someone approve it again and potentially run the write a second time.
    A rejected item's handler never writes anything (see e.g.
    dedupe.py's "not_duplicate": pass), so putting it back to pending is
    completely safe - nothing to undo, nothing that could double-apply."""
    item = db.get(ReviewQueueItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
    if item.status != "rejected":
        raise HTTPException(
            status_code=400,
            detail=(
                "Only a rejected item can be reopened - an approved one already made its CRM "
                "change, and reopening it wouldn't undo that."
            ),
        )

    item.status = "pending"
    item.resolved_action = None
    item.review_note = None
    item.reviewed_at = None
    db.commit()
    db.refresh(item)
    return ReviewQueueItemOut.model_validate(item)
