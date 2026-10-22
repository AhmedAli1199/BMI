"""What the service does, independent of HTTP: schedule a bot, react to its updates, write up the notes."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from notetaker import outbox, states
from notetaker.bots.base import BotRequest, BotUpdate, ZoomConnectError
from notetaker.config import settings
from notetaker.models import Client, Meeting, MeetingEvent, ProcessedHook, ZoomConnection, now
from notetaker.providers import get_bot

log = logging.getLogger(__name__)

PLATFORMS = [
    ("google_meet", re.compile(r"^https://meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}", re.I)),
    ("teams", re.compile(r"^https://(teams\.microsoft\.com|teams\.live\.com)/", re.I)),
    ("zoom", re.compile(r"^https://([\w-]+\.)?zoom\.us/", re.I)),
]


class InputError(ValueError):
    """A plain-language problem with what the caller sent."""


# ---- The app's own bot project (Zoom keys of its own) -------------------------------------------------

def bot_key(client: Client) -> str | None:
    """The app's own bot project key, once attendee-sync has made it (only apps with Zoom keys have one)."""
    from notetaker.security import decrypt
    return decrypt(client.bot_key_enc) if client.bot_project_id and client.bot_key_enc else None


def meeting_key(m: Meeting) -> str | None:
    """The key for the project the meeting's bot was made in."""
    project = (m.meta or {}).get("_bot_project")
    return bot_key(m.client) if project and project == m.client.bot_project_id else None


def zoom_ready(client: Client) -> bool:
    return client.zoom_status == "ready" and bool(bot_key(client))


def detect_platform(url: str) -> str:
    for name, rx in PLATFORMS:
        if rx.match(url.strip()):
            return name
    raise InputError("That doesn't look like a Google Meet, Teams or Zoom meeting link.")


def meeting_view(m: Meeting) -> dict:
    return {
        "id": m.id, "external_id": m.external_id, "meeting_url": m.meeting_url, "platform": m.platform, "title": m.title,
        "join_at": m.join_at, "ends_at": m.ends_at, "bot_name": m.bot_name, "metadata": m.meta or {}, "status": m.status,
        "status_label": states.LABELS.get(m.status, m.status), "status_detail": m.status_detail,
        "started_at": m.started_at, "ended_at": m.ended_at, "participants": m.participants or [],
        "transcript": m.transcript or [], "notes": m.summary, "created_at": m.created_at, "updated_at": m.updated_at,
    }


def _event_payload(m: Meeting, full: bool) -> dict:
    v = meeting_view(m)
    if not full:
        v.pop("transcript"), v.pop("notes")
    return v


def set_status(db: Session, m: Meeting, new: str, detail: str | None = None, force: bool = False) -> bool:
    if not force and not states.can_move(m.status, new):
        return False
    m.status, m.status_detail = new, detail
    if new == states.RECORDING and not m.started_at:
        m.started_at = now()
    if new in (states.PROCESSING, *states.FINAL) and m.started_at and not m.ended_at:
        m.ended_at = now()
    db.add(MeetingEvent(meeting_id=m.id, status=new, detail=detail))
    event = {states.COMPLETED: "meeting.completed", states.FAILED: "meeting.failed",
             states.NOT_ADMITTED: "meeting.failed"}.get(new, "meeting.status_changed")
    outbox.enqueue(db, m.client, event, _event_payload(m, full=new == states.COMPLETED), meeting_id=m.id)
    return True


def active_bots(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Meeting).where(Meeting.status.in_(states.ACTIVE))) or 0


# ---- Capacity --------------------------------------------------------------------------------------
# Every booking holds a slot from its start to its expected end (or DEFAULT_CALL_MINUTES). A new booking is
# refused up front if, at its busiest moment, it would go over the overall limit (one call per bot worker)
# or the app's own limit - so an app hears "busy at 2pm" when it books, not after the meeting started.

HOLDING = (states.SCHEDULED, *states.ACTIVE)


def _aware(dt: datetime | None) -> datetime | None:
    from datetime import timezone as _tz
    return dt.replace(tzinfo=_tz.utc) if dt and dt.tzinfo is None else dt


def slot(m: Meeting) -> tuple[datetime, datetime]:
    start = _aware(m.join_at) or _aware(m.created_at) or now()
    end = _aware(m.ends_at) or start + timedelta(minutes=settings.default_call_minutes)
    if m.status in states.ACTIVE:          # a call that's running long keeps its bot until it actually ends
        end = max(end, now() + timedelta(minutes=5))
    return start, end


def peak(db: Session, start: datetime, end: datetime, client_id: str | None = None, exclude: str | None = None) -> int:
    """The most bookings running at the same moment within [start, end)."""
    q = select(Meeting).where(Meeting.status.in_(HOLDING))
    if client_id:
        q = q.where(Meeting.client_id == client_id)
    edges = []
    for m in db.scalars(q):
        if m.id == exclude:
            continue
        s, e = slot(m)
        s, e = max(s, start), min(e, end)
        if s < e:
            edges += [(s, 1), (e, -1)]
    best = cur = 0
    for _, d in sorted(edges, key=lambda x: (x[0], x[1])):
        cur += d
        best = max(best, cur)
    return best


def capacity(db: Session, client: Client, start: datetime, end: datetime) -> dict:
    overall = settings.max_concurrent_bots
    used = peak(db, start, end)
    free = max(0, overall - used)
    if client.max_concurrent:
        free = min(free, max(0, client.max_concurrent - peak(db, start, end, client.id)))
    return {"start": start, "end": end, "free": free, "overall_limit": overall, "app_limit": client.max_concurrent}


def _check_capacity(db: Session, client: Client, start: datetime, end: datetime) -> None:
    when = "right now" if start <= now() + timedelta(minutes=1) else f"at {start:%H:%M} UTC on {start:%d %b}"
    if peak(db, start, end) >= settings.max_concurrent_bots:
        raise InputError(f"The notetaker is already booked for {settings.max_concurrent_bots} calls {when} - the most it can join at once. "
                         "Try another time, or ask the notetaker admin to add capacity.")
    if client.max_concurrent and peak(db, start, end, client.id) >= client.max_concurrent:
        raise InputError(f"This app already has {client.max_concurrent} call{'s' if client.max_concurrent > 1 else ''} booked {when}, "
                         "which is its limit. The notetaker admin can raise it in the console.")


def schedule(db: Session, client: Client, *, meeting_url: str, join_at: datetime | None = None, title: str | None = None,
             external_id: str | None = None, bot_name: str | None = None, metadata: dict | None = None,
             ends_at: datetime | None = None, zoom_user_id: str | None = None) -> tuple[Meeting, bool]:
    """Send a bot. Returns (meeting, created). The same client + external_id twice gives back the first meeting."""
    if external_id:
        existing = db.scalar(select(Meeting).where(Meeting.client_id == client.id, Meeting.external_id == external_id))
        if existing and existing.status != states.CANCELLED:
            return existing, False
        if existing:   # re-scheduling a cancelled one: keep its history, free the id for the new booking
            existing.external_id = f"{external_id}~cancelled~{existing.id[:8]}"[:200]
            db.flush()
    platform = detect_platform(meeting_url)
    if platform == "zoom":
        zoom_user_id = _zoom_user(db, client, zoom_user_id)
    else:
        zoom_user_id = None
    start = join_at or now()
    end = ends_at or start + timedelta(minutes=settings.default_call_minutes)
    if end <= start:
        raise InputError("The end time has to be after the start.")
    _check_capacity(db, client, start, end)
    m = Meeting(client_id=client.id, external_id=external_id, meeting_url=meeting_url.strip(), platform=platform, title=title,
                join_at=join_at, ends_at=ends_at, bot_name=bot_name or client.bot_name or settings.default_bot_name, meta=metadata or {},
                bot_provider=get_bot().name, status=states.SCHEDULED)
    key = bot_key(client)   # an app with its own project sends all its bots from it
    if zoom_user_id:
        m.meta = {**m.meta, "_zoom_user_id": zoom_user_id}
    if key:
        m.meta = {**m.meta, "_bot_project": client.bot_project_id}
    m.client = client
    db.add(m)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise InputError("That meeting is already scheduled.")
    m.bot_id = get_bot().create(BotRequest(meeting_id=m.id, meeting_url=m.meeting_url, bot_name=m.bot_name, join_at=join_at,
                                           chat_message=client.chat_message, dedupe_key=f"{client.id}:{m.id}",
                                           zoom_user_id=zoom_user_id, bot_key=key))
    db.add(MeetingEvent(meeting_id=m.id, status=states.SCHEDULED, detail=None))
    outbox.enqueue(db, client, "meeting.status_changed", _event_payload(m, full=False), meeting_id=m.id)
    return m, True


# ---- Zoom ------------------------------------------------------------------------------------------
# Zoom only lets a notetaker join "on behalf of" a signed-in person who is in the call (since March 2026, for
# notetakers). Each person connects their Zoom once from their app; a Zoom booking names whose Zoom to use.

ZOOM_OFF = "Zoom isn't set up for this app on the notetaker yet. Ask whoever runs the notetaker to add the app's Zoom keys (Apps, Edit)."


def _zoom_user(db: Session, client: Client, zoom_user_id: str | None) -> str:
    if not zoom_ready(client):
        raise InputError(ZOOM_OFF)
    if not zoom_user_id:
        raise InputError("Zoom calls need someone's connected Zoom - the notetaker joins on their behalf. Connect Zoom first.")
    c = db.scalar(select(ZoomConnection).where(ZoomConnection.client_id == client.id, ZoomConnection.zoom_user_id == zoom_user_id))
    if not c or c.state != "connected":
        raise InputError("That person's Zoom isn't connected any more. They need to press Connect Zoom again.")
    return zoom_user_id


def zoom_view(c: ZoomConnection) -> dict:
    return {"zoom_user_id": c.zoom_user_id, "state": c.state, "external_user": c.external_user,
            "created_at": c.created_at, "updated_at": c.updated_at}


def connect_zoom(db: Session, client: Client, authorization_code: str, redirect_uri: str, external_user: str | None) -> ZoomConnection:
    if not zoom_ready(client):
        raise InputError(ZOOM_OFF)
    try:
        got = get_bot().connect_zoom(authorization_code, redirect_uri, {"notetaker_client": client.id, "external_user": external_user or ""},
                                     key=bot_key(client))
    except ZoomConnectError as e:
        raise InputError(str(e))
    c = db.scalar(select(ZoomConnection).where(ZoomConnection.client_id == client.id, ZoomConnection.zoom_user_id == got["zoom_user_id"]))
    if c is None:
        # the same Zoom account can't belong to two apps - the meeting bot keeps one sign-in per Zoom account
        other = db.scalar(select(ZoomConnection).where(ZoomConnection.zoom_user_id == got["zoom_user_id"]))
        if other:
            raise InputError("That Zoom account is already connected to another app on this notetaker. Use a different Zoom account.")
        c = ZoomConnection(client_id=client.id, zoom_user_id=got["zoom_user_id"])
        db.add(c)
    c.bot_connection_id, c.external_user, c.state = got["id"], external_user, got.get("state") or "connected"
    db.flush()
    return c


def zoom_connection(db: Session, client: Client, zoom_user_id: str, refresh: bool = True) -> ZoomConnection | None:
    c = db.scalar(select(ZoomConnection).where(ZoomConnection.client_id == client.id, ZoomConnection.zoom_user_id == zoom_user_id))
    if c and refresh:
        try:
            state = get_bot().zoom_state(c.bot_connection_id, key=bot_key(client))
        except Exception:
            log.warning("Couldn't check Zoom connection %s", c.id, exc_info=True)
            state = None
        if state and state != c.state:
            c.state = state
    return c


def disconnect_zoom(db: Session, client: Client, zoom_user_id: str) -> bool:
    c = db.scalar(select(ZoomConnection).where(ZoomConnection.client_id == client.id, ZoomConnection.zoom_user_id == zoom_user_id))
    if not c:
        return False
    try:
        get_bot().disconnect_zoom(c.bot_connection_id, key=bot_key(client))
    except Exception:
        log.warning("Couldn't remove Zoom connection %s from the meeting bot", c.id, exc_info=True)
    db.delete(c)
    return True


def stop(db: Session, m: Meeting) -> None:
    """"Stop" from an app or the console. A bot that's already in the call leaves, and what it recorded so far
    is still written up as usual (the meeting goes on to processing and completed). A bot that hasn't joined
    yet is called off."""
    if m.status in states.ACTIVE and m.bot_id:
        try:
            get_bot().cancel(m.bot_id, key=meeting_key(m))   # for a bot in the call this asks it to leave
        except Exception:
            log.exception("Asking bot %s to leave failed", m.bot_id)
            raise
        m.meta = {**(m.meta or {}), "_stopped": True}
        db.add(MeetingEvent(meeting_id=m.id, status=m.status, detail="Asked to leave. The notes cover the call up to now."))
        return
    cancel(db, m)


def cancel(db: Session, m: Meeting) -> None:
    if m.status in states.FINAL:
        return
    if m.bot_id:
        try:
            get_bot().cancel(m.bot_id, key=meeting_key(m))
        except Exception:
            log.exception("Cancelling bot %s failed", m.bot_id)
    set_status(db, m, states.CANCELLED, "Cancelled.", force=True)


def handle_bot_update(db: Session, u: BotUpdate) -> Meeting | None:
    if u.dedupe_key:
        if db.get(ProcessedHook, u.dedupe_key):
            return None
        db.add(ProcessedHook(key=u.dedupe_key))
    m = db.scalar(select(Meeting).where(Meeting.bot_id == u.bot_id))
    if not m:
        return None
    if u.status:
        set_status(db, m, u.status, u.detail)
    if u.ready and m.status == states.PROCESSING:
        m.meta = {**(m.meta or {}), "_ready": True}   # the worker writes up the notes (it can take a minute)
    return m


def transcript_text(m: Meeting) -> str:
    def ts(ms: int) -> str:
        s = ms // 1000
        return f"{s // 60:02d}:{s % 60:02d}"
    return "\n".join(f"[{ts(u['start_ms'])}] {u['speaker']}: {u['text']}" for u in m.transcript or [])


def finalise(db: Session, m: Meeting) -> None:
    """Collect the transcript and write the notes. Retried by the worker if anything fails."""
    result = get_bot().fetch_result(m.bot_id, key=meeting_key(m))
    m.transcript = [u.__dict__ for u in result.transcript]
    m.participants = result.participants
    if not m.transcript:
        m.summary = None
        set_status(db, m, states.COMPLETED, "Nobody spoke, so there are no notes.")
        return
    from notetaker.providers import app_ai
    from notetaker.styles import instructions
    ai = app_ai(m.client)
    if ai is None:   # each app brings its own Gemini key - without one, the transcript still goes back
        m.summary = None
        set_status(db, m, states.COMPLETED, "Transcript only - add this app's Gemini key in the notetaker console to get written notes.")
        return
    notes = ai.summarise(transcript_text(m), m.participants, instructions(m.client.notes_style, m.client.summary_instructions))
    m.ai_input_tokens = (m.ai_input_tokens or 0) + ai.last_usage[0]
    m.ai_output_tokens = (m.ai_output_tokens or 0) + ai.last_usage[1]
    m.summary = notes.model_dump()
    if not m.title:
        m.title = notes.title
    meta = dict(m.meta or {})
    meta.pop("_ready", None)
    m.meta = meta
    set_status(db, m, states.COMPLETED)


def due_for_finalising(db: Session) -> list[Meeting]:
    rows = db.scalars(select(Meeting).where(Meeting.status == states.PROCESSING, Meeting.attempts < 5)).all()
    return [m for m in rows if (m.meta or {}).get("_ready")]


POLL_EVERY_SECONDS = 60


def reconcile(db: Session) -> int:
    """Check unfinished meetings with the bot provider directly, at most once a minute each, so a lost
    webhook can't leave a call stuck on "Recording". Returns how many were checked."""
    from datetime import timezone as _tz
    rows = db.scalars(select(Meeting).where(Meeting.status.in_([*states.ACTIVE, states.PROCESSING, states.SCHEDULED]))).all()
    checked = 0
    for m in rows:
        meta = dict(m.meta or {})
        if not m.bot_id or meta.get("_ready"):
            continue
        if m.status == states.SCHEDULED and m.join_at and m.join_at.replace(tzinfo=m.join_at.tzinfo or _tz.utc) > now():
            continue
        last = meta.get("_polled_at")
        if last and (now() - datetime.fromisoformat(last)).total_seconds() < POLL_EVERY_SECONDS:
            continue
        meta["_polled_at"] = now().isoformat()
        m.meta = meta
        try:
            u = get_bot().poll(m.bot_id, key=meeting_key(m))
        except Exception:
            log.warning("Couldn't check bot %s", m.bot_id)
            continue
        checked += 1
        if not u:
            continue
        # walk forward through the steps we missed, so the timeline stays readable
        if u.status and u.status != m.status:
            if u.status == states.PROCESSING and m.status in (states.SCHEDULED, states.JOINING, states.WAITING_ROOM):
                set_status(db, m, states.RECORDING)
            set_status(db, m, u.status, u.detail)
        if u.ready and m.status == states.PROCESSING:
            m.meta = {**(m.meta or {}), "_ready": True}
    return checked


# ---- attendee-sync (deploy/attendee_sync.py) ------------------------------------------------------------

def bot_projects_wanted(db: Session) -> list[dict]:
    """Apps that need their own bot project: those with Zoom keys, and those that already have one (so removed
    keys get taken off it)."""
    from notetaker.security import decrypt, hash_key
    out = []
    for c in db.scalars(select(Client).where((Client.zoom_client_id.isnot(None)) | (Client.bot_project_id.isnot(None)))):
        key = bot_key(c)
        out.append({"app_id": c.id, "name": c.name, "project_id": c.bot_project_id, "key_hash": hash_key(key) if key else None,
                    "zoom_client_id": c.zoom_client_id, "zoom_client_secret": decrypt(c.zoom_secret_enc) if c.zoom_secret_enc else None})
    return out


def bot_project_applied(db: Session, client: Client, data: dict) -> None:
    from notetaker.security import encrypt
    if data.get("project_id"):
        client.bot_project_id = data["project_id"]
    if data.get("api_key"):
        client.bot_key_enc = encrypt(data["api_key"])
    if data.get("webhook_secret"):
        client.bot_webhook_secret_enc = encrypt(data["webhook_secret"])
    zoom = data.get("zoom")
    if zoom == "ready":
        client.zoom_status, client.zoom_error = ("ready", None) if client.zoom_client_id else (None, None)
    elif zoom == "error":
        client.zoom_status, client.zoom_error = "error", data.get("error") or "Zoom couldn't be set up for this app."
    elif zoom == "off":
        client.zoom_status = client.zoom_error = None


def bot_webhook_secrets(db: Session) -> list[str]:
    from notetaker.security import decrypt
    return [decrypt(c.bot_webhook_secret_enc) for c in db.scalars(select(Client).where(Client.bot_webhook_secret_enc.isnot(None)))]
