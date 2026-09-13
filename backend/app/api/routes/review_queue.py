from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas import (
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
                        {"key": f.key, "label": f.label, "placeholder": f.placeholder, "required": f.required}
                        for f in a.extra_fields
                    ],
                    confirm_message=a.confirm_message,
                )
                for a in k.actions
            ],
        )
        for k in all_kinds()
    ]


@router.get("/counts", response_model=list[ReviewQueueCounts])
def list_counts(db: Session = Depends(get_db)) -> list[ReviewQueueCounts]:
    """Pending count per kind, for the filter-chip badges - shown even for
    a kind with zero items so reviewers know it exists."""
    rows = dict(
        db.execute(
            select(ReviewQueueItem.kind, func.count())
            .where(ReviewQueueItem.status == "pending")
            .group_by(ReviewQueueItem.kind)
        ).all()
    )
    return [ReviewQueueCounts(kind=k.kind, pending=rows.get(k.kind, 0)) for k in all_kinds()]


@router.get("", response_model=ReviewQueuePage)
def list_review_items(
    kind: str | None = Query(None),
    status: str | None = Query("pending"),
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
    stmt = stmt.order_by(ReviewQueueItem.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
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
    for f in action.extra_fields:
        if f.required and not (payload.fields.get(f.key) or "").strip():
            raise HTTPException(status_code=400, detail=f"{f.label} is required.")

    input_data: dict = dict(payload.fields)
    if payload.note:
        input_data["note"] = payload.note
    if payload.contact_id:
        input_data["contact_id"] = payload.contact_id

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
