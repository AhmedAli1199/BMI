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

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import Session

from notetaker import service, states
from notetaker.clients import create_client
from notetaker.config import settings
from notetaker.db import SessionLocal, init_db
from notetaker.models import Client, Meeting
from notetaker.providers import get_ai, get_bot
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
    return c


def require_admin(x_admin_token: str = Header(default="")) -> None:
    if not same(x_admin_token, settings.admin_token):
        raise HTTPException(401, "Admin access only.")


@app.exception_handler(service.InputError)
def _input_error(_: Request, e: service.InputError):
    return JSONResponse(status_code=422, content={"detail": str(e)})


# ---- Client API -----------------------------------------------------------------------------------

class MeetingIn(BaseModel):
    meeting_url: HttpUrl
    join_at: datetime | None = Field(None, description="When to join (ISO 8601). Leave out to join now.")
    title: str | None = None
    external_id: str | None = Field(None, description="Your own id for this meeting (e.g. the calendar event). Sending it twice won't send two bots.")
    bot_name: str | None = None
    metadata: dict = Field(default_factory=dict, description="Anything you want back in the webhooks.")


@app.post("/v1/meetings", status_code=201)
def create_meeting(body: MeetingIn, client: Client = Depends(current_client), db: Session = Depends(get_db)):
    join_at = body.join_at
    if join_at and join_at.tzinfo is None:
        raise HTTPException(422, "Give join_at with a time zone, e.g. 2026-10-14T09:00:00Z.")
    try:
        m, created = service.schedule(db, client, meeting_url=str(body.meeting_url), join_at=join_at, title=body.title,
                                      external_id=body.external_id, bot_name=body.bot_name, metadata=body.metadata)
    except service.InputError:
        raise
    except Exception:
        log.exception("Scheduling a bot failed")
        raise HTTPException(502, "The notetaker couldn't be sent just now. Please try again in a minute.")
    return JSONResponse(status_code=201 if created else 200, content=_json(service.meeting_view(m)))


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
async def transcribe(audio: UploadFile = File(...), x_internal_token: str = Header(default="")):
    if not same(x_internal_token, settings.internal_token):
        raise HTTPException(401, "Not allowed.")
    data = await audio.read()
    try:
        text = get_ai().transcribe(data, audio.content_type or "audio/mpeg")
    except Exception:
        log.exception("Transcription failed")
        return {"status": "error", "error_code": "transcription_failed"}
    return {"status": "done", "result": {"transcription": {"full_transcript": text, "utterances": []}}}


# ---- Admin ---------------------------------------------------------------------------------------

class ClientIn(BaseModel):
    name: str
    webhook_url: HttpUrl | None = None
    bot_name: str | None = None
    chat_message: str | None = None
    summary_instructions: str | None = None
    retention_days: int = 30


@app.post("/admin/clients", dependencies=[Depends(require_admin)], status_code=201)
def admin_create_client(body: ClientIn, db: Session = Depends(get_db)):
    c, key = create_client(db, body.name, str(body.webhook_url) if body.webhook_url else None, bot_name=body.bot_name,
                           chat_message=body.chat_message, summary_instructions=body.summary_instructions,
                           retention_days=body.retention_days)
    return {"id": c.id, "name": c.name, "api_key": key, "webhook_secret": c.webhook_secret,
            "note": "Save the API key now - it isn't shown again."}


@app.get("/admin/clients", dependencies=[Depends(require_admin)])
def admin_clients(db: Session = Depends(get_db)):
    return [{"id": c.id, "name": c.name, "webhook_url": c.webhook_url, "bot_name": c.bot_name, "created_at": c.created_at}
            for c in db.scalars(select(Client).order_by(Client.created_at))]


# ---- Health and dashboard ------------------------------------------------------------------------

@app.get("/health")
def health(db: Session = Depends(get_db)):
    return {"ok": True, "active_bots": service.active_bots(db), "max_bots": settings.max_concurrent_bots,
            "bot": settings.bot_provider, "transcription": settings.transcription_mode}


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return (Path(__file__).parent / "dashboard.html").read_text()


def _json(v):
    from fastapi.encoders import jsonable_encoder
    return jsonable_encoder(v)
