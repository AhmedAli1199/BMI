from __future__ import annotations

import logging
import uuid
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Float, String, and_, case, cast, func, literal, or_, select, text
from sqlalchemy.orm import Session

from app.api.schemas import (
    BulkReviewActionRequest,
    BulkReviewActionResult,
    RedraftRequest,
    RedraftResult,
    ReviewActionOut,
    ReviewActionRequest,
    ReviewFacetOption,
    ReviewFacetOut,
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
from app.automations.review_facets import NOT_SET
from app.core.identity import Identity, get_identity
from app.db.session import get_db
from app.models import Company, Contact, Email, Phone, ReviewQueueItem, User

logger = logging.getLogger("app.api.review_queue")

_BULK_FALLBACK_REASON = "something went wrong while applying it - try these cards one at a time."

router = APIRouter(prefix="/review-queue", tags=["review-queue"])


def _visible_kinds(identity: Identity, db: Session | None = None) -> set[str] | None:
    """None = every registered kind (admin/data_manager, or no identity
    forwarded - see identity.py's fail-open note). A sales identity only
    ever sees audience="sales" kinds - CRM-hygiene kinds (merges,
    departures, bounce/OOO triage) stay admin/data_manager regardless of
    which database they're in."""
    base = None if (not identity.is_known or identity.role != "sales") else {k.kind for k in all_kinds() if k.audience == "sales"}
    accounts_kinds = {k.kind for k in all_kinds() if k.approver == "accounts"}
    if not accounts_kinds or not identity.is_known:
        return base
    from app.sales.accounts import can_approve
    if db is not None:
        approves = can_approve(db, identity.user_uuid, identity.role)
    else:
        from app.db.session import SessionLocal
        with SessionLocal() as own:
            approves = can_approve(own, identity.user_uuid, identity.role)
    if approves:   # Samantha sees booking checks and change requests whatever her role
        return None if base is None else base | accounts_kinds
    return ({k.kind for k in all_kinds()} if base is None else base) - accounts_kinds


def _apply_scope(stmt, identity: Identity, db: Session | None = None):
    """Kind + database scoping shared by every read/write endpoint below.
    A NULL source_db row (e.g. bounce_unmatched - no contact matched yet,
    nothing to scope by) is always let through the database filter; the
    kind filter above already keeps such kinds admin/data_manager-only."""
    visible_kinds = _visible_kinds(identity, db)
    if visible_kinds is not None:
        stmt = stmt.where(ReviewQueueItem.kind.in_(visible_kinds))
        # A renewal (or an allocation reminder) is the job of the rep who sold it: a salesperson sees only their own.
        if identity.user_uuid and identity.role == "sales":
            from app.models import SalesOrder, SalesRep

            mine = (select(SalesOrder.id).join(SalesRep, SalesOrder.rep_id == SalesRep.id)
                    .where(SalesRep.user_id == identity.user_uuid,
                           cast(SalesOrder.id, String) == ReviewQueueItem.payload["order_id"].astext)).exists()
            stmt = stmt.where(or_(ReviewQueueItem.kind.notin_(("renewal_due", "allocation_due", "proposal_request", "press_release")), mine,
                                  ReviewQueueItem.payload["owner_user_id"].astext == str(identity.user_uuid)))

    if db is not None:
        from app.core.visibility import review_item_clause

        seen = review_item_clause(db, identity)  # items about records outside someone's groups stay hidden
        if seen is not None:
            stmt = stmt.where(seen)
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


def _is_visible(item: ReviewQueueItem, identity: Identity, db: Session | None = None) -> bool:
    visible_kinds = _visible_kinds(identity, db)
    if visible_kinds is not None and item.kind not in visible_kinds:
        return False
    allowed_dbs = identity.allowed_source_dbs()
    if allowed_dbs is not None and item.source_db is not None and item.source_db not in allowed_dbs:
        return False
    return True


@router.get("/kinds", response_model=list[ReviewKindOut])
def list_kinds(identity: Identity = Depends(get_identity), db: Session = Depends(get_db)) -> list[ReviewKindOut]:
    """Every registered automation kind this caller may see, and its
    available actions - the frontend's generic review screen renders
    entirely from this, so a new automation shows up with zero frontend
    changes once it registers here. Filtered by audience (see
    ReviewKind.audience / _visible_kinds) - a sales identity only ever
    gets sales-facing kinds back, so its filter-chip row never shows a
    hygiene kind it has no action on anyway.
    """
    visible_kinds = _visible_kinds(identity, db)
    return [
        ReviewKindOut(
            kind=k.kind,
            label=k.label,
            description=k.description,
            audience=k.audience,
            facets=[{"key": key, "label": label} for key, label in k.facets],
            date_sort_label=k.date_sort_label,
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
                    reopenable=a.reopenable,
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
        db,
    )
    rows = db.execute(stmt).all()
    by_kind: dict[str, dict[str, int]] = {}
    for kind, status, count in rows:
        by_kind.setdefault(kind, {})[status] = count
    visible_kinds = _visible_kinds(identity, db)
    return [
        ReviewQueueCounts(
            kind=k.kind,
            pending=by_kind.get(k.kind, {}).get("pending", 0),
            approved=by_kind.get(k.kind, {}).get("approved", 0),
            rejected=by_kind.get(k.kind, {}).get("rejected", 0),
            snoozed=by_kind.get(k.kind, {}).get("snoozed", 0),
        )
        for k in all_kinds()
        if visible_kinds is None or k.kind in visible_kinds
    ]


def _parse_facets(raw: list[str]) -> dict[str, list[str]]:
    """["salesperson:Sally Parker", "payment:Paid"] -> {"salesperson": ["Sally Parker"], "payment": ["Paid"]}"""
    out: dict[str, list[str]] = {}
    for item in raw:
        key, sep, value = item.partition(":")
        if sep and key and value:
            out.setdefault(key, []).append(value)
    return out


def _facet_expr(key: str):
    # A card queued before its kind had filters has no "facets" at all - it shows under "Not set"
    # (and can be filtered to) until the kind's next scan fills it in (see review_facets.backfill).
    return case((ReviewQueueItem.payload.has_key("facets"), ReviewQueueItem.payload["facets"][key].astext),
                else_=literal(NOT_SET))


def _apply_filters(stmt, *, kind, status, q, bucket, facets: dict[str, list[str]], skip: str | None = None):
    if kind:
        stmt = stmt.where(ReviewQueueItem.kind == kind)
    if status:
        stmt = stmt.where(ReviewQueueItem.status == status)
    if bucket:
        if not kind:
            raise HTTPException(status_code=400, detail="Pick a kind of card before choosing a Queue Insights group.")
        condition = _bucket_condition(kind, bucket)
        if condition is None:
            raise HTTPException(status_code=400, detail="That Queue Insights group doesn't exist for this kind of card.")
        stmt = stmt.where(condition)
    if q and q.strip():
        needle = f"%{q.strip()}%"
        stmt = stmt.where(or_(ReviewQueueItem.payload["summary"].astext.ilike(needle),
                              ReviewQueueItem.payload["subject"].astext.ilike(needle)))
    for key, values in facets.items():
        if key != skip:
            stmt = stmt.where(_facet_expr(key).in_(values))
    return stmt


@router.get("/facets", response_model=list[ReviewFacetOut])
def list_facets(
    kind: str = Query(...),
    status: str | None = Query("pending"),
    q: str | None = Query(None),
    bucket: str | None = Query(None),
    facet: list[str] = Query(default=[]),
    db: Session = Depends(get_db),
    identity: Identity = Depends(get_identity),
) -> list[ReviewFacetOut]:
    """The filters a kind offers, with how many items each option would show -
    counted with every OTHER filter already applied (so picking a salesperson
    updates the counts beside the titles, as in the bookings filters)."""
    kind_def = get_kind(kind)
    visible = _visible_kinds(identity, db)
    if not kind_def or (visible is not None and kind not in visible):
        return []
    chosen = _parse_facets(facet)
    out = []
    for key, label in kind_def.facets:
        expr = _facet_expr(key)
        stmt = _apply_filters(_apply_scope(select(expr, func.count()), identity, db), kind=kind, status=status, q=q,
                              bucket=bucket, facets=chosen, skip=key).where(expr.isnot(None)).group_by(expr)
        rows = sorted(db.execute(stmt).all(), key=lambda r: (-r[1], str(r[0])))
        out.append(ReviewFacetOut(key=key, label=label, options=[ReviewFacetOption(value=v, count=c) for v, c in rows]))
    return out


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
    visible_kinds = _visible_kinds(identity, db)
    if visible_kinds is not None and kind not in visible_kinds:
        return ReviewQueueInsights(kind=kind, buckets=[])

    buckets: list[ReviewQueueInsightBucket] = []
    for key, label in bucket_defs:
        condition = _bucket_condition(kind, key)
        stmt = _apply_scope(
            select(func.count()).select_from(ReviewQueueItem).where(ReviewQueueItem.kind == kind, condition),
            identity, db,
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
    facet: list[str] = Query(default=[], description="Repeatable 'key:value' filter - see ReviewKind.facets and /facets."),
    sort: str = Query("recent"),  # "recent" (default) | "confidence_asc" | "confidence_desc" | "date_desc" | "date_asc"
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    identity: Identity = Depends(get_identity),
) -> ReviewQueuePage:
    stmt = _apply_filters(_apply_scope(select(ReviewQueueItem), identity, db), kind=kind, status=status, q=q, bucket=bucket,
                          facets=_parse_facets(facet))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    # confidence lives inside the JSONB payload, not a real column - not
    # every kind sets it, so a missing value always sorts to the end
    # regardless of direction (nulls_last both ways), rather than an
    # unscored item confusingly dominating an ascending sort.
    if sort in ("confidence_asc", "confidence_desc"):
        confidence_expr = cast(ReviewQueueItem.payload["confidence"].astext, Float)
        order = confidence_expr.asc() if sort == "confidence_asc" else confidence_expr.desc()
        stmt = stmt.order_by(order.nulls_last())
    elif sort in ("date_desc", "date_asc"):
        # payload["sort_date"] is an ISO date (e.g. the booking date), so text order is date order
        date_expr = ReviewQueueItem.payload["sort_date"].astext
        stmt = stmt.order_by((date_expr.desc() if sort == "date_desc" else date_expr.asc()).nulls_last(),
                             ReviewQueueItem.created_at.desc())
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
    if not item or not _is_visible(item, identity, db):
        raise HTTPException(status_code=404, detail="Review item not found")
    return _serialize_items(db, [item])[0]


@router.post("/{item_id}/actions/{action_id}", response_model=ReviewQueueItemOut)
def resolve_review_item(
    item_id: uuid.UUID, action_id: str, payload: ReviewActionRequest,
    db: Session = Depends(get_db), identity: Identity = Depends(get_identity),
) -> ReviewQueueItemOut:
    item = db.get(ReviewQueueItem, item_id)
    if not item or not _is_visible(item, identity, db):
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
        raise HTTPException(status_code=400, detail="That button isn't available for this card. Refresh the page and try again.")

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
    # Who clicked - for actions done "as me" (send from my Outlook).
    input_data["_actor_user_id"] = str(identity.user_uuid) if identity.user_uuid else None
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
    if not item or not _is_visible(item, identity, db):
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


# One bulk call does at most this many cards; the screen calls again for the rest.
BULK_MAX_PER_CALL = 500
BULK_COMMIT_EVERY = 100


@router.post("/bulk-actions/{action_id}", response_model=BulkReviewActionResult)
def bulk_resolve_review_items(
    action_id: str,
    kind: str = Query(..., description="Bulk actions always target one kind's action list - the same kind the queue view is filtered to."),
    facet: list[str] = Query(default=[], description="The same 'key:value' filters the list is showing - only those items are touched."),
    q: str | None = Query(None, description="The same search the list is showing."),
    bucket: str | None = Query(None, description="The Queue Insights group the list is showing (e.g. 'soft' bounces) - only those items are touched."),
    offset: int = Query(0, ge=0, description="Skip this many matching cards (oldest first) - the ones earlier calls of the same run couldn't do."),
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

    Very large selections: one call handles at most BULK_MAX_PER_CALL cards
    (oldest first), saving every BULK_COMMIT_EVERY so finished work is kept
    even if the request is cut off. `remaining` says how many matching cards
    this call didn't get to; the screen calls again (passing how many failed
    so far as `offset`, since failed cards stay waiting at the front) until
    it reaches 0.
    """
    kind_def = get_kind(kind)
    visible_kinds = _visible_kinds(identity, db)
    if not kind_def or (visible_kinds is not None and kind not in visible_kinds):
        raise HTTPException(status_code=404, detail="This kind of card doesn't exist, or you don't have access to it.")
    action = get_action(kind, action_id)
    if not action:
        raise HTTPException(status_code=400, detail="That button isn't available for these cards. Refresh the page and try again.")

    if action.requires_contact_picker or action.requires_related_entity_choice:
        raise HTTPException(status_code=400, detail=f"\"{action.label}\" needs a per-item choice and can't be applied in bulk.")
    if any(f.required for f in action.extra_fields if f.field_type != "bool"):
        raise HTTPException(status_code=400, detail=f"\"{action.label}\" needs per-item input and can't be applied in bulk.")
    if action.requires_note and not (payload.note or "").strip():
        raise HTTPException(status_code=400, detail=f"\"{action.label}\" requires a note - add one to apply it in bulk.")

    input_data: dict = {"_actor_user_id": str(identity.user_uuid) if identity.user_uuid else None}
    if payload.note:
        input_data["note"] = payload.note

    stmt = _apply_filters(_apply_scope(select(ReviewQueueItem), identity, db), kind=kind, status="pending", q=q, bucket=bucket,
                          facets=_parse_facets(facet))
    matched = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(ReviewQueueItem.created_at, ReviewQueueItem.id).offset(offset).limit(BULK_MAX_PER_CALL)).all()

    succeeded = failed = 0
    # Why cards couldn't be done, counted by reason - a plain summary for the person, never card ids.
    reasons: Counter[str] = Counter()
    for n, item in enumerate(items, start=1):
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
            # Handlers raise ValueError with a plain sentence written for people.
            failed += 1
            reasons[str(e).strip() or _BULK_FALLBACK_REASON] += 1
        except Exception:
            logger.exception("bulk review action %s failed for item %s", action_id, item.id)
            failed += 1
            reasons[_BULK_FALLBACK_REASON] += 1
        if n % BULK_COMMIT_EVERY == 0:
            db.commit()

    errors = [
        f"{n} card{'' if n == 1 else 's'}: {reason}"
        for reason, n in reasons.most_common(5)  # a batch failing wholesale doesn't need a long list
    ]
    db.commit()
    return BulkReviewActionResult(matched=matched, succeeded=succeeded, failed=failed, errors=errors,
                                  remaining=max(matched - offset - len(items), 0))


@router.post("/{item_id}/reopen", response_model=ReviewQueueItemOut)
def reopen_review_item(
    item_id: uuid.UUID, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)
) -> ReviewQueueItemOut:
    """Puts a rejected item back into the pending queue - the safety net
    for "I dismissed a batch of these too quickly and want a second look
    at one." Only for a card closed with a button that changed nothing
    (ReviewAction.reopenable, e.g. dedupe.py's "Keep as separate
    contacts"): putting it back is then completely safe - nothing to undo,
    nothing that could double-apply. Refused for everything else: an
    approved card already made its change, a snoozed card already set its
    new date, some rejected buttons write too ("No invoice needed" adds a
    note, "Needs a fix" tells the salesperson), and a card the system
    closed itself has no button to press again."""
    item = db.get(ReviewQueueItem, item_id)
    if not item or not _is_visible(item, identity, db):
        raise HTTPException(status_code=404, detail="Review item not found")
    if item.status == "pending":
        raise HTTPException(status_code=400, detail="This card is already waiting for review.")
    action = get_action(item.kind, item.resolved_action) if item.resolved_action else None
    if item.status != "rejected" or not action or not action.reopenable:
        raise HTTPException(
            status_code=400,
            detail=(
                "This card can't be reopened, because what was decided on it has already been carried out. "
                "Make any further change on the record itself."
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
