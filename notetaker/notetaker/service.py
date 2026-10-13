"""What the service does, independent of HTTP: schedule a bot, react to its updates, write up the notes."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from notetaker import outbox, states
from notetaker.bots.base import BotRequest, BotUpdate
from notetaker.config import settings
from notetaker.models import Client, Meeting, MeetingEvent, ProcessedHook, now
from notetaker.providers import get_ai, get_bot

log = logging.getLogger(__name__)

PLATFORMS = [
    ("google_meet", re.compile(r"^https://meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}", re.I)),
    ("teams", re.compile(r"^https://(teams\.microsoft\.com|teams\.live\.com)/", re.I)),
    ("zoom", re.compile(r"^https://([\w-]+\.)?zoom\.us/", re.I)),
]


class InputError(ValueError):
    """A plain-language problem with what the caller sent."""


def detect_platform(url: str) -> str:
    for name, rx in PLATFORMS:
        if rx.match(url.strip()):
            return name
    raise InputError("That doesn't look like a Google Meet, Teams or Zoom meeting link.")


def meeting_view(m: Meeting) -> dict:
    return {
        "id": m.id, "external_id": m.external_id, "meeting_url": m.meeting_url, "platform": m.platform, "title": m.title,
        "join_at": m.join_at, "bot_name": m.bot_name, "metadata": m.meta or {}, "status": m.status,
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


def schedule(db: Session, client: Client, *, meeting_url: str, join_at: datetime | None = None, title: str | None = None,
             external_id: str | None = None, bot_name: str | None = None, metadata: dict | None = None) -> tuple[Meeting, bool]:
    """Send a bot. Returns (meeting, created). The same client + external_id twice gives back the first meeting."""
    if external_id:
        existing = db.scalar(select(Meeting).where(Meeting.client_id == client.id, Meeting.external_id == external_id))
        if existing and existing.status != states.CANCELLED:
            return existing, False
        if existing:   # re-scheduling a cancelled one: start it again
            db.delete(existing)
            db.flush()
    platform = detect_platform(meeting_url)
    if platform == "zoom":
        raise InputError("Zoom calls aren't supported yet - Zoom has to approve our app first.")
    starts_now = join_at is None or join_at <= now() + timedelta(minutes=1)
    if starts_now and active_bots(db) >= settings.max_concurrent_bots:
        raise InputError(f"The notetaker is already in {settings.max_concurrent_bots} calls. Try again when one finishes.")
    m = Meeting(client_id=client.id, external_id=external_id, meeting_url=meeting_url.strip(), platform=platform, title=title,
                join_at=join_at, bot_name=bot_name or client.bot_name or settings.default_bot_name, meta=metadata or {},
                bot_provider=get_bot().name, status=states.SCHEDULED)
    m.client = client
    db.add(m)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise InputError("That meeting is already scheduled.")
    m.bot_id = get_bot().create(BotRequest(meeting_id=m.id, meeting_url=m.meeting_url, bot_name=m.bot_name, join_at=join_at,
                                           chat_message=client.chat_message, dedupe_key=f"{client.id}:{external_id}" if external_id else None))
    db.add(MeetingEvent(meeting_id=m.id, status=states.SCHEDULED, detail=None))
    outbox.enqueue(db, client, "meeting.status_changed", _event_payload(m, full=False), meeting_id=m.id)
    return m, True


def cancel(db: Session, m: Meeting) -> None:
    if m.status in states.FINAL:
        return
    if m.bot_id:
        try:
            get_bot().cancel(m.bot_id)
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
    result = get_bot().fetch_result(m.bot_id)
    m.transcript = [u.__dict__ for u in result.transcript]
    m.participants = result.participants
    if not m.transcript:
        m.summary = None
        set_status(db, m, states.COMPLETED, "Nobody spoke, so there are no notes.")
        return
    notes = get_ai().summarise(transcript_text(m), m.participants, m.client.summary_instructions)
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
