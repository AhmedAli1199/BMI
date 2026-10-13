"""HTTP API.

Client apps:        Authorization: Bearer <api key>      /v1/...
Meeting bot:        POST /hooks/attendee                 (signed by Attendee)
Transcription:      POST /internal/transcribe            (Attendee sends each speaker's audio; X-Internal-Token)
Admin:              X-Admin-Token: <ADMIN_TOKEN>         /admin/...
Dashboard:          GET /                                (a small page for watching meetings and sending a bot)
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import Session

from notetaker import service, states
from notetaker.config import settings
from notetaker.db import SessionLocal, init_db
from notetaker.models import Client, Meeting
from notetaker.providers import get_bot
from notetaker.security import hash_key, same

log = logging.getLogger(__name__)
@asynccontextmanager
async def lifespan(_app):
    init_db()
    yield


app = FastAPI(title="Cybix Notetaker", version="0.1.0", lifespan=lifespan,
              description="Send a notetaker into a Google Meet or Teams call and get back the transcript and notes by webhook.")


def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def current_client(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> Client:
    key = authorization.removeprefix("Bearer ").strip()
    c = db.scalar(select(Client).where(Client.api_key_hash == hash_key(key))) if key else None
    if not c:
        raise HTTPException(401, "That API key isn't valid.")
    if c.is_active is False:
        raise HTTPException(403, "This app has been switched off in the notetaker console.")
    from notetaker.models import now as _now
    c.last_used_at = _now()
    return c


@app.exception_handler(service.InputError)
def _input_error(_: Request, e: service.InputError):
    return JSONResponse(status_code=422, content={"detail": str(e)})


# ---- Client API -----------------------------------------------------------------------------------

class MeetingIn(BaseModel):
    meeting_url: HttpUrl
    join_at: datetime | None = Field(None, description="When to join (ISO 8601). Leave out to join now.")
    end_at: datetime | None = Field(None, description="When the meeting should end - holds the bot's slot until then (default: an hour).")
    title: str | None = None
    external_id: str | None = Field(None, description="Your own id for this meeting (e.g. the calendar event). Sending it twice won't send two bots.")
    bot_name: str | None = None
    metadata: dict = Field(default_factory=dict, description="Anything you want back in the webhooks.")


@app.post("/v1/meetings", status_code=201)
def create_meeting(body: MeetingIn, client: Client = Depends(current_client), db: Session = Depends(get_db)):
    join_at = body.join_at
    if (join_at and join_at.tzinfo is None) or (body.end_at and body.end_at.tzinfo is None):
        raise HTTPException(422, "Give times with a time zone, e.g. 2026-10-14T09:00:00Z.")
    try:
        m, created = service.schedule(db, client, meeting_url=str(body.meeting_url), join_at=join_at, title=body.title,
                                      external_id=body.external_id, bot_name=body.bot_name, metadata=body.metadata,
                                      ends_at=body.end_at)
    except service.InputError:
        raise
    except Exception:
        log.exception("Scheduling a bot failed")
        raise HTTPException(502, "The notetaker couldn't be sent just now. Please try again in a minute.")
    return JSONResponse(status_code=201 if created else 200, content=_json(service.meeting_view(m)))


@app.get("/v1/capacity")
def get_capacity(start: datetime | None = None, end: datetime | None = None, client: Client = Depends(current_client),
                 db: Session = Depends(get_db)):
    """How many more calls this app could book for that time (default: now, for an hour)."""
    from datetime import timedelta
    from notetaker.models import now as _now
    start = start or _now()
    end = end or start + timedelta(minutes=settings.default_call_minutes)
    if start.tzinfo is None or end.tzinfo is None:
        raise HTTPException(422, "Give times with a time zone, e.g. 2026-10-14T09:00:00Z.")
    return _json(service.capacity(db, client, start, end))


@app.get("/v1/meetings")
def list_meetings(status: str | None = None, limit: int = 50, client: Client = Depends(current_client), db: Session = Depends(get_db)):
    q = select(Meeting).where(Meeting.client_id == client.id).order_by(Meeting.created_at.desc()).limit(min(limit, 200))
    if status:
        q = q.where(Meeting.status == status)
    rows = db.scalars(q).all()
    return [{k: v for k, v in service.meeting_view(m).items() if k != "transcript"} for m in rows]


def _own(db: Session, client: Client, meeting_id: str) -> Meeting:
    m = db.get(Meeting, meeting_id)
    if not m or m.client_id != client.id:
        raise HTTPException(404, "We couldn't find that meeting.")
    return m


@app.get("/v1/meetings/{meeting_id}")
def get_meeting(meeting_id: str, client: Client = Depends(current_client), db: Session = Depends(get_db)):
    m = _own(db, client, meeting_id)
    v = service.meeting_view(m)
    v["timeline"] = [{"status": e.status, "label": states.LABELS.get(e.status, e.status), "detail": e.detail, "at": e.created_at} for e in m.events]
    return v


@app.delete("/v1/meetings/{meeting_id}")
def cancel_meeting(meeting_id: str, client: Client = Depends(current_client), db: Session = Depends(get_db)):
    m = _own(db, client, meeting_id)
    service.cancel(db, m)
    return service.meeting_view(m)


# ---- Meeting bot webhooks ------------------------------------------------------------------------

@app.post("/hooks/attendee")
async def attendee_hook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    try:
        update = get_bot().parse_webhook(body, {k.lower(): v for k, v in request.headers.items()})
    except PermissionError:
        raise HTTPException(400, "Invalid signature.")
    if update:
        service.handle_bot_update(db, update)
    return {"ok": True}


@app.post("/hooks/fake")
async def fake_hook(request: Request, db: Session = Depends(get_db)):
    """Demo only: pretend the bot moved on (works when BOT_PROVIDER=fake)."""
    if settings.bot_provider != "fake":
        raise HTTPException(404, "Not found.")
    update = get_bot().parse_webhook(await request.body(), {})
    service.handle_bot_update(db, update)
    return {"ok": True}


# ---- Transcription for Attendee (TRANSCRIPTION_MODE=gemini) --------------------------------------

@app.post("/internal/transcribe")
async def transcribe(audio: UploadFile = File(...), meeting_id: str = Form(default=""), x_internal_token: str = Header(default=""),
                     db: Session = Depends(get_db)):
    if not same(x_internal_token, settings.internal_token):
        raise HTTPException(401, "Not allowed.")
    from notetaker.providers import app_ai
    m = db.get(Meeting, meeting_id) if meeting_id else None
    ai = app_ai(m.client) if m else None
    if ai is None:   # transcribed with the app's own key only - no key, no Gemini transcript
        return {"status": "error", "error_code": "no_gemini_key"}
    data = await audio.read()
    try:
        text = ai.transcribe(data, audio.content_type or "audio/mpeg")
        m.ai_input_tokens = (m.ai_input_tokens or 0) + ai.last_usage[0]
        m.ai_output_tokens = (m.ai_output_tokens or 0) + ai.last_usage[1]
    except Exception:
        log.exception("Transcription failed")
        return {"status": "error", "error_code": "transcription_failed"}
    return {"status": "done", "result": {"transcription": {"full_transcript": text, "utterances": []}}}


# ---- Health and dashboard ------------------------------------------------------------------------

@app.get("/health")
def health(db: Session = Depends(get_db)):
    return {"ok": True, "active_bots": service.active_bots(db), "max_bots": settings.max_concurrent_bots,
            "bot": settings.bot_provider, "transcription": settings.transcription_mode}


@app.get("/", response_class=HTMLResponse)
def console_page():
    return (Path(__file__).parent / "console.html").read_text()


@app.get("/guide", response_class=HTMLResponse)
def guide_page():
    return (Path(__file__).parent / "guide.html").read_text().replace("{{PUBLIC_URL}}", settings.public_url)


from notetaker.api.console import router as console_router  # noqa: E402

app.include_router(console_router)


def _json(v):
    from fastapi.encoders import jsonable_encoder
    return jsonable_encoder(v)
