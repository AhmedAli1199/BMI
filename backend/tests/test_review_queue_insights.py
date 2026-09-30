"""Queue Insights - bucketed counts for the 3 kinds that already compute
a categorizing value at ingestion time (confidence / severity /
replacements), and the matching ?bucket= filter on the list endpoint.
See review_queue.py's _INSIGHT_BUCKETS / _bucket_condition."""
import uuid

from app.models import ReviewQueueItem


def _dup_item(db_session, confidence: float, *, status: str = "pending") -> ReviewQueueItem:
    item = ReviewQueueItem(
        id=uuid.uuid4(), kind="duplicate_contact", source_db="onboard",
        payload={"summary": "Maybe a duplicate", "confidence": confidence},
        status=status,
    )
    db_session.add(item)
    db_session.flush()
    return item


def _bounce_item(db_session, kind: str, severity: str, *, status: str = "pending") -> ReviewQueueItem:
    item = ReviewQueueItem(
        id=uuid.uuid4(), kind=kind, source_db="onboard",
        payload={"summary": "A bounce", "severity": severity, "confidence": 0.5},
        status=status,
    )
    db_session.add(item)
    db_session.flush()
    return item


def _ooo_item(db_session, replacements: list, *, status: str = "pending") -> ReviewQueueItem:
    item = ReviewQueueItem(
        id=uuid.uuid4(), kind="ooo_ambiguous", source_db="onboard",
        payload={"summary": "Out of office", "replacements": replacements},
        status=status,
    )
    db_session.add(item)
    db_session.flush()
    return item


def test_duplicate_contact_confidence_buckets(client, db_session):
    _dup_item(db_session, 0.95)
    _dup_item(db_session, 0.92)
    _dup_item(db_session, 0.75)
    _dup_item(db_session, 0.5)

    resp = client.get("/api/review-queue/insights?kind=duplicate_contact")
    assert resp.status_code == 200
    buckets = {b["key"]: b["count"] for b in resp.json()["buckets"]}
    assert buckets == {"high": 2, "medium": 1, "low": 1}


def test_bounce_severity_buckets(client, db_session):
    _bounce_item(db_session, "bounce_uncertain", "hard")
    _bounce_item(db_session, "bounce_uncertain", "hard")
    _bounce_item(db_session, "bounce_uncertain", "soft")

    resp = client.get("/api/review-queue/insights?kind=bounce_uncertain")
    assert resp.status_code == 200
    buckets = {b["key"]: b["count"] for b in resp.json()["buckets"]}
    assert buckets == {"hard": 2, "soft": 1}


def test_ooo_replacement_buckets(client, db_session):
    _ooo_item(db_session, [{"name": "Bhavisha Hartley", "email": "b@chubb.com"}])
    _ooo_item(db_session, [])

    resp = client.get("/api/review-queue/insights?kind=ooo_ambiguous")
    assert resp.status_code == 200
    buckets = {b["key"]: b["count"] for b in resp.json()["buckets"]}
    assert buckets == {"has_replacement": 1, "no_replacement": 1}


def test_ooo_item_missing_replacements_key_counts_as_no_replacement(client, db_session):
    """An older item queued before this field existed, or any future
    caller that never sets it, must not silently vanish from both
    buckets - jsonb_array_length(NULL) is NULL, so this specifically
    exercises the coalesce-to-[] in _replacements_len_expr."""
    item = ReviewQueueItem(
        id=uuid.uuid4(), kind="ooo_ambiguous", source_db="onboard",
        payload={"summary": "Out of office"},  # no "replacements" key at all
        status="pending",
    )
    db_session.add(item)
    db_session.flush()

    resp = client.get("/api/review-queue/insights?kind=ooo_ambiguous")
    buckets = {b["key"]: b["count"] for b in resp.json()["buckets"]}
    assert buckets["no_replacement"] == 1
    assert buckets["has_replacement"] == 0


def test_insights_only_counts_the_requested_status(client, db_session):
    _dup_item(db_session, 0.95, status="pending")
    _dup_item(db_session, 0.95, status="approved")

    resp = client.get("/api/review-queue/insights?kind=duplicate_contact&status=pending")
    buckets = {b["key"]: b["count"] for b in resp.json()["buckets"]}
    assert buckets["high"] == 1


def test_kind_with_no_configured_buckets_returns_empty_list(client, db_session):
    resp = client.get("/api/review-queue/insights?kind=followup_due")
    assert resp.status_code == 200
    assert resp.json()["buckets"] == []


def test_bucket_filter_narrows_the_list(client, db_session):
    high = _dup_item(db_session, 0.95)
    low = _dup_item(db_session, 0.5)

    resp = client.get("/api/review-queue?kind=duplicate_contact&bucket=high")
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert str(high.id) in ids
    assert str(low.id) not in ids


def test_bucket_without_kind_is_rejected(client, db_session):
    resp = client.get("/api/review-queue?bucket=high")
    assert resp.status_code == 400


def test_unrecognized_bucket_for_kind_is_rejected(client, db_session):
    resp = client.get("/api/review-queue?kind=duplicate_contact&bucket=not-a-real-bucket")
    assert resp.status_code == 400

