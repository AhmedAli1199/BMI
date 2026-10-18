"""Repeating activities: marking one done schedules the next one."""
import uuid
from datetime import datetime, timedelta, timezone

from tests.conftest import identity_headers, make_user

from app.models import Activity, Contact
from app.services.activity_repeats import schedule_next


def _contact(db):
    ct = Contact(id=uuid.uuid4(), source_db="onboard", source_act_id=str(uuid.uuid4()), full_name="Sarah Jones")
    db.add(ct)
    db.flush()
    return ct


def test_marking_a_repeating_activity_done_schedules_the_next(client, db_session):
    me = make_user(db_session, role="admin")
    ct = _contact(db_session)
    h = identity_headers(me)
    start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0)
    r = client.post("/api/activities", json={"activity_type": "Call", "subject": "Weekly check-in", "start_at": start.isoformat(),
                                             "end_at": (start + timedelta(minutes=30)).isoformat(), "recurrence": "weekly",
                                             "contact_id": str(ct.id), "source_db": "onboard"}, headers=h)
    assert r.status_code == 201, r.text
    first = r.json()["id"]
    assert db_session.query(Activity).filter_by(contact_id=ct.id).count() == 1     # only the next one is on the calendar
    assert client.patch(f"/api/activities/{first}", json={"is_cleared": True}, headers=h).status_code == 200
    rows = db_session.query(Activity).filter_by(contact_id=ct.id).order_by(Activity.start_at).all()
    assert len(rows) == 2 and not rows[1].is_cleared and rows[1].recurrence == "weekly" and rows[1].subject == "Weekly check-in"
    assert rows[1].start_at == start + timedelta(weeks=1) and rows[1].end_at - rows[1].start_at == timedelta(minutes=30)
    # undone and done again: no second copy
    client.patch(f"/api/activities/{first}", json={"is_cleared": False}, headers=h)
    client.patch(f"/api/activities/{first}", json={"is_cleared": True}, headers=h)
    assert db_session.query(Activity).filter_by(contact_id=ct.id).count() == 2


def test_next_one_is_after_today_and_months_keep_their_day(db_session):
    ct = _contact(db_session)
    now = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
    late = Activity(id=uuid.uuid4(), source_db="onboard", source_act_id="x1", contact_id=ct.id, activity_type="Call", subject="Weekly",
                    start_at=datetime(2026, 9, 28, 9, 0, tzinfo=timezone.utc), recurrence="weekly", priority="normal")
    monthly = Activity(id=uuid.uuid4(), source_db="onboard", source_act_id="x2", contact_id=ct.id, activity_type="To-do", subject="Month end",
                       start_at=datetime(2026, 10, 31, 9, 0, tzinfo=timezone.utc), recurrence="monthly", priority="normal")
    once = Activity(id=uuid.uuid4(), source_db="onboard", source_act_id="x3", contact_id=ct.id, activity_type="Call", subject="Once",
                    start_at=now, recurrence="never", priority="normal")
    db_session.add_all([late, monthly, once])
    db_session.flush()
    assert schedule_next(db_session, late, now).start_at == datetime(2026, 10, 19, 9, 0, tzinfo=timezone.utc)   # cleared late: not overdue
    assert schedule_next(db_session, monthly, now).start_at == datetime(2026, 11, 30, 9, 0, tzinfo=timezone.utc)
    assert schedule_next(db_session, once, now) is None
