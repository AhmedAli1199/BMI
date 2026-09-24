from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Float, and_, cast, func, or_, select, text
from sqlalchemy.orm import Session

from app.api.schemas import (
    BulkReviewActionRequest,
    BulkReviewActionResult,
    RedraftRequest,
    RedraftResult,
    ReviewActionOut,
    ReviewActionRequest,
    ReviewKindOut,
    ReviewQueueCounts,
    ReviewQueueEntitySummary,
    ReviewQueueInsightBucket,
    ReviewQueueInsights,
    ReviewQueueItemOut,
    ReviewQueuePage,
    UserSummary,
)
from app.automations import all_kinds, get_action, get_kind
from app.core.identity import Identity, get_identity
from app.db.session import get_db
from app.models import Company, Contact, Email, Phone, ReviewQueueItem, User

router = APIRouter(prefix="/review-queue", tags=["review-queue"])


def _visible_kinds(identity: Identity) -> set[str] | None:
    """None = every registered kind (admin/data_manager, or no identity
    forwarded - see identity.py's fail-open note). A sales identity only
    ever sees audience="sales" kinds - CRM-hygiene kinds (merges,
    departures, bounce/OOO triage) stay admin/data_manager regardless of
    which database they're in."""
    if not identity.is_known or identity.role != "sales":
        return None
    return {k.kind for k in all_kinds() if k.audience == "sales"}


def _apply_scope(stmt, identity: Identity):
    """Kind + database scoping shared by every read/write endpoint below.
    A NULL source_db row (e.g. bounce_unmatched - no contact matched yet,
    nothing to scope by) is always let through the database filter; the
    kind filter above already keeps such kinds admin/data_manager-only."""
    visible_kinds = _visible_kinds(identity)
    if visible_kinds is not None:
        stmt = stmt.where(ReviewQueueItem.kind.in_(visible_kinds))

    allowed_dbs = identity.allowed_source_dbs()
    if allowed_dbs is not None:
        stmt = stmt.where(
            or_(ReviewQueueItem.source_db.is_(None), ReviewQueueItem.source_db.in_(allowed_dbs))
        )
    return stmt


def _confidence_expr():
    return cast(ReviewQueueItem.payload["confidence"].astext, Float)


def _replacements_len_expr():
    # coalesce first: a row with no "replacements" key at all (an older
    # item, or a kind that never sets it) must count as "no replacement",
    # not silently drop out of both buckets - jsonb_array_length(NULL) is
    # NULL, which fails every comparison.
    replacements = func.coalesce(ReviewQueueItem.payload["replacements"], text("'[]'::jsonb"))
    return func.jsonb_array_length(replacements)


# Queue Insights buckets, kind by kind - deliberately only the 3 kinds
# that already compute a categorizing value at ingestion time
# (confidence / severity / replacements), so this is pure aggregation
# over data that already exists, never a new classification step. A kind
# with no entry here just gets an empty bucket list from /insights - the
# frontend hides the panel entirely rather than showing "no insights yet".
_INSIGHT_BUCKETS: dict[str, list[tuple[str, str]]] = {
    "duplicate_contact": [
        ("high", "High confidence (≥90%)"),
        ("medium", "Medium confidence (70–89%)"),
        ("low", "Low confidence (<70%)"),
    ],
    "bounce_uncertain": [
        ("hard", "Hard bounce"),
        ("soft", "Soft bounce"),
    ],
    "bounce_unmatched": [
        ("hard", "Hard bounce"),
        ("soft", "Soft bounce"),
    ],
    "ooo_ambiguous": [
        ("has_replacement", "Has a named replacement"),
        ("no_replacement", "Absence only, no replacement named"),
    ],
}


def _bucket_condition(kind: str, bucket: str):
    """The SQL condition for one (kind, bucket) pair, or None if that
    combination isn't a real bucket - callers must check for None rather
    than silently matching everything, since an unrecognized bucket key
    should behave as "invalid filter", not "no filter"."""
    if kind == "duplicate_contact":
        confidence = _confidence_expr()
        if bucket == "high":
            return confidence >= 0.9
        if bucket == "medium":
            return and_(confidence >= 0.7, confidence < 0.9)
        if bucket == "low":
            return confidence < 0.7
        return None
    if kind in ("bounce_uncertain", "bounce_unmatched"):
        if bucket in ("hard", "soft"):
            return ReviewQueueItem.payload["severity"].astext == bucket
        return None
    if kind == "ooo_ambiguous":
        replacements_len = _replacements_len_expr()
        if bucket == "has_replacement":
            return replacements_len > 0
        if bucket == "no_replacement":
            return replacements_len == 0
        return None
    return None


def _serialize_items(db: Session, items: list[ReviewQueueItem]) -> list[ReviewQueueItemOut]:
    """Batch-attaches the two things a plain model_validate(item) can't
    give you - entity_summary (linked contact/company's name, email,
    phone, employer) and reviewed_by (who resolved it) - in a handful of
    IN (...) queries regardless of how many items are being serialized,
    never one query per item."""
    contact_ids = {i.entity_id for i in items if i.entity_type == "contact" and i.entity_id}
    company_ids = {i.entity_id for i in items if i.entity_type == "company" and i.entity_id}
    reviewer_ids = {i.reviewed_by_user_id for i in items if i.reviewed_by_user_id}

    contacts = {c.id: c for c in db.scalars(select(Contact).where(Contact.id.in_(contact_ids)))} if contact_ids else {}
    companies = {c.id: c for c in db.scalars(select(Company).where(Company.id.in_(company_ids)))} if company_ids else {}
    reviewers = {u.id: u for u in db.scalars(select(User).where(User.id.in_(reviewer_ids)))} if reviewer_ids else {}

    # A contact's own employer, needed for entity_summary.company_name -
    # not necessarily the same set as company_ids above (those are items
    # whose entity_type IS "company", this is companies *referenced by* a
    # contact-type item).
    employer_ids = {c.company_id for c in contacts.values() if c.company_id}
    missing_employer_ids = employer_ids - companies.keys()
    if missing_employer_ids:
        for c in db.scalars(select(Company).where(Company.id.in_(missing_employer_ids))):
            companies[c.id] = c

    emails_by_contact: dict[uuid.UUID, str] = {}
    phones_by_contact: dict[uuid.UUID, str] = {}
    if contacts:
        for e in db.scalars(
            select(Email).where(Email.contact_id.in_(contacts.keys())).order_by(Email.is_primary.desc())
        ):
            emails_by_contact.setdefault(e.contact_id, e.address)
        for p in db.scalars(
            select(Phone).where(Phone.contact_id.in_(contacts.keys())).order_by(Phone.is_primary.desc())
        ):
            phones_by_contact.setdefault(p.contact_id, p.number)

    def entity_summary(item: ReviewQueueItem) -> ReviewQueueEntitySummary | None:
        if item.entity_type == "contact" and item.entity_id in contacts:
            c = contacts[item.entity_id]
            employer = companies.get(c.company_id) if c.company_id else None
            label = c.full_name or " ".join(filter(None, [c.first_name, c.last_name])) or "(no name)"
            return ReviewQueueEntitySummary(
                id=c.id, type="contact", label=label, job_title=c.job_title,
                email=emails_by_contact.get(c.id), phone=phones_by_contact.get(c.id),
                company_name=employer.name if employer else None,
            )
        if item.entity_type == "company" and item.entity_id in companies:
            comp = companies[item.entity_id]
            return ReviewQueueEntitySummary(id=comp.id, type="company", label=comp.name)
        return None

    out = []
    for item in items:
        item_out = ReviewQueueItemOut.model_validate(item)
        item_out.entity_summary = entity_summary(item)
        if item.reviewed_by_user_id and item.reviewed_by_user_id in reviewers:
            item_out.reviewed_by = UserSummary.model_validate(reviewers[item.reviewed_by_user_id])
        out.append(item_out)
    return out


def _is_visible(item: ReviewQueueItem, identity: Identity) -> bool:
    visible_kinds = _visible_kinds(identity)
    if visible_kinds is not None and item.kind not in visible_kinds:
        return False
    allowed_dbs = identity.allowed_source_dbs()
    if allowed_dbs is not None and item.source_db is not None and item.source_db not in allowed_dbs:
        return False
    return True


@router.get("/kinds", response_model=list[ReviewKindOut])
def list_kinds(identity: Identity = Depends(get_identity)) -> list[ReviewKindOut]:
    """Every registered automation kind this caller may see, and its
    available actions - the frontend's generic review screen renders
    entirely from this, so a new automation shows up with zero frontend
    changes once it registers here. Filtered by audience (see
    ReviewKind.audience / _visible_kinds) - a sales identity only ever
    gets sales-facing kinds back, so its filter-chip row never shows a
    hygiene kind it has no action on anyway.
    """
    visible_kinds = _visible_kinds(identity)
    return [
        ReviewKindOut(
            kind=k.kind,
            label=k.label,
            description=k.description,
            audience=k.audience,
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
        if visible_kinds is None or k.kind in visible_kinds
    ]


@router.get("/counts", response_model=list[ReviewQueueCounts])
def list_counts(db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> list[ReviewQueueCounts]:
    """Pending/approved/rejected count per kind, scoped to this caller (see
    _apply_scope) - pending drives the filter-chip badges (shown even for
    a kind with zero items, so reviewers know it exists), approved/
    rejected drive the overview's "handled so far" throughput stat."""
    stmt = _apply_scope(
        select(ReviewQueueItem.kind, ReviewQueueItem.status, func.count()).group_by(
            ReviewQueueItem.kind, ReviewQueueItem.status
        ),
        identity,
    )
    rows = db.execute(stmt).all()
    by_kind: dict[str, dict[str, int]] = {}
    for kind, status, count in rows:
        by_kind.setdefault(kind, {})[status] = count
    visible_kinds = _visible_kinds(identity)
    return [
        ReviewQueueCounts(
            kind=k.kind,
            pending=by_kind.get(k.kind, {}).get("pending", 0),
            approved=by_kind.get(k.kind, {}).get("approved", 0),
            rejected=by_kind.get(k.kind, {}).get("rejected", 0),
        )
        for k in all_kinds()
        if visible_kinds is None or k.kind in visible_kinds
    ]


@router.get("/insights", response_model=ReviewQueueInsights)
def get_review_insights(
    kind: str = Query(...),
    status: str | None = Query("pending"),
    db: Session = Depends(get_db),
    identity: Identity = Depends(get_identity),
) -> ReviewQueueInsights:
    """Queue Insights: how many pending (or whatever `status`) items of
    this one kind fall into each of its buckets (see _INSIGHT_BUCKETS) -
    "587 have a named replacement, 311 don't" instead of a flat unlabeled
    count. Pure aggregation over data the automation already writes into
    payload at ingestion time (confidence / severity / replacements) - no
    new classification step, and cheap enough at this table's real size
    (hundreds to low thousands of rows per kind) that no caching layer is
    warranted; add one only if that stops being true.

    Empty bucket list for a kind not in _INSIGHT_BUCKETS - the frontend
    hides its Queue Insights panel entirely rather than showing an empty
    one, so adding a kind here is the only step needed to turn it on
    there too."""
    bucket_defs = _INSIGHT_BUCKETS.get(kind, [])
    visible_kinds = _visible_kinds(identity)
    if visible_kinds is not None and kind not in visible_kinds:
        return ReviewQueueInsights(kind=kind, buckets=[])

    buckets: list[ReviewQueueInsightBucket] = []
    for key, label in bucket_defs:
        condition = _bucket_condition(kind, key)
        stmt = _apply_scope(
            select(func.count()).select_from(ReviewQueueItem).where(ReviewQueueItem.kind == kind, condition),
            identity,
        )
        if status:
            stmt = stmt.where(ReviewQueueItem.status == status)
        count = db.scalar(stmt) or 0
        buckets.append(ReviewQueueInsightBucket(key=key, label=label, count=count))
    return ReviewQueueInsights(kind=kind, buckets=buckets)


@router.get("", response_model=ReviewQueuePage)
def list_review_items(
    kind: str | None = Query(None),
    status: str | None = Query("pending"),
    q: str | None = Query(None, description="Free-text search - every kind's card headline (payload.summary) always names the contact/company, so this doubles as search-by-contact without a join."),
    bucket: str | None = Query(None, description="One Queue Insights bucket key for this kind (see /insights) - e.g. 'high' for duplicate_contact. Requires kind to be set; an unrecognized (kind, bucket) pair 400s rather than silently matching everything."),
    sort: str = Query("recent"),  # "recent" (default) | "confidence_asc" | "confidence_desc"
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    identity: Identity = Depends(get_identity),
) -> ReviewQueuePage:
    stmt = _apply_scope(select(ReviewQueueItem), identity)
    if kind:
        stmt = stmt.where(ReviewQueueItem.kind == kind)
    if status:
        stmt = stmt.where(ReviewQueueItem.status == status)
    if bucket:
        if not kind:
            raise HTTPException(status_code=400, detail="bucket requires kind to be set too.")
        condition = _bucket_condition(kind, bucket)
        if condition is None:
            raise HTTPException(status_code=400, detail=f"{bucket!r} is not a Queue Insights bucket for {kind!r}.")
        stmt = stmt.where(condition)
    if q and q.strip():
        needle = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                ReviewQueueItem.payload["summary"].astext.ilike(needle),
                ReviewQueueItem.payload["subject"].astext.ilike(needle),
            )
        )

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
        items=_serialize_items(db, items),
        total=total, page=page, page_size=page_size,
    )


@router.get("/{item_id}", response_model=ReviewQueueItemOut)
def get_review_item(
    item_id: uuid.UUID, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)
) -> ReviewQueueItemOut:
    item = db.get(ReviewQueueItem, item_id)
    # Out-of-scope reads as "not found", not "forbidden" - doesn't confirm
    # to a caller outside their access that some other database's item
    # exists at this id at all.
    if not item or not _is_visible(item, identity):
        raise HTTPException(status_code=404, detail="Review item not found")
    return _serialize_items(db, [item])[0]


@router.post("/{item_id}/actions/{action_id}", response_model=ReviewQueueItemOut)
def resolve_review_item(
    item_id: uuid.UUID, action_id: str, payload: ReviewActionRequest,
    db: Session = Depends(get_db), identity: Identity = Depends(get_identity),
) -> ReviewQueueItemOut:
    item = db.get(ReviewQueueItem, item_id)
    if not item or not _is_visible(item, identity):
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
    item.reviewed_by_user_id = identity.user_uuid
    db.commit()
    db.refresh(item)
    return _serialize_items(db, [item])[0]


@router.post("/{item_id}/redraft", response_model=RedraftResult)
def redraft_review_item(
    item_id: uuid.UUID, payload: RedraftRequest,
    db: Session = Depends(get_db), identity: Identity = Depends(get_identity),
) -> RedraftResult:
    """Regenerates an AI-drafted follow-up (payload["original_text"]) with
    extra instructions from the reviewer - "make it shorter", "mention the
    renewal date explicitly", etc. Deliberately does NOT resolve the item
    (status stays "pending") - this is a preview step the reviewer can
    call as many times as they like before actually approving, same as
    editing a draft by hand would be. The regenerated text IS persisted
    into the item's own payload so a page refresh (or the review list
    itself) shows the latest draft rather than the original one, but that
    persistence never touches item.status/resolved_action - only an
    explicit POST .../actions/{action_id} does that.
    """
    item = db.get(ReviewQueueItem, item_id)
    if not item or not _is_visible(item, identity):
        raise HTTPException(status_code=404, detail="Review item not found")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="Already resolved - can't redraft a closed item.")

    kind_def = get_kind(item.kind)
    if not kind_def:
        raise HTTPException(status_code=500, detail=f"No automation is registered for kind {item.kind!r}")
    if not kind_def.redraft:
        raise HTTPException(status_code=400, detail=f"{item.kind!r} items don't support redrafting.")

    try:
        new_draft = kind_def.redraft(db, item, payload.instructions.strip())
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e

    item.payload = {**item.payload, "original_text": new_draft}
    db.commit()
    return RedraftResult(draft=new_draft)


@router.post("/bulk-actions/{action_id}", response_model=BulkReviewActionResult)
def bulk_resolve_review_items(
    action_id: str,
    kind: str = Query(..., description="Bulk actions always target one kind's action list - the same kind the queue view is filtered to."),
    payload: BulkReviewActionRequest = BulkReviewActionRequest(),
    db: Session = Depends(get_db),
    identity: Identity = Depends(get_identity),
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
    visible_kinds = _visible_kinds(identity)
    if visible_kinds is not None and kind not in visible_kinds:
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
        _apply_scope(
            select(ReviewQueueItem).where(ReviewQueueItem.kind == kind, ReviewQueueItem.status == "pending"),
            identity,
        )
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
                item.reviewed_by_user_id = identity.user_uuid
            succeeded += 1
        except ValueError as e:
            if len(errors) < 20:  # cap - a batch that's failing wholesale doesn't need a 500-line response
                errors.append(f"{item.id}: {e}")

    db.commit()
    return BulkReviewActionResult(matched=len(items), succeeded=succeeded, failed=len(items) - succeeded, errors=errors)


@router.post("/{item_id}/reopen", response_model=ReviewQueueItemOut)
def reopen_review_item(
    item_id: uuid.UUID, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)
) -> ReviewQueueItemOut:
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
    if not item or not _is_visible(item, identity):
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
    item.reviewed_by_user_id = None
    db.commit()
    db.refresh(item)
    return _serialize_items(db, [item])[0]
