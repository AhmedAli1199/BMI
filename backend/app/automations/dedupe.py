"""CS-004 (Duplicate & Moved-Person Record Merging). Runs entirely against
data already in Postgres - no mailbox, no AI required, unblocked from day
one. Finds likely-duplicate contacts within the same source_db (contacts
are deliberately kept separate per title - see contact.py's docstring, so
a merge never crosses that boundary) using trigram name similarity,
corroborated by the real activity/company association data from the
2026-09-18 backfill (two contacts sharing an activity or a company link is
much stronger evidence than name similarity alone).

Every merge is queued for a human to confirm - there is no auto-merge
path. A false merge is effectively irreversible (child records get
reassigned), so this is treated with the same care as departure.py's
successor-confirmation flow.

"Merge" here means: move every Note/History/Activity/Opportunity/Phone/
Email/Address/GroupMembership/ContactCompanyLink/ActivityContact off the
losing record onto the surviving one, then flag the loser retired (via
custom_fields - no schema change needed) rather than deleting it, so its
own provenance (source_db/source_act_id) and history of existing is never
lost.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.automations.registry import ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.automations.state import get_state, set_state
from app.core.config import settings
from app.db.session import SessionLocal
from app.models import (
    Activity,
    ActivityContact,
    Contact,
    ContactCompanyLink,
    Email,
    GroupMembership,
    HistoryEntry,
    Note,
    Opportunity,
    Phone,
    ReviewQueueItem,
)
from app.models.contact_channel import Address


def _label(contact: Contact) -> str:
    return contact.full_name or " ".join(filter(None, [contact.first_name, contact.last_name])) or "(no name)"


def _reassign_simple(db: Session, model, fk_col: str, loser_id: uuid.UUID, survivor_id: uuid.UUID) -> None:
    """For child records with no uniqueness constraint tying them to their
    parent (Note, HistoryEntry, Phone, Email, Address, Opportunity) - a
    plain bulk UPDATE is always safe, there's nothing it could conflict
    with."""
    db.query(model).filter(getattr(model, fk_col) == loser_id).update(
        {fk_col: survivor_id}, synchronize_session=False
    )


def _reassign_avoiding_duplicates(
    db: Session, model, fk_col: str, other_col: str, loser_id: uuid.UUID, survivor_id: uuid.UUID
) -> None:
    """For child records with a UNIQUE(fk_col, other_col) constraint
    (GroupMembership, ContactCompanyLink, ActivityContact) - moving a row
    from loser to survivor could collide with a row the survivor already
    has for that same other_col (e.g. both were already in the same
    group). Reassign only the ones that won't collide; drop the rest
    (survivor already has the equivalent link, so nothing is actually
    lost)."""
    survivor_others = {
        getattr(row, other_col)
        for row in db.query(model).filter(getattr(model, fk_col) == survivor_id).all()
    }
    loser_rows = db.query(model).filter(getattr(model, fk_col) == loser_id).all()
    for row in loser_rows:
        if getattr(row, other_col) in survivor_others:
            db.delete(row)  # survivor already has this link - the loser's copy is redundant
        else:
            setattr(row, fk_col, survivor_id)


def _merge_contacts(db: Session, survivor: Contact, loser: Contact) -> None:
    _reassign_avoiding_duplicates(db, GroupMembership, "contact_id", "group_id", loser.id, survivor.id)
    _reassign_avoiding_duplicates(db, ContactCompanyLink, "contact_id", "company_id", loser.id, survivor.id)
    _reassign_avoiding_duplicates(db, ActivityContact, "contact_id", "activity_id", loser.id, survivor.id)

    _reassign_simple(db, Phone, "contact_id", loser.id, survivor.id)
    _reassign_simple(db, Email, "contact_id", loser.id, survivor.id)
    _reassign_simple(db, Address, "contact_id", loser.id, survivor.id)
    _reassign_simple(db, Activity, "contact_id", loser.id, survivor.id)
    _reassign_simple(db, Opportunity, "contact_id", loser.id, survivor.id)

    # Notes/History use a polymorphic entity_type+entity_id pair, not a
    # dedicated FK column - reassign entity_id only where entity_type is
    # already 'contact'.
    db.query(Note).filter(Note.entity_type == "contact", Note.entity_id == loser.id).update(
        {"entity_id": survivor.id}, synchronize_session=False
    )
    db.query(HistoryEntry).filter(
        HistoryEntry.entity_type == "contact", HistoryEntry.entity_id == loser.id
    ).update({"entity_id": survivor.id}, synchronize_session=False)

    loser.custom_fields = {
        **(loser.custom_fields or {}),
        "_merged_into": str(survivor.id),
        "_merged_at": datetime.now(timezone.utc).isoformat(),
        "_merge_reason": "Confirmed duplicate via review queue",
    }


def _handle_duplicate(db: Session, item: ReviewQueueItem, action_id: str, input_data: dict) -> None:
    candidate = item.payload.get("candidate") or {}
    loser_id = candidate.get("contact_id")
    survivor_id = str(item.entity_id) if item.entity_id else None
    if not loser_id or not survivor_id:
        raise ValueError("This review item is missing one of the two contact records - can't act on it.")

    survivor = db.get(Contact, uuid.UUID(survivor_id))
    loser = db.get(Contact, uuid.UUID(loser_id))
    if not survivor or not loser:
        raise ValueError("One of these contacts no longer exists - it may already have been merged or deleted.")

    if action_id == "merge":
        _merge_contacts(db, survivor, loser)
    elif action_id == "not_duplicate":
        pass  # No write - reviewer says these are genuinely two different people.
    else:
        raise ValueError(f"Unknown action {action_id!r} for duplicate_contact")


register(ReviewKind(
    kind="duplicate_contact",
    label="Possible duplicate contact",
    description=(
        "Two contact records in the same database look like the same person. Merging moves every "
        "note, history entry, activity, and group membership from the older record onto the one you "
        "keep, then retires the other - it never deletes anything outright, but it can't be undone "
        "from this screen, so double-check before confirming."
    ),
    actions=[
        ReviewAction(
            id="merge", label="Merge - same person", style="primary", outcome="approved",
            confirm_message="This moves every note, history, activity and group membership from the "
                             "older record onto the one shown as the survivor, then retires the other. Continue?",
        ),
        ReviewAction(id="not_duplicate", label="Not a duplicate", style="destructive", outcome="rejected"),
    ],
    handler=_handle_duplicate,
))


_DEDUPE_CURSOR_KEY = "dedupe_scan_cursor"


def scan_for_duplicates() -> None:
    """Producer job: fuzzy-matches contact names within each source_db via
    pg_trgm, corroborates with shared company/activity links, and queues
    the strongest candidates above the confidence floor.

    The outer side of the match is paginated by contact id (cursor stored
    via app.automations.state, wrapping back to the start once it reaches
    the end) rather than scanning every contact on every run. This matters
    a lot in practice: the LATERAL join below uses the GIN trigram index
    correctly on its *inner* side, but the query planner still has to
    drive that lookup once per *outer* row - with no cap there, cost scales
    with total contact count, not with dedupe_max_per_run, and a real
    contact table (tens of thousands of rows) can turn "every candidate
    pair" into a query that runs for minutes and gets killed by the
    database's own statement timeout - which surfaces as a bare "job
    failed" with nothing more specific in the logs. DEDUPE_BATCH_SIZE
    caps that outer side to a fixed, predictable amount of work per run
    regardless of how large contacts grows over time; the weekly cron
    just takes more runs to sweep the whole table, which is fine for a
    non-urgent, human-reviewed suggestion queue.
    """
    db = SessionLocal()
    try:
        already_queued_pairs: set[frozenset[str]] = set()
        for item in db.query(ReviewQueueItem).filter(
            ReviewQueueItem.kind == "duplicate_contact", ReviewQueueItem.status == "pending"
        ):
            ids = {e["id"] for e in item.payload.get("related_entities", []) if e.get("type") == "contact"}
            if len(ids) == 2:
                already_queued_pairs.add(frozenset(ids))

        cursor = get_state(db, _DEDUPE_CURSOR_KEY).get("last_contact_id")

        # Fetch this run's page of "a" contacts first, as a plain id list -
        # a fast, single-index lookup (id > cursor, ORDER BY id LIMIT n).
        # This is what actually bounds the work below: everything after
        # this touches at most DEDUPE_BATCH_SIZE "a" contacts, however big
        # `contacts` grows over time, instead of scanning the whole table
        # every run (see this function's docstring for why that mattered).
        page_ids = db.execute(
            text(
                "SELECT id FROM contacts WHERE NOT (custom_fields ? '_merged_into') "
                "AND (CAST(:cursor AS uuid) IS NULL OR id > CAST(:cursor AS uuid)) "
                "ORDER BY id LIMIT :batch_size"
            ),
            {"cursor": cursor, "batch_size": settings.dedupe_batch_size},
        ).scalars().all()

        # Advance (or wrap) the cursor now, based on the page itself - not
        # on how many candidate pairs it produced, so a quiet page of
        # contacts still moves the sweep forward next run rather than
        # getting stuck re-scanning it forever.
        set_state(db, _DEDUPE_CURSOR_KEY, {"last_contact_id": str(max(page_ids)) if page_ids else None})

        rows = []
        if page_ids:
            # Top-3 nearest-by-trigram-similarity match per contact, using
            # the GIN trigram index (the `%` operator) rather than a full
            # O(n^2) self-join - see migration 0012's docstring on why a
            # plain btree can't do this. The inner side still scans all of
            # `contacts` per outer row (that's what the index is for); only
            # the outer side (`page_ids`, capped above) bounds the total
            # work.
            rows = db.execute(
                text(
                    "SELECT a.id AS a_id, b.id AS b_id, similarity(a.full_name, b.full_name) AS sim, "
                    "a.company_id AS a_company, b.company_id AS b_company "
                    "FROM contacts a "
                    "JOIN LATERAL ("
                    "  SELECT b.id, b.full_name, b.company_id, similarity(a.full_name, b.full_name) AS sim "
                    "  FROM contacts b "
                    "  WHERE b.source_db = a.source_db AND b.id <> a.id AND b.full_name % a.full_name"
                    "    AND NOT (b.custom_fields ? '_merged_into')"
                    "  ORDER BY sim DESC LIMIT 3"
                    ") b ON true "
                    "WHERE a.id = ANY(:page_ids) "
                    f"ORDER BY sim DESC LIMIT {settings.dedupe_max_per_run * 3}"
                ),
                {"page_ids": page_ids},
            ).all()

        # Corroborating signal: do these two contacts share an activity?
        shared_activity_pairs: set[frozenset[str]] = set()
        if rows:
            candidate_ids = {str(r.a_id) for r in rows} | {str(r.b_id) for r in rows}
            links = db.execute(
                text(
                    "SELECT activity_id, contact_id FROM activity_contacts "
                    "WHERE contact_id = ANY(:ids)"
                ),
                {"ids": list(candidate_ids)},
            ).all()
            by_activity: dict[str, set[str]] = {}
            for link in links:
                by_activity.setdefault(str(link.activity_id), set()).add(str(link.contact_id))
            for contacts_on_activity in by_activity.values():
                if len(contacts_on_activity) >= 2:
                    for x in contacts_on_activity:
                        for y in contacts_on_activity:
                            if x != y:
                                shared_activity_pairs.add(frozenset({x, y}))

        queued = 0
        for row in rows:
            if queued >= settings.dedupe_max_per_run:
                break
            pair = frozenset({str(row.a_id), str(row.b_id)})
            if pair in already_queued_pairs:
                continue
            already_queued_pairs.add(pair)

            confidence = float(row.sim)
            if row.a_company and row.a_company == row.b_company:
                confidence = min(1.0, confidence + 0.15)
            if pair in shared_activity_pairs:
                confidence = min(1.0, confidence + 0.1)
            if confidence < settings.dedupe_confidence_floor:
                continue

            survivor = db.get(Contact, row.a_id)
            candidate_contact = db.get(Contact, row.b_id)
            if not survivor or not candidate_contact:
                continue

            db.add(ReviewQueueItem(
                id=uuid.uuid4(),
                kind="duplicate_contact",
                entity_type="contact",
                entity_id=survivor.id,
                payload={
                    "summary": f"\"{_label(survivor)}\" and \"{_label(candidate_contact)}\" look like the same person",
                    "details": [
                        {"key": "name_similarity", "label": "Name similarity", "value": f"{row.sim:.0%}"},
                        {"key": "same_company", "label": "Same company", "value": "Yes" if row.a_company == row.b_company and row.a_company else "No"},
                        {"key": "shared_activity", "label": "Shares an activity", "value": "Yes" if pair in shared_activity_pairs else "No"},
                    ],
                    "related_entities": [
                        {"type": "contact", "id": str(survivor.id), "label": f"{_label(survivor)} (keep this one)"},
                        {"type": "contact", "id": str(candidate_contact.id), "label": f"{_label(candidate_contact)} (would be retired)"},
                    ],
                    "candidate": {"contact_id": str(candidate_contact.id), "label": _label(candidate_contact)},
                    "confidence": round(confidence, 2),
                },
            ))
            queued += 1

        db.commit()
        print(f"duplicate_contact scan: {queued} new item(s) queued "
              f"({len(rows)} raw candidate pairs, {len(already_queued_pairs) - queued} already pending/skipped)")
    finally:
        db.close()


register_job(ScheduledJob(
    id="cs004_dedupe_scan",
    label="Duplicate contact scan",
    description="Fuzzy-matches contact names within each database and flags likely duplicates for review.",
    cron="0 3 * * 0",  # weekly, Sunday 3am UTC - low-frequency, non-urgent, and avoids competing with daytime jobs
    func=scan_for_duplicates,
    enabled_flag="automations_dedupe_scan_enabled",
))
