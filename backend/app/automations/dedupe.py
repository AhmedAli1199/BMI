"""CS-004 (Duplicate & Moved-Person Record Merging). Runs entirely against
data already in Postgres - no mailbox, no AI required, unblocked from day
one. Finds likely-duplicate contacts within the same source_db (contacts
are deliberately kept separate per title - see contact.py's docstring, so
a merge never crosses that boundary) using trigram name similarity to
generate candidate pairs, then scores each pair on as many comparable
fields as both sides actually have data for (see _score_pair /
_FIELD_WEIGHTS): company, email, phone, postcode/city, plus whether they
share an activity. A perfect name match alone deliberately cannot reach
100% confidence - matching names is real evidence, but on its own it
isn't proof of the same person (shared names happen; two duplicate
records can also have a name that only fuzzy-matches), and reporting
"100% confident" from name alone would mislead a reviewer into thinking
every field matched when only one did.

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

import re
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.automations.registry import ReviewAction, ReviewKind, register
from app.automations.scheduler import ScheduledJob, register_job
from app.automations.state import get_state, set_state
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


# How much each comparable field contributes to overall confidence. These
# always sum to 1.0 - the point being that NO single field, however
# perfectly it matches, can push confidence past its own weight. A
# perfect name match alone tops out at 0.40, never 100% - matching names
# is real evidence, but two different people can share a name, and two
# duplicate records can have a name that only fuzzy-matches (a nickname,
# a typo) - name similarity earning the whole score, on its own, is
# exactly the misleading "100% confident" result this is designed not to
# produce. A field neither contact has data for contributes 0, same as an
# outright mismatch - "we don't know" is not evidence of a match, so it's
# never treated as one.
_FIELD_WEIGHTS = {
    "name": 0.40,
    "company": 0.20,
    "email": 0.15,
    "phone": 0.15,
    "location": 0.10,
}


def _normalize_phone(number: str | None) -> str | None:
    """Compares the last 9 digits only, so "+44 20 7946 0958", "020 7946
    0958" and "02079460958" all match despite different formatting/country
    prefixes - exact string equality would treat all of those as different
    phone numbers, which they aren't."""
    if not number:
        return None
    digits = re.sub(r"\D", "", number)
    return digits[-9:] if len(digits) >= 9 else (digits or None)


def _text_similarity(a: str | None, b: str | None) -> float | None:
    if not a or not b:
        return None
    return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()


def _fetch_contact_details(db: Session, contact_ids: set[uuid.UUID]) -> dict[uuid.UUID, dict]:
    """One batched fetch of the fields the confidence score needs -
    primary email, primary phone, primary address's postal code/city -
    for a bounded set of candidate contact ids (never the whole page;
    scan_for_duplicates only calls this with the handful of pairs that
    survived the trigram match). Deliberately not folded into the earlier
    raw-SQL query - that query's whole job is cheaply narrowing tens of
    thousands of contacts down to a short candidate list; the more
    detailed field comparison only ever needs to run on that short list."""
    if not contact_ids:
        return {}
    ids = list(contact_ids)
    result: dict[uuid.UUID, dict] = {cid: {} for cid in ids}

    for cid, address, is_primary in db.execute(
        select(Email.contact_id, Email.address, Email.is_primary).where(Email.contact_id.in_(ids))
    ).all():
        if "email" not in result[cid] or is_primary:
            result[cid]["email"] = address

    for cid, number, is_primary in db.execute(
        select(Phone.contact_id, Phone.number, Phone.is_primary).where(Phone.contact_id.in_(ids))
    ).all():
        if "phone" not in result[cid] or is_primary:
            result[cid]["phone"] = number

    for cid, postal, city, is_primary in db.execute(
        select(Address.contact_id, Address.postal_code, Address.city, Address.is_primary)
        .where(Address.contact_id.in_(ids))
    ).all():
        if "postal_code" not in result[cid] or is_primary:
            result[cid]["postal_code"] = postal
            result[cid]["city"] = city

    return result


def _score_pair(
    name_similarity: float,
    survivor: Contact,
    candidate: Contact,
    survivor_details: dict,
    candidate_details: dict,
    shares_activity: bool,
) -> tuple[float, list[dict]]:
    """Weighted multi-field confidence, 0.0-1.0 - see _FIELD_WEIGHTS. Also
    returns the per-field breakdown shown on the review card, so a
    reviewer sees exactly why a pair scored what it did (which field(s)
    corroborated, which couldn't be compared) rather than one opaque
    number."""
    scores: dict[str, float] = {"name": name_similarity}
    details: list[dict] = [
        {"key": "name_similarity", "label": "Name similarity", "value": f"{name_similarity:.0%}"}
    ]

    if survivor.company_id and candidate.company_id:
        scores["company"] = 1.0 if survivor.company_id == candidate.company_id else 0.0
        details.append({"key": "same_company", "label": "Same company", "value": "Yes" if scores["company"] else "No"})
    else:
        company_sim = _text_similarity(survivor.company_name_freetext, candidate.company_name_freetext)
        if company_sim is not None:
            scores["company"] = company_sim
            details.append({"key": "same_company", "label": "Similar company name", "value": f"{company_sim:.0%}"})
        else:
            details.append({"key": "same_company", "label": "Same company", "value": "Unknown - no data"})

    survivor_email = (survivor_details.get("email") or "").strip().lower()
    candidate_email = (candidate_details.get("email") or "").strip().lower()
    if survivor_email and candidate_email:
        scores["email"] = 1.0 if survivor_email == candidate_email else 0.0
        details.append({"key": "same_email", "label": "Same email", "value": "Yes" if scores["email"] else "No"})
    else:
        details.append({"key": "same_email", "label": "Same email", "value": "Unknown - no data"})

    survivor_phone = _normalize_phone(survivor_details.get("phone"))
    candidate_phone = _normalize_phone(candidate_details.get("phone"))
    if survivor_phone and candidate_phone:
        scores["phone"] = 1.0 if survivor_phone == candidate_phone else 0.0
        details.append({"key": "same_phone", "label": "Same phone", "value": "Yes" if scores["phone"] else "No"})
    else:
        details.append({"key": "same_phone", "label": "Same phone", "value": "Unknown - no data"})

    survivor_postal = (survivor_details.get("postal_code") or "").strip().lower()
    candidate_postal = (candidate_details.get("postal_code") or "").strip().lower()
    if survivor_postal and candidate_postal:
        scores["location"] = 1.0 if survivor_postal == candidate_postal else 0.0
        details.append({"key": "same_location", "label": "Same postcode", "value": "Yes" if scores["location"] else "No"})
    else:
        survivor_city = (survivor_details.get("city") or "").strip().lower()
        candidate_city = (candidate_details.get("city") or "").strip().lower()
        if survivor_city and candidate_city:
            scores["location"] = 1.0 if survivor_city == candidate_city else 0.0
            details.append({"key": "same_location", "label": "Same city", "value": "Yes" if scores["location"] else "No"})
        else:
            details.append({"key": "same_location", "label": "Same postcode/city", "value": "Unknown - no data"})

    confidence = sum(_FIELD_WEIGHTS[field] * value for field, value in scores.items())

    # Shared-activity is corroboration on top of the field comparison
    # above, not one of the weighted fields itself (it's a relationship
    # signal, not a property either contact "has" to compare) - a small
    # bonus, still capped at 1.0 overall.
    if shares_activity:
        confidence = min(1.0, confidence + 0.05)
    details.append({"key": "shared_activity", "label": "Shares an activity", "value": "Yes" if shares_activity else "No"})

    return confidence, details


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
    pair_ids = {str(item.entity_id) if item.entity_id else None, candidate.get("contact_id")} - {None}
    if len(pair_ids) != 2:
        raise ValueError("This review item is missing one of the two contact records - can't act on it.")

    # Which contact survives is the reviewer's call (requires_related_entity_choice
    # on "merge", below) - default to the automation's original guess
    # (item.entity_id) only for items queued before this choice existed,
    # so nothing already in the queue breaks.
    chosen = input_data.get("chosen_entity_id")
    survivor_id = chosen if chosen in pair_ids else (str(item.entity_id) if item.entity_id else None)
    loser_id = next(iter(pair_ids - {survivor_id}))

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
    label="Duplicate Contact Resolution",
    description="Consolidates matching records to unify interaction history, notes, and activity records into a single profile.",
    actions=[
        ReviewAction(
            id="merge", label="Merge records", style="primary", outcome="approved",
            requires_related_entity_choice=True,
            confirm_message="This merges all notes, history, activities, and group memberships into the primary contact and archives the duplicate. Continue?",
        ),
        ReviewAction(id="not_duplicate", label="Keep as separate contacts", style="secondary", outcome="rejected"),
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
        dedupe_batch_size = runtime_settings.get_int(db, "dedupe_batch_size")
        dedupe_max_per_run = runtime_settings.get_int(db, "dedupe_max_per_run")
        dedupe_confidence_floor = runtime_settings.get_float(db, "dedupe_confidence_floor")

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
            {"cursor": cursor, "batch_size": dedupe_batch_size},
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
                    "SELECT a.id AS a_id, b.id AS b_id, similarity(a.full_name, b.full_name) AS sim "
                    "FROM contacts a "
                    "JOIN LATERAL ("
                    "  SELECT b.id, b.full_name, similarity(a.full_name, b.full_name) AS sim "
                    "  FROM contacts b "
                    "  WHERE b.source_db = a.source_db AND b.id <> a.id AND b.full_name % a.full_name"
                    "    AND NOT (b.custom_fields ? '_merged_into')"
                    "  ORDER BY sim DESC LIMIT 3"
                    ") b ON true "
                    "WHERE a.id = ANY(:page_ids) "
                    f"ORDER BY sim DESC LIMIT {dedupe_max_per_run * 3}"
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

        # Batch-fetch the extra fields the multi-field score needs, for
        # only the contacts actually involved in a surviving candidate
        # pair - never the whole page, see _fetch_contact_details.
        all_ids = {row.a_id for row in rows} | {row.b_id for row in rows}
        contacts_by_id = {c.id: c for c in db.query(Contact).filter(Contact.id.in_(all_ids))} if all_ids else {}
        details_by_id = _fetch_contact_details(db, all_ids)

        queued = 0
        for row in rows:
            if queued >= dedupe_max_per_run:
                break
            pair = frozenset({str(row.a_id), str(row.b_id)})
            if pair in already_queued_pairs:
                continue
            already_queued_pairs.add(pair)

            survivor = contacts_by_id.get(row.a_id)
            candidate_contact = contacts_by_id.get(row.b_id)
            if not survivor or not candidate_contact:
                continue

            confidence, details = _score_pair(
                float(row.sim),
                survivor,
                candidate_contact,
                details_by_id.get(row.a_id, {}),
                details_by_id.get(row.b_id, {}),
                pair in shared_activity_pairs,
            )
            if confidence < dedupe_confidence_floor:
                continue

            db.add(ReviewQueueItem(
                id=uuid.uuid4(),
                kind="duplicate_contact", source_db=survivor.source_db,
                entity_type="contact",
                entity_id=survivor.id,
                payload={
                    "summary": f"\"{_label(survivor)}\" and \"{_label(candidate_contact)}\" might be the same person",
                    "details": details,
                    # Plain labels, deliberately no "(keep this one)"/"(would be
                    # retired)" - which one survives is the reviewer's choice
                    # at action time (merge's requires_related_entity_choice),
                    # not something this scan should presume.
                    "related_entities": [
                        {"type": "contact", "id": str(survivor.id), "label": _label(survivor)},
                        {"type": "contact", "id": str(candidate_contact.id), "label": _label(candidate_contact)},
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
    cursor_prefix=_DEDUPE_CURSOR_KEY,
))
