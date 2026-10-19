"""Calendar & tasks: paging and the Overdue count come from the server, so they cover every activity."""
import uuid
from datetime import datetime, timedelta, timezone

from tests.conftest import identity_headers, make_user

from app.models import Activity, Contact


def _setup(db):
    ct = Contact(id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()), full_name="Sarah Jones")
    db.add(ct)
    db.flush()
    now = datetime.now(timezone.utc)

    def add(days: int, cleared: bool = False, priority: str = "normal"):
        db.add(Activity(id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()), contact_id=ct.id,
                        activity_type="Call", subject=f"Call {days}", start_at=now + timedelta(days=days),
                        is_cleared=cleared, priority=priority))

    for d in range(1, 6):
        add(-d)                      # 5 overdue, not done
    add(-10, cleared=True)           # overdue date, but done - not counted
    add(-3, priority="high")         # 1 more overdue, high priority
    for d in range(1, 4):
        add(d)                       # 3 coming up
    db.flush()
    return ct, now


def test_overdue_count_covers_every_activity_not_just_one_page(client, db_session):
    _setup(db_session)
    h = identity_headers(make_user(db_session, role="admin"))
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    r = client.get("/api/activities", params={"source_db": "onboard", "is_cleared": "false", "page_size": 2,
                                              "overdue_before": today.isoformat()}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["items"]) == 2 and body["total"] == 9
    assert body["overdue_total"] == 6
    # Same other filters apply to the count.
    r = client.get("/api/activities", params={"source_db": "onboard", "priority": "high", "page_size": 1,
                                              "overdue_before": today.isoformat()}, headers=h)
    assert r.json()["overdue_total"] == 1


def test_overdue_count_is_left_out_unless_asked_for(client, db_session):
    _setup(db_session)
    h = identity_headers(make_user(db_session, role="admin"))
    assert client.get("/api/activities", params={"source_db": "onboard"}, headers=h).json()["overdue_total"] is None


def test_pages_walk_through_everything(client, db_session):
    _setup(db_session)
    h = identity_headers(make_user(db_session, role="admin"))
    seen = []
    for page in (1, 2, 3):
        body = client.get("/api/activities", params={"source_db": "onboard", "page": page, "page_size": 4}, headers=h).json()
        seen += [i["id"] for i in body["items"]]
    assert len(seen) == 10 and len(set(seen)) == 10
