"""The shared calendar: merge everyone's calendars into one, decide which meetings get the notetaker,
and book (or call off) the bot.

Merging. The same meeting shows up in each invited person's calendar with a different event id. It's one
row in calendar_meetings, matched on (meeting room, start minute): the room comes from the Meet/Teams/Zoom
link (normalised, so differently-written links still match) - which also matches a Google user and an
Outlook user invited to the same call. Meetings with no link match on the calendar's own UID + start.
A moved meeting gets a new row (new start); the old one loses its last copy and is marked cancelled, so
its bot is called off and a new one is booked - any one-off Record/Skip choice is carried over.

Deciding (should_record). Plain-language reasons are kept so the calendar can say why, e.g.
"Everyone at BMI declined" or "Only BMI people (internal meetings are off)".
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.models import CallRecording, Contact, Email, User
from app.models.calendar import CalendarAttendance, CalendarConnection, CalendarMeeting
from app.services import calendar_providers as cp
from app.services import zoom

log = logging.getLogger(__name__)

WINDOW_BACK = timedelta(days=1)
WINDOW_AHEAD = timedelta(days=14)
BOOK_AHEAD = timedelta(minutes=20)      # people are told this long before the start that the notetaker will join
# The bot itself is sent "join now" once its join time is less than one job run away (the job runs every 3 minutes),
# exactly like pasting a link by hand. It used to be booked 20 minutes early with a join time, which relies on the
# bot service's own scheduler to wake it up later - when that scheduler isn't running, booked bots never join.
SEND_WINDOW = timedelta(minutes=3)
LATE_JOIN = timedelta(minutes=30)       # a meeting added late is still joined up to this long after it started
SYNC_EVERY = timedelta(minutes=4)
PREF_KEY = "calendar_recording"         # users.preferences: auto | remind | off
SUPPORTED = {"google_meet", "teams", "zoom"}


def now() -> datetime:
    return datetime.now(timezone.utc)


def dedupe_key(ev: cp.CalEvent, conn_id: uuid.UUID) -> str:
    start = ev.start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    room = cp.link_identity(ev.join_url, cp.find_link(ev.join_url)[1] if ev.join_url else None)
    if room:
        return f"room:{room}|{start}"[:600]
    if ev.ical_uid:
        return f"uid:{ev.ical_uid.lower()}|{start}"[:600]
    return f"event:{conn_id}:{ev.id}"[:600]


def _merge_people(old: list[dict], new: list[dict]) -> list[dict]:
    by = {p["email"]: p for p in old or []}
    for p in new:
        cur = by.get(p["email"])
        by[p["email"]] = {**(cur or {}), **{k: v for k, v in p.items() if v not in (None, "", "none") or not cur}}
    return sorted(by.values(), key=lambda p: p["email"])


# ---- Sync ---------------------------------------------------------------------------------------

def sync_connection(db: Session, conn: CalendarConnection, at: datetime | None = None,
                    events: list[cp.CalEvent] | None = None) -> int:
    """Reads one calendar and merges it in. `events` lets tests skip the network."""
    at = at or now()
    start, end = at - WINDOW_BACK, at + WINDOW_AHEAD
    if events is None:
        try:
            events = cp.fetch_events(db, conn, start, end)
        except cp.CalendarAuthError as e:
            conn.status, conn.last_error = "error", str(e)
            return 0
        except Exception:
            log.exception("Calendar read failed for %s", conn.email)
            conn.last_error = "We couldn't read this calendar just now - we'll try again in a few minutes."
            return 0
    seen: set[uuid.UUID] = set()
    touched: set[uuid.UUID] = set()   # meetings that lost one of this person's copies
    for ev in events:
        if ev.cancelled:
            continue
        key = dedupe_key(ev, conn.id)
        m = db.scalar(select(CalendarMeeting).where(CalendarMeeting.dedupe_key == key))
        if not m:
            m = CalendarMeeting(id=uuid.uuid4(), dedupe_key=key, start_at=ev.start, end_at=ev.end, attendees=[])
            db.add(m)
        _, platform = cp.find_link(ev.join_url)
        is_organizer_copy = ev.my_response == "organizer"
        if ev.title and (is_organizer_copy or not m.title):
            m.title = ev.title
        m.start_at, m.end_at, m.is_all_day = ev.start, ev.end, ev.all_day
        if ev.join_url and (is_organizer_copy or not m.join_url):
            m.join_url, m.platform = ev.join_url, platform
        m.organizer_email = m.organizer_email or ev.organizer_email
        m.organizer_name = m.organizer_name or ev.organizer_name
        people = list(ev.attendees)
        if ev.organizer_email and ev.organizer_email not in {p["email"] for p in people}:
            people.append({"email": ev.organizer_email, "name": ev.organizer_name, "response": "organizer"})
        m.attendees = _merge_people(m.attendees, people)
        m.status = "active"
        db.flush()

        att = db.scalar(select(CalendarAttendance).where(CalendarAttendance.connection_id == conn.id,
                                                         CalendarAttendance.provider_event_id == ev.id))
        if att and att.meeting_id != m.id:
            touched.add(att.meeting_id)
            old = db.get(CalendarMeeting, att.meeting_id)
            if old and old.record_override and not m.record_override:   # carry a one-off choice over a reschedule
                m.record_override, m.override_by_user_id = old.record_override, old.override_by_user_id
        if not att:
            att = CalendarAttendance(id=uuid.uuid4(), connection_id=conn.id, user_id=conn.user_id, provider_event_id=ev.id,
                                     meeting_id=m.id, last_seen_at=at)
            db.add(att)
        att.meeting_id, att.response, att.is_private, att.last_seen_at = m.id, ev.my_response, ev.is_private, at
        seen.add(att.id)
    db.flush()

    # This person's copies we didn't see this time (inside the window) are gone: deleted, cancelled or moved.
    stale = db.scalars(select(CalendarAttendance).join(CalendarMeeting, CalendarMeeting.id == CalendarAttendance.meeting_id)
                       .where(CalendarAttendance.connection_id == conn.id, CalendarMeeting.start_at >= start,
                              CalendarMeeting.start_at < end)).all()
    for a in stale:
        if a.id not in seen:
            touched.add(a.meeting_id)
            db.delete(a)
    db.flush()
    for mid in touched:
        if not db.scalar(select(CalendarAttendance.id).where(CalendarAttendance.meeting_id == mid).limit(1)):
            gone = db.get(CalendarMeeting, mid)
            if gone:
                gone.status = "cancelled"
    conn.last_synced_at, conn.last_error = at, None
    if conn.status != "connected":
        conn.status = "connected"
    db.flush()
    return len(events)


def sync_all(db: Session, force: bool = False) -> int:
    n = 0
    for conn in db.scalars(select(CalendarConnection)):
        if conn.status == "error" and not force:
            continue
        if not force and conn.last_synced_at and now() - conn.last_synced_at < SYNC_EVERY:
            continue
        n += sync_connection(db, conn)
        db.commit()
    return n


# ---- Rules --------------------------------------------------------------------------------------

@dataclass
class Decision:
    record: bool
    reason: str          # plain words for the calendar
    remind: bool = False


def internal_domains(db: Session) -> set[str]:
    doms = {d.strip().lower() for d in runtime_settings.get_csv(db, "email_summary_internal_domains") if d.strip()}
    doms |= {c.email.split("@")[-1].lower() for c in db.scalars(select(CalendarConnection)) if "@" in c.email}
    return doms


def outside_people(m: CalendarMeeting, domains: set[str]) -> list[dict]:
    return [p for p in m.attendees or [] if p.get("email") and p["email"].split("@")[-1] not in domains]


def attending(db: Session, m: CalendarMeeting) -> list[CalendarAttendance]:
    return db.scalars(select(CalendarAttendance).where(CalendarAttendance.meeting_id == m.id)).all()


def pref(user: User | None) -> str:
    return ((user.preferences or {}).get(PREF_KEY) if user else None) or "auto"


def should_record(db: Session, m: CalendarMeeting, domains: set[str] | None = None) -> Decision:
    if m.status == "cancelled":
        return Decision(False, "Cancelled")
    if not m.join_url:
        return Decision(False, "No meeting link")
    if m.platform not in SUPPORTED:
        return Decision(False, "No Meet, Teams or Zoom link")
    if m.platform == "zoom" and not zoom.available():
        return Decision(False, "Zoom isn't set up on the notetaker yet")
    if m.is_all_day:
        return Decision(False, "All-day event")
    atts = attending(db, m)
    going = [a for a in atts if a.response != "declined"]
    if not going:
        return Decision(False, "Everyone at BMI declined")
    if m.platform == "zoom" and not zoom_person(db, m, going):
        return Decision(False, "Nobody from BMI in it has connected Zoom - connect it under Your calendars")
    if m.record_override == "skip":
        return Decision(False, "Skipped for this meeting")
    if m.record_override == "record":
        return Decision(True, "Will be recorded (chosen for this meeting)")
    if all(a.is_private for a in going) and not runtime_settings.get_bool(db, "calendar_include_private"):
        return Decision(False, "Marked private")
    if not outside_people(m, domains if domains is not None else internal_domains(db)) and not runtime_settings.get_bool(db, "calendar_include_internal"):
        return Decision(False, "Only BMI people (internal meetings are off)")
    return _by_preference(db, m, going)


def _by_preference(db: Session, m: CalendarMeeting, going: list[CalendarAttendance]) -> Decision:
    """Whose "Record my meetings" choice counts. One person's "Join automatically" mustn't record everyone:
    - the BMI organiser decides for their own meeting (it's their call, and their review queue gets the notes);
    - otherwise (a client's invite, or only one of us on it - then it's their calendar) the BMI people going decide
      together: recorded only if someone chose "Join automatically" and nobody chose "Off". If they disagree,
      it isn't recorded; anyone who chose "Just remind me" (or "Join automatically") gets a reminder with a button."""
    users = {a.user_id: db.get(User, a.user_id) for a in going}
    org_email = (m.organizer_email or "").lower()
    organiser = next((a for a in going if a.response == "organizer"), None) or next(
        (a for a in going if org_email and users[a.user_id] and (users[a.user_id].email or "").lower() == org_email), None)
    if organiser:
        p = pref(users[organiser.user_id])
        if p == "auto":
            return Decision(True, "Will be recorded")
        if p == "remind":
            return Decision(False, "Reminder only", remind=True)
        return Decision(False, "Automatic recording is off for the organiser")
    prefs = {pref(users[a.user_id]) for a in going}
    if "auto" in prefs and "off" not in prefs:
        return Decision(True, "Will be recorded")
    if "auto" in prefs:
        return Decision(False, "Not everyone at BMI in it wants it recorded - reminder only", remind=True)
    if "remind" in prefs:
        return Decision(False, "Reminder only", remind=True)
    return Decision(False, "Automatic recording is off for everyone in it")


def zoom_person(db: Session, m: CalendarMeeting, going: list[CalendarAttendance] | None = None):
    """Whose Zoom the notetaker joins a Zoom call with: someone from BMI going who has connected Zoom - the
    organiser first. Zoom only lets it in once that person is in the call. None if nobody has."""
    going = going if going is not None else [a for a in attending(db, m) if a.response != "declined"]
    org_email = (m.organizer_email or "").lower()

    def first(a: CalendarAttendance) -> int:
        u = db.get(User, a.user_id)
        return 0 if a.response == "organizer" or (u and org_email and (u.email or "").lower() == org_email) else 1

    for a in sorted(going, key=first):
        conn = zoom.connection(db, a.user_id)
        if conn and conn.status == "connected":
            return conn
    return None


def owner(db: Session, m: CalendarMeeting) -> uuid.UUID | None:
    """Whose review queue the notes go to: the BMI organiser, else the first person going."""
    atts = attending(db, m)
    for a in atts:
        if a.response == "organizer":
            return a.user_id
    going = [a for a in atts if a.response != "declined"]
    return (going or atts or [None])[0].user_id if (going or atts) else None


def match_crm(db: Session, m: CalendarMeeting, domains: set[str]) -> None:
    if m.contact_id:
        return
    for p in outside_people(m, domains):
        row = db.scalar(select(Email).where(Email.address.ilike(p["email"])).limit(1))
        if row and row.contact_id:
            c = db.get(Contact, row.contact_id)
            m.contact_id = row.contact_id
            m.company_id = getattr(c, "company_id", None) if c else None
            return


# ---- Booking the bot ----------------------------------------------------------------------------

def _notify(db: Session, m: CalendarMeeting, title: str, body: str) -> None:
    from app.services.notify import create_notification
    for a in attending(db, m):
        if a.response != "declined":
            create_notification(db, a.user_id, "call_notes", title, body, link="/calls/meetings", email=False)


def plan(db: Session, at: datetime | None = None) -> dict:
    """Books bots for meetings starting soon and calls off ones that no longer qualify."""
    from app.services import notetaker
    at = at or now()
    domains = internal_domains(db)
    out = {"booked": 0, "called_off": 0, "reminded": 0}
    rows = db.scalars(select(CalendarMeeting).where(CalendarMeeting.start_at <= at + BOOK_AHEAD,
                                                    CalendarMeeting.start_at >= at - LATE_JOIN,
                                                    CalendarMeeting.end_at > at)).all()
    for m in rows:
        d = should_record(db, m, domains)
        call = db.get(CallRecording, m.call_id) if m.call_id else None
        live = call and call.status not in ("completed", "failed", "not_admitted", "cancelled")
        # One bot per meeting. If someone stopped it, it finished, or it wasn't let in, it isn't sent again
        # (skipping a meeting, or the meeting moving, clears call_id - so those can book again).
        if d.record and not call:
            if not notetaker.configured():
                m.last_error = "The notetaker isn't connected yet."
                continue
            join_at = max(m.start_at - timedelta(minutes=runtime_settings.get_int(db, "calendar_join_minutes_before")), at)
            if not m.notified_at:
                _notify(db, m, f"BMI Notetaker will join “{m.title or 'your meeting'}”",
                        f"It joins at {join_at:%H:%M} UTC and the notes come to Call notes afterwards. Open Meetings to skip it.")
                m.notified_at = at
            if join_at - at > SEND_WINDOW:
                continue   # not yet: it's sent on the job run just before its join time
            match_crm(db, m, domains)
            call = CallRecording(id=uuid.uuid4(), user_id=owner(db, m), contact_id=m.contact_id, company_id=m.company_id,
                                 calendar_meeting_id=m.id, meeting_url=m.join_url, title=m.title, status="scheduled", status_label="Scheduled")
            db.add(call)
            db.flush()
            try:
                zc = zoom_person(db, m) if m.platform == "zoom" else None
                res = notetaker.send_bot(meeting_url=m.join_url, external_id=f"cal:{m.id}", title=m.title,
                                         end_at=max(m.end_at, join_at + timedelta(minutes=15)),
                                         metadata={"bmi_call_id": str(call.id), "bmi_calendar_meeting_id": str(m.id)},
                                         zoom_user_id=zc.zoom_user_id if zc else None)
            except notetaker.NotetakerError as e:
                db.delete(call)
                # Tried again on every sync (every few minutes) until the meeting ends.
                m.last_error = f"{str(e).replace(' Please try again in a minute.', '')} BMI Brain tries again every few minutes until the meeting ends."
                continue
            call.notetaker_id, call.platform = res.get("id"), res.get("platform") or m.platform
            call.status, call.status_label = res.get("status", "scheduled"), res.get("status_label") or "Scheduled"
            m.call_id, m.last_error = call.id, None
            out["booked"] += 1
        elif not d.record and live and call.status == "scheduled":
            try:
                if call.notetaker_id:
                    notetaker.stop_bot(call.notetaker_id)
            except notetaker.NotetakerError as e:
                m.last_error = str(e)
                continue
            call.status, call.status_label, call.status_detail = "cancelled", "Cancelled", d.reason
            m.call_id = None
            out["called_off"] += 1
        elif d.remind and not m.notified_at and m.start_at - at <= timedelta(minutes=10):
            _notify(db, m, f"“{m.title or 'Your meeting'}” starts soon",
                    "Want notes? Open Meetings and press Record - the notetaker will join.")
            m.notified_at = at
            out["reminded"] += 1
    # meetings that were cancelled or moved after their bot was booked
    for m in db.scalars(select(CalendarMeeting).where(CalendarMeeting.status == "cancelled", CalendarMeeting.call_id.is_not(None))):
        call = db.get(CallRecording, m.call_id)
        if call and call.status == "scheduled":
            try:
                if call.notetaker_id:
                    notetaker.stop_bot(call.notetaker_id)
                call.status, call.status_label, call.status_detail = "cancelled", "Cancelled", "The meeting was cancelled or moved."
                out["called_off"] += 1
            except notetaker.NotetakerError:
                continue
        m.call_id = None
    db.commit()
    return out


# ---- What happened (the line on each meeting) ---------------------------------------------------

def latest_call(db: Session, m: CalendarMeeting) -> CallRecording | None:
    call = db.get(CallRecording, m.call_id) if m.call_id else None
    return call or db.scalar(select(CallRecording).where(CallRecording.calendar_meeting_id == m.id)
                             .order_by(CallRecording.created_at.desc()).limit(1))


def outcome(m: CalendarMeeting, call: CallRecording | None, d: Decision, at: datetime | None = None) -> dict:
    """One plain sentence for the meeting's line: what actually happened once it's over, what will happen
    before it starts. tone: ok | warn | bad | muted | live."""
    at = at or now()
    ended = bool(m.end_at and m.end_at <= at)
    started = m.start_at <= at
    def low(t: str) -> str:   # "The notetaker..." reads as "...- the notetaker..." after a dash
        return t[0].lower() + t[1:] if len(t) > 1 and not t[1].isupper() else t
    err = low((m.last_error or "").strip())
    detail = low(((call.status_detail if call else None) or "").strip())

    def say(tone: str, text: str) -> dict:
        return {"tone": tone, "text": text}

    if call and call.status != "cancelled":
        s = call.status
        if s == "completed":
            return say("ok", "Recorded - the notes are in Call notes")
        if s == "not_admitted":
            return say("bad", f"Not recorded - the notetaker wasn't let into the call{': ' + detail if detail else '. Someone in the meeting has to admit it from the waiting room.'}")
        if s == "failed":
            return say("bad", f"Not recorded - {detail or 'the notetaker had a problem in the call'}")
        if s == "processing":
            return say("live", "Recorded - writing up the notes now")
        if s == "scheduled":
            if ended:
                return say("bad", "Not recorded - the notetaker was sent but never joined, and it didn't say why. Ask whoever runs the notetaker to look.")
            if started:
                return say("warn", "The notetaker has been sent and should be joining now")
            return say("ok", "Will be recorded - the notetaker is on its way")
        return say("live", call.status_label or "The notetaker is in the call")

    if call and call.status == "cancelled" and not d.record:
        return say("muted", f"{'Not recorded' if ended else 'Won’t be recorded'} - {detail or d.reason}")

    if not d.record:
        if d.reason == "Cancelled":
            return say("muted", "Cancelled")
        return say("muted", f"{'Not recorded' if ended else 'Won’t be recorded'} - {low(d.reason)}")

    # The rules say record it, but no bot is (or was) booked.
    if ended:
        if err:
            return say("bad", f"Not recorded - {err}")
        if m.created_at and m.created_at > m.start_at + LATE_JOIN:
            return say("muted", "Not recorded - it reached BMI Brain after it had started, too late for the notetaker to join")
        return say("bad", "Not recorded - the notetaker was never sent. The calendar job may not have been running then - an administrator can see why in Notetaker check.")
    if err:
        return say("bad" if started else "warn", f"{'Not recording yet' if started else 'Will try to record'} - {err}")
    if started:
        return say("warn", "Should be recording - sending the notetaker now")
    return say("ok", "Will be recorded - the notetaker is sent just before it starts")


# ---- Starting over ------------------------------------------------------------------------------

def start_over(db: Session) -> dict:
    """Clears the shared calendar's history - every meeting and each person's copy - and calls off bots that
    were booked but haven't joined. Calendar connections stay; they're read again from scratch straight after.
    Calls that were actually recorded (they have notes) are kept, just no longer tied to a meeting."""
    from app.services import notetaker
    out = {"meetings": 0, "bots_called_off": 0, "calls_removed": 0}
    calls = db.scalars(select(CallRecording).where(CallRecording.calendar_meeting_id.is_not(None))).all()
    for c in calls:
        if c.status == "scheduled":
            try:
                if c.notetaker_id and notetaker.configured():
                    notetaker.stop_bot(c.notetaker_id)
                    out["bots_called_off"] += 1
            except notetaker.NotetakerError:
                log.warning("couldn't call off notetaker %s while starting over", c.notetaker_id)
        if c.status in ("scheduled", "cancelled", "failed", "not_admitted"):
            db.delete(c)
            out["calls_removed"] += 1
        else:
            c.calendar_meeting_id = None
    db.flush()
    out["meetings"] = db.query(CalendarMeeting).count()
    db.query(CalendarAttendance).delete(synchronize_session=False)
    db.query(CalendarMeeting).delete(synchronize_session=False)
    for conn in db.scalars(select(CalendarConnection)):
        conn.last_synced_at = None
    db.commit()
    return out


def run(db: Session) -> dict:
    """The scheduled job: read calendars that are due, then book or call off bots."""
    sync_all(db)
    return plan(db)
