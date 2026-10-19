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
    # 10 minutes out: people are told, but the bot isn't sent yet
    assert cs.plan(db_session, NOW)["booked"] == 0 and sent == []
    assert meetings(db_session)[0].notified_at == NOW
    # on the job run just before its join time it's sent "join now" - no join time for the bot service to wake it up
    soon = NOW + timedelta(minutes=7)
    assert cs.plan(db_session, soon)["booked"] == 1
    assert cs.plan(db_session, soon)["booked"] == 0   # not twice
    assert len(sent) == 1 and "join_at" not in sent[0] and sent[0]["end_at"] >= start
    m = meetings(db_session)[0]
    call = db_session.get(CallRecording, m.call_id)
    assert call.user_id == matt.id and call.calendar_meeting_id == m.id   # the organiser owns the notes
    # someone presses Skip before it starts: the bot is called off
    m.record_override = "skip"
    assert cs.plan(db_session, soon)["called_off"] == 1 and stopped == ["nt_1"]
    # far-off meetings aren't booked yet
    cs.sync_connection(db_session, cm, NOW, [ev("ms-1", start, me="organizer"), ev("ms-2", NOW + timedelta(days=2))])
    assert cs.plan(db_session, soon)["booked"] == 0


def test_cancelled_after_booking_calls_off(db_session, people, monkeypatch):
    matt, sam, cm, cg = people
    monkeypatch.setattr(settings, "notetaker_url", "http://nt")
    monkeypatch.setattr(settings, "notetaker_api_key", "k")
    stopped = []
    monkeypatch.setattr(notetaker, "send_bot", lambda **kw: {"id": "nt_9", "status": "scheduled"})
    monkeypatch.setattr(notetaker, "stop_bot", lambda nid: stopped.append(nid))
    cs.sync_connection(db_session, cm, NOW, [ev("ms-1", NOW + timedelta(minutes=3))])
    cs.plan(db_session, NOW)
    cs.sync_connection(db_session, cm, NOW, [])   # the meeting is deleted
    cs.plan(db_session, NOW)
    assert stopped == ["nt_9"]


def test_outcome_says_what_actually_happened(db_session, people, monkeypatch):
    matt, sam, cm, cg = people
    monkeypatch.setattr(settings, "notetaker_url", "")
    start = NOW + timedelta(minutes=10)
    cs.sync_connection(db_session, cm, NOW, [ev("ms-1", start, me="organizer")])
    m = meetings(db_session)[0]
    m.created_at = NOW - timedelta(days=1)
    d = cs.should_record(db_session, m)
    assert cs.outcome(m, None, d, NOW)["tone"] == "ok"
    cs.plan(db_session, NOW)   # notetaker not connected: the reason is kept
    after = start + timedelta(hours=1)
    o = cs.outcome(m, None, d, after)
    assert o["tone"] == "bad" and o["text"].startswith("Not recorded") and "isn't connected" in o["text"]
    # never tried at all (job not running)
    m.last_error = None
    assert "never sent" in cs.outcome(m, None, d, after)["text"]
    # booked but never joined / not let in / recorded
    call = CallRecording(id=uuid.uuid4(), user_id=matt.id, calendar_meeting_id=m.id, meeting_url=m.join_url, status="scheduled", status_label="Scheduled")
    assert "never joined" in cs.outcome(m, call, d, after)["text"]
    call.status = "not_admitted"
    assert "wasn't let into" in cs.outcome(m, call, d, after)["text"]
    call.status = "completed"
    assert cs.outcome(m, call, d, after) == {"tone": "ok", "text": "Recorded - the notes are in Call notes"}
    # the rules said no: past tense once it's over
    m.record_override = "skip"
    o = cs.outcome(m, None, cs.should_record(db_session, m), after)
    assert o == {"tone": "muted", "text": "Not recorded - skipped for this meeting"}


def test_start_over_keeps_connections_and_recorded_calls(db_session, people, monkeypatch):
    matt, sam, cm, cg = people
    monkeypatch.setattr(settings, "notetaker_url", "http://nt")
    monkeypatch.setattr(settings, "notetaker_api_key", "k")
    stopped = []
    monkeypatch.setattr(notetaker, "send_bot", lambda **kw: {"id": "nt_1", "status": "scheduled"})
    monkeypatch.setattr(notetaker, "stop_bot", lambda nid: stopped.append(nid))
    cs.sync_connection(db_session, cm, NOW, [ev("ms-1", NOW + timedelta(minutes=3)),
                                             ev("ms-2", NOW - timedelta(hours=3), link="https://meet.google.com/xyz-abcd-efg")])
    cs.plan(db_session, NOW)
    old = meetings(db_session)[0]
    done = CallRecording(id=uuid.uuid4(), user_id=matt.id, calendar_meeting_id=old.id, meeting_url=old.join_url, status="completed", status_label="Done")
    db_session.add(done)
    db_session.flush()
    out = cs.start_over(db_session)
    assert out["meetings"] == 2 and stopped == ["nt_1"] and out["calls_removed"] == 1
    assert meetings(db_session) == [] and db_session.query(CalendarAttendance).count() == 0
    assert db_session.query(CalendarConnection).count() == 2 and cm.last_synced_at is None
    db_session.refresh(done)
    assert done.calendar_meeting_id is None


def test_notetaker_check_and_start_over_are_admin_only(client, db_session, people, monkeypatch):
    from tests.conftest import identity_headers
    monkeypatch.setattr(settings, "notetaker_url", "")
    admin = make_user(db_session, role="admin", name="Ahmed")
    sales = make_user(db_session, role="sales", name="Tom")
    db_session.flush()
    assert client.get("/api/calendar/health", headers=identity_headers(sales)).status_code == 403
    r = client.get("/api/calendar/health", headers=identity_headers(admin))
    assert r.status_code == 200, r.text
    first = r.json()["checks"][0]
    assert first["label"] == "The notetaker service" and not first["ok"] and "haven't been added on the server" in first["text"]
    assert "NOTETAKER" not in first["text"]   # never the server setting names
    assert client.post("/api/calendar/start-over", headers=identity_headers(sales)).status_code == 403
    monkeypatch.setattr(cs, "sync_all", lambda db, force=False: 0)
    r = client.post("/api/calendar/start-over", headers=identity_headers(admin))
    assert r.status_code == 200 and r.json()["meetings"] == 0


def test_one_persons_automatic_recording_doesnt_record_everyone(db_session, people):
    matt, sam, cm, cg = people
    start = NOW + timedelta(hours=2)
    cs.sync_connection(db_session, cm, NOW, [ev("ms-1", start, me="organizer")])
    cs.sync_connection(db_session, cg, NOW, [ev("g-1", start)])
    m = meetings(db_session)[0]

    def rule(matt_pref, sam_pref):
        matt.preferences, sam.preferences = {cs.PREF_KEY: matt_pref}, {cs.PREF_KEY: sam_pref}
        db_session.flush()
        return cs.should_record(db_session, m)

    # Matt organised it: his choice decides
    assert not rule("off", "auto").record
    assert rule("auto", "off").record
    d = rule("remind", "auto")
    assert not d.record and d.remind
    # A client's invite, two of us in it: recorded only if someone wants it and nobody said no
    m.organizer_email = "sarah@caribbean.example"
    for a in cs.attending(db_session, m):
        a.response = "accepted"
    assert rule("auto", "remind").record
    assert rule("auto", "auto").record
    d = rule("auto", "off")
    assert not d.record and d.remind                     # they disagree: not recorded, a reminder instead
    d = rule("off", "off")
    assert not d.record and not d.remind
    # only Sam is in it: her calendar, her choice
    cs.sync_connection(db_session, cm, NOW, [])
    assert rule("off", "auto").record and not rule("auto", "off").record
