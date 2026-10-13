"""The shared calendar: merging, moves and cancellations, the recording rules, and booking the bot."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from tests.conftest import make_user

from app.core.config import settings
from app.models import CallRecording
from app.models.calendar import CalendarAttendance, CalendarConnection, CalendarMeeting
from app.services import calendar_sync as cs
from app.services import notetaker
from app.services.calendar_providers import CalEvent, find_link, link_identity

NOW = datetime(2026, 10, 14, 9, 0, tzinfo=timezone.utc)
CLIENT = {"email": "sarah@caribbean.example", "name": "Sarah Jones", "response": "accepted"}


def ev(id_, start, *, link="https://meet.google.com/abc-defg-hij", title="Spring campaign", me="accepted", private=False,
       people=None, uid=None):
    return CalEvent(id=id_, ical_uid=uid, title=title, start=start, end=start + timedelta(minutes=30), all_day=False,
                    join_url=link, organizer_email="matt@bmipublishing.co.uk", organizer_name="Matt",
                    attendees=people if people is not None else [CLIENT], my_response=me, is_private=private)


def conn(db, user, provider="google", email=None):
    c = CalendarConnection(id=uuid.uuid4(), user_id=user.id, provider=provider, email=email or user.email, refresh_token_enc="x")
    db.add(c)
    db.flush()
    return c


@pytest.fixture
def people(db_session):
    matt = make_user(db_session, email="matt@bmipublishing.co.uk", name="Matt")
    sam = make_user(db_session, email="sam@bmipublishing.co.uk", name="Samantha")
    return matt, sam, conn(db_session, matt, "microsoft"), conn(db_session, sam, "google")


def meetings(db):
    return db.query(CalendarMeeting).order_by(CalendarMeeting.start_at).all()


def test_link_parsing_matches_however_it_was_written():
    a = link_identity(*find_link("Join https://teams.microsoft.com/l/meetup-join/19%3ameeting_XyZ%40thread.v2/0?context=%7b%7d"))
    b = link_identity(*find_link("<https://teams.microsoft.com/l/meetup-join/19:meeting_xyz@thread.v2/0?context={}>"))
    assert a == b
    assert find_link("Join Zoom https://us02web.zoom.us/j/123456?pwd=x")[1] == "zoom"


def test_same_meeting_in_two_calendars_is_one_meeting(db_session, people):
    matt, sam, cm, cg = people
    start = NOW + timedelta(hours=2)
    cs.sync_connection(db_session, cm, NOW, [ev("ms-1", start, me="organizer")])
    cs.sync_connection(db_session, cg, NOW, [ev("g-1", start, link="https://meet.google.com/abc-defg-hij?authuser=1", title="Invite: Spring")])
    ms = meetings(db_session)
    assert len(ms) == 1
    assert ms[0].title == "Spring campaign"   # the organiser's copy wins
    assert {a.user_id for a in cs.attending(db_session, ms[0])} == {matt.id, sam.id}


def test_moves_cancels_and_partial_removals(db_session, people):
    matt, sam, cm, cg = people
    start = NOW + timedelta(hours=2)
    cs.sync_connection(db_session, cm, NOW, [ev("ms-1", start)])
    cs.sync_connection(db_session, cg, NOW, [ev("g-1", start)])
    first = meetings(db_session)[0]
    first.record_override = "skip"
    # moved by an hour in both calendars
    later = start + timedelta(hours=1)
    cs.sync_connection(db_session, cm, NOW, [ev("ms-1", later)])
    cs.sync_connection(db_session, cg, NOW, [ev("g-1", later)])
    db_session.refresh(first)
    active = [m for m in meetings(db_session) if m.status == "active"]
    assert first.status == "cancelled" and len(active) == 1 and active[0].start_at == later
    assert active[0].record_override == "skip"   # the one-off choice followed it
    # Samantha deletes it from her calendar: still on Matt's, so it stays
    cs.sync_connection(db_session, cg, NOW, [])
    assert active[0].status == "active" and len(cs.attending(db_session, active[0])) == 1
    # gone from Matt's too: cancelled
    cs.sync_connection(db_session, cm, NOW, [])
    db_session.refresh(active[0])
    assert active[0].status == "cancelled"


def test_rules(db_session, people, monkeypatch):
    matt, sam, cm, cg = people
    t = NOW + timedelta(hours=3)
    cs.sync_connection(db_session, cm, NOW, [
        ev("a", t, title="External"),
        ev("b", t + timedelta(hours=1), link="https://us02web.zoom.us/j/1", title="Zoom"),
        ev("c", t + timedelta(hours=2), link=None, title="No link"),
        ev("d", t + timedelta(hours=3), me="declined", title="Declined"),
        ev("e", t + timedelta(hours=4), private=True, title="Private"),
        ev("f", t + timedelta(hours=5), people=[{"email": "sam@bmipublishing.co.uk", "name": "Sam", "response": "accepted"}], title="Internal",
           link="https://meet.google.com/zzz-zzzz-zzz"),
    ])
    reason = {m.title: cs.should_record(db_session, m) for m in meetings(db_session)}
    assert reason["External"].record
    assert reason["Zoom"].reason == "Zoom calls aren't supported yet"
    assert reason["No link"].reason == "No meeting link"
    assert reason["Declined"].reason == "Everyone at BMI declined"
    assert reason["Private"].reason == "Marked private"
    assert reason["Internal"].record   # internal meetings are on by default
    monkeypatch.setattr(settings, "calendar_include_internal", False)
    internal = next(m for m in meetings(db_session) if m.title == "Internal")
    assert cs.should_record(db_session, internal).reason.startswith("Only BMI people")
    matt.preferences = {cs.PREF_KEY: "remind"}
    ext = next(m for m in meetings(db_session) if m.title == "External")
    d = cs.should_record(db_session, ext)
    assert not d.record and d.remind
    ext.record_override = "record"
    assert cs.should_record(db_session, ext).record


def test_plan_books_once_and_calls_off(db_session, people, monkeypatch):
    matt, sam, cm, cg = people
    monkeypatch.setattr(settings, "notetaker_url", "http://nt")
    monkeypatch.setattr(settings, "notetaker_api_key", "k")
    sent, stopped = [], []
    monkeypatch.setattr(notetaker, "send_bot", lambda **kw: sent.append(kw) or {"id": f"nt_{len(sent)}", "status": "scheduled", "platform": "google_meet"})
    monkeypatch.setattr(notetaker, "stop_bot", lambda nid: stopped.append(nid))
    start = NOW + timedelta(minutes=10)
    cs.sync_connection(db_session, cm, NOW, [ev("ms-1", start, me="organizer")])
    cs.sync_connection(db_session, cg, NOW, [ev("g-1", start)])
    assert cs.plan(db_session, NOW)["booked"] == 1
    assert cs.plan(db_session, NOW)["booked"] == 0   # not twice
    assert len(sent) == 1 and sent[0]["join_at"] == start - timedelta(minutes=1)
    m = meetings(db_session)[0]
    call = db_session.get(CallRecording, m.call_id)
    assert call.user_id == matt.id and call.calendar_meeting_id == m.id   # the organiser owns the notes
    # someone presses Skip before it starts: the bot is called off
    m.record_override = "skip"
    assert cs.plan(db_session, NOW)["called_off"] == 1 and stopped == ["nt_1"]
    # far-off meetings aren't booked yet
    cs.sync_connection(db_session, cm, NOW, [ev("ms-1", start, me="organizer"), ev("ms-2", NOW + timedelta(days=2))])
    assert cs.plan(db_session, NOW)["booked"] == 0


def test_cancelled_after_booking_calls_off(db_session, people, monkeypatch):
    matt, sam, cm, cg = people
    monkeypatch.setattr(settings, "notetaker_url", "http://nt")
    monkeypatch.setattr(settings, "notetaker_api_key", "k")
    stopped = []
    monkeypatch.setattr(notetaker, "send_bot", lambda **kw: {"id": "nt_9", "status": "scheduled"})
    monkeypatch.setattr(notetaker, "stop_bot", lambda nid: stopped.append(nid))
    cs.sync_connection(db_session, cm, NOW, [ev("ms-1", NOW + timedelta(minutes=5))])
    cs.plan(db_session, NOW)
    cs.sync_connection(db_session, cm, NOW, [])   # the meeting is deleted
    cs.plan(db_session, NOW)
    assert stopped == ["nt_9"]
