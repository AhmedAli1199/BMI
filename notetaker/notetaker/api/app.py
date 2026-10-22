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
              description="Send a notetaker into a Google Meet, Teams or Zoom call and get back the transcript and notes by webhook.")


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
    zoom_user_id: str | None = Field(None, description="Zoom only: whose connected Zoom the notetaker joins on behalf of (from POST /v1/zoom/connections). They must be in the call.")


@app.post("/v1/meetings", status_code=201)
def create_meeting(body: MeetingIn, client: Client = Depends(current_client), db: Session = Depends(get_db)):
    join_at = body.join_at
    if (join_at and join_at.tzinfo is None) or (body.end_at and body.end_at.tzinfo is None):
        raise HTTPException(422, "Give times with a time zone, e.g. 2026-10-14T09:00:00Z.")
    try:
        m, created = service.schedule(db, client, meeting_url=str(body.meeting_url), join_at=join_at, title=body.title,
                                      external_id=body.external_id, bot_name=body.bot_name, metadata=body.metadata,
                                      ends_at=body.end_at, zoom_user_id=body.zoom_user_id)
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
    try:
        service.stop(db, m)
    except Exception:
        raise HTTPException(502, "The bot couldn't be asked to leave just now. Please try again in a minute.")
    return service.meeting_view(m)


# ---- Zoom ("Connect Zoom") -------------------------------------------------------------------------

@app.get("/v1/zoom")
def zoom_info(client: Client = Depends(current_client)):
    """Is Zoom set up for this app, and its Zoom app's client id (public - it goes in the Zoom sign-in link)."""
    ready = service.zoom_ready(client)
    return {"available": ready, "client_id": client.zoom_client_id if ready else None}


class ZoomConnectIn(BaseModel):
    authorization_code: str
    redirect_uri: str
    external_user: str | None = Field(None, description="Your own id for the person, kept with the connection.")


@app.post("/v1/zoom/connections", status_code=201)
def zoom_connect(body: ZoomConnectIn, client: Client = Depends(current_client), db: Session = Depends(get_db)):
    """Finish "Connect Zoom": hand over the code Zoom sent back to your redirect address."""
    c = service.connect_zoom(db, client, body.authorization_code, body.redirect_uri, body.external_user)
    return _json(service.zoom_view(c))


@app.get("/v1/zoom/connections/{zoom_user_id}")
def zoom_connection(zoom_user_id: str, client: Client = Depends(current_client), db: Session = Depends(get_db)):
    c = service.zoom_connection(db, client, zoom_user_id)
    if not c:
        raise HTTPException(404, "That Zoom account isn't connected.")
    return _json(service.zoom_view(c))


@app.delete("/v1/zoom/connections/{zoom_user_id}", status_code=204)
def zoom_disconnect(zoom_user_id: str, client: Client = Depends(current_client), db: Session = Depends(get_db)):
    service.disconnect_zoom(db, client, zoom_user_id)


# ---- Zoom's side ----------------------------------------------------------------------------------

@app.post("/hooks/zoom-tokens")
async def zoom_tokens(request: Request, db: Session = Depends(get_db)):
    """The meeting bot, joining a Zoom call, asks for the "on behalf of" token (signed with its project's secret)."""
    import json as _json
    from notetaker.bots.attendee import sign
    from notetaker import engine
    body = await request.body()
    try:
        payload = _json.loads(body)
    except ValueError:
        raise HTTPException(400, "Not JSON.")
    given = request.headers.get("x-webhook-signature", "")
    secrets = [x for x in [engine.webhook_secret(), *service.bot_webhook_secrets(db)] if x]
    if secrets and not any(same(given, sign(payload, sec)) for sec in secrets):
        raise HTTPException(401, "Not allowed.")
    return service.zoom_tokens_for_bot(db, payload)


@app.post("/hooks/zoom/{app_id}")
async def zoom_events(app_id: str, request: Request, db: Session = Depends(get_db)):
    """Zoom's events for one app's Zoom app (Features > Access > Event Subscription), checked with x-zm-signature
    and the app's Secret Token. app_deauthorized: the person removed the app in Zoom - their sign-in is deleted."""
    import json as _json
    from notetaker import zoomapi
    from notetaker.security import decrypt
    c = db.get(Client, app_id)
    if not c or not c.zoom_webhook_secret_enc:
        raise HTTPException(404, "Not found.")
    secret = decrypt(c.zoom_webhook_secret_enc)
    body = await request.body()
    if not zoomapi.signature_ok(secret, body, request.headers.get("x-zm-request-timestamp", ""), request.headers.get("x-zm-signature", "")):
        raise HTTPException(401, "Invalid signature.")
    event = _json.loads(body)
    kind, p = event.get("event"), event.get("payload") or {}
    if kind == "endpoint.url_validation":
        return zoomapi.url_validation(secret, p.get("plainToken", ""))
    if kind == "app_deauthorized":
        service.zoom_deauthorized(db, c, p.get("user_id") or "")
    return {"ok": True}


# ---- Meeting bot webhooks ------------------------------------------------------------------------

@app.post("/hooks/attendee")
async def attendee_hook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    try:
        update = get_bot().parse_webhook(body, {k.lower(): v for k, v in request.headers.items()}, service.bot_webhook_secrets(db))
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


# ---- attendee-sync: each app's own bot project (deploy/attendee_sync.py) -----------------------------

def _internal(x_internal_token: str) -> None:
    if not same(x_internal_token, settings.internal_token):
        raise HTTPException(401, "Not allowed.")


@app.get("/internal/bot-projects")
def bot_projects(x_internal_token: str = Header(default=""), db: Session = Depends(get_db)):
    _internal(x_internal_token)
    from notetaker.models import ServiceState, now as _now
    hb = db.get(ServiceState, "bot_sync_heartbeat") or ServiceState(key="bot_sync_heartbeat")
    hb.value = _now().isoformat()
    db.merge(hb)
    return {"apps": service.bot_projects_wanted(db)}


@app.post("/internal/bot-projects/{app_id}")
def bot_project_done(app_id: str, body: dict, x_internal_token: str = Header(default=""), db: Session = Depends(get_db)):
    _internal(x_internal_token)
    c = db.get(Client, app_id)
    if c:
        service.bot_project_applied(db, c, body)
    return {"ok": True}


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
