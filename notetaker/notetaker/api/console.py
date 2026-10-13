"""The admin console's API: sign in, the set-up checklist, apps (create, edit, keys), webhook
deliveries, and sending a test bot. Signed in with ADMIN_TOKEN as the password (a signed cookie), or
the X-Admin-Token header for scripts."""
from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, HttpUrl
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from notetaker import engine, outbox, service, states
from notetaker.clients import create_client, rotate_key, rotate_secret
from notetaker.config import settings
from notetaker.models import Client, Meeting, OutboxMessage, ServiceState, now
from notetaker.providers import get_bot
from notetaker.security import same
from notetaker.styles import STYLES

router = APIRouter()
COOKIE = "nt_console"
SESSION_HOURS = 12


def _get_db():
    from notetaker.api.app import get_db
    yield from get_db()


def _sign(exp: int) -> str:
    return hmac.new(("console:" + settings.admin_token).encode(), str(exp).encode(), hashlib.sha256).hexdigest()


def require_admin(x_admin_token: str = Header(default=""), nt_console: str | None = Cookie(default=None)) -> None:
    if settings.admin_token and same(x_admin_token, settings.admin_token):
        return
    if nt_console and settings.admin_token:
        exp, _, sig = nt_console.partition(".")
        if exp.isdigit() and int(exp) > time.time() and same(sig, _sign(int(exp))):
            return
    raise HTTPException(401, "Please sign in to the console.")


class LoginIn(BaseModel):
    password: str


@router.post("/console/login")
def login(body: LoginIn, response: Response):
    if not settings.admin_token:
        raise HTTPException(409, "Set ADMIN_TOKEN in the server settings first - it's the console password.")
    if not same(body.password.strip(), settings.admin_token):
        time.sleep(1)
        raise HTTPException(401, "That password isn't right.")
    exp = int(time.time()) + SESSION_HOURS * 3600
    response.set_cookie(COOKIE, f"{exp}.{_sign(exp)}", max_age=SESSION_HOURS * 3600, httponly=True, samesite="strict",
                        secure=settings.public_url.startswith("https"))
    return {"ok": True}


@router.post("/console/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE)
    return {"ok": True}


# ---- Set-up checklist -------------------------------------------------------------------------------

@router.get("/admin/overview", dependencies=[Depends(require_admin)])
def overview(db: Session = Depends(_get_db)):
    checks = []
    bot = get_bot()
    if settings.bot_provider == "attendee":
        ok, msg = bot.check()
        checks.append({"name": "Meeting bot", "ok": ok, "detail": msg})
        checks.append({"name": "Bot updates are signed", "ok": bool(engine.webhook_secret()),
                       "detail": "Ready" if engine.webhook_secret() else "Waiting for the set-up step to finish"})
    else:
        checks.append({"name": "Meeting bot", "ok": True, "detail": "Demo mode (pretend bot)"})
    ai_ok = settings.ai_provider != "gemini" or bool(settings.gemini_api_key)
    checks.append({"name": "Notes writer (Gemini)", "ok": ai_ok, "detail": "Ready" if ai_ok else "Add GEMINI_API_KEY to the server settings"})
    https = settings.public_url.startswith("https://")
    checks.append({"name": "Public address", "ok": https, "detail": settings.public_url if https else "PUBLIC_URL must start with https://"})
    hb = db.get(ServiceState, "worker_heartbeat")
    age = (now() - datetime.fromisoformat(hb.value)).total_seconds() if hb and hb.value else None
    checks.append({"name": "Background worker", "ok": age is not None and age < 120,
                   "detail": f"Running (checked in {int(age)}s ago)" if age is not None and age < 120 else "Not running - check the notetaker-worker container"})
    since = now() - timedelta(days=30)
    stats = {
        "apps": db.scalar(select(func.count()).select_from(Client)) or 0,
        "live_calls": service.active_bots(db), "max_calls": settings.max_concurrent_bots,
        "calls_30d": db.scalar(select(func.count()).select_from(Meeting).where(Meeting.created_at >= since)) or 0,
        "failed_webhooks": db.scalar(select(func.count()).select_from(OutboxMessage).where(OutboxMessage.status == "dead")) or 0,
    }
    return {"checks": checks, "ready": all(c["ok"] for c in checks), "stats": stats, "public_url": settings.public_url,
            "styles": [{"value": k, "label": v[0], "hint": v[1]} for k, v in STYLES.items()],
            "engine_login": engine.admin_login(), "engine_url": settings.attendee_public_url or None}


# ---- Apps -------------------------------------------------------------------------------------------

def _app_view(db: Session, c: Client) -> dict:
    since = now() - timedelta(days=30)
    return jsonable_encoder({
        "id": c.id, "name": c.name, "webhook_url": c.webhook_url, "bot_name": c.bot_name, "chat_message": c.chat_message,
        "notes_style": c.notes_style or "general", "summary_instructions": c.summary_instructions, "retention_days": c.retention_days,
        "is_active": c.is_active is not False, "key_hint": c.key_hint, "created_at": c.created_at, "last_used_at": c.last_used_at,
        "calls_30d": db.scalar(select(func.count()).select_from(Meeting).where(Meeting.client_id == c.id, Meeting.created_at >= since)) or 0,
        "failed_webhooks": db.scalar(select(func.count()).select_from(OutboxMessage).where(OutboxMessage.client_id == c.id, OutboxMessage.status == "dead")) or 0,
    })


def _one(db: Session, app_id: str) -> Client:
    c = db.get(Client, app_id)
    if not c:
        raise HTTPException(404, "We couldn't find that app.")
    return c


class AppIn(BaseModel):
    name: str
    webhook_url: HttpUrl | None = None
    bot_name: str | None = None
    chat_message: str | None = None
    notes_style: str = "general"
    summary_instructions: str | None = None
    retention_days: int = 30
    # the old /admin/clients field, kept so scripts written against it still work
    is_active: bool = True


def _clean(body: AppIn) -> dict:
    if body.notes_style not in STYLES:
        raise HTTPException(422, "Pick one of the notes styles.")
    if not body.name.strip():
        raise HTTPException(422, "Give the app a name.")
    return {"name": body.name.strip(), "webhook_url": str(body.webhook_url) if body.webhook_url else None,
            "bot_name": (body.bot_name or "").strip() or None, "chat_message": (body.chat_message or "").strip() or None,
            "notes_style": body.notes_style, "summary_instructions": (body.summary_instructions or "").strip() or None,
            "retention_days": max(1, min(body.retention_days, 365)), "is_active": body.is_active}


def _integration(c: Client, key: str | None, secret: str | None) -> dict:
    return {"api_key": key, "webhook_secret": secret, "env": "\n".join(x for x in [
        f"NOTETAKER_URL={settings.public_url}",
        f"NOTETAKER_API_KEY={key}" if key else None,
        f"NOTETAKER_WEBHOOK_SECRET={secret}" if secret else None] if x)}


@router.get("/admin/apps", dependencies=[Depends(require_admin)])
def list_apps(db: Session = Depends(_get_db)):
    return [_app_view(db, c) for c in db.scalars(select(Client).order_by(Client.created_at))]


@router.post("/admin/apps", dependencies=[Depends(require_admin)], status_code=201)
def create_app(body: AppIn, db: Session = Depends(_get_db)):
    data = _clean(body)
    c, key = create_client(db, data.pop("name"), data.pop("webhook_url"), **data)
    return {"app": _app_view(db, c), **_integration(c, key, c.webhook_secret)}


@router.post("/admin/clients", dependencies=[Depends(require_admin)], status_code=201)
def create_client_compat(body: AppIn, db: Session = Depends(_get_db)):
    r = create_app(body, db)
    return {"id": r["app"]["id"], "name": r["app"]["name"], "api_key": r["api_key"], "webhook_secret": r["webhook_secret"]}


@router.patch("/admin/apps/{app_id}", dependencies=[Depends(require_admin)])
def update_app(app_id: str, body: AppIn, db: Session = Depends(_get_db)):
    c = _one(db, app_id)
    for k, v in _clean(body).items():
        setattr(c, k, v)
    return _app_view(db, c)


@router.delete("/admin/apps/{app_id}", dependencies=[Depends(require_admin)], status_code=204)
def delete_app(app_id: str, db: Session = Depends(_get_db)):
    c = _one(db, app_id)
    live = db.scalar(select(func.count()).select_from(Meeting).where(Meeting.client_id == c.id, Meeting.status.in_(states.ACTIVE)))
    if live:
        raise HTTPException(409, "This app has a call in progress. Wait for it to finish, or switch the app off instead.")
    for m in db.scalars(select(Meeting).where(Meeting.client_id == c.id)):
        db.delete(m)
    db.query(OutboxMessage).filter(OutboxMessage.client_id == c.id).delete()
    db.delete(c)


@router.post("/admin/apps/{app_id}/rotate-key", dependencies=[Depends(require_admin)])
def new_key(app_id: str, db: Session = Depends(_get_db)):
    c = _one(db, app_id)
    return {"app": _app_view(db, c), **_integration(c, rotate_key(db, c), None)}


@router.post("/admin/apps/{app_id}/rotate-secret", dependencies=[Depends(require_admin)])
def new_secret(app_id: str, db: Session = Depends(_get_db)):
    c = _one(db, app_id)
    return {"app": _app_view(db, c), **_integration(c, None, rotate_secret(c))}


@router.post("/admin/apps/{app_id}/test-webhook", dependencies=[Depends(require_admin)])
def test_webhook(app_id: str, db: Session = Depends(_get_db)):
    c = _one(db, app_id)
    if not c.webhook_url:
        raise HTTPException(422, "Add the app's webhook address first.")
    outbox.enqueue(db, c, "test.ping", {"message": "Test from the notetaker console - if your app answered 2xx, webhooks work."})
    return {"ok": True}


@router.get("/admin/apps/{app_id}/deliveries", dependencies=[Depends(require_admin)])
def deliveries(app_id: str, db: Session = Depends(_get_db)):
    _one(db, app_id)
    rows = db.scalars(select(OutboxMessage).where(OutboxMessage.client_id == app_id).order_by(OutboxMessage.created_at.desc()).limit(50))
    return jsonable_encoder([{"id": m.id, "event": m.event, "status": m.status, "attempts": m.attempts, "last_error": m.last_error,
                              "created_at": m.created_at, "delivered_at": m.delivered_at, "meeting_id": m.meeting_id} for m in rows])


@router.post("/admin/deliveries/{delivery_id}/resend", dependencies=[Depends(require_admin)])
def resend(delivery_id: str, db: Session = Depends(_get_db)):
    m = db.get(OutboxMessage, delivery_id)
    if not m:
        raise HTTPException(404, "We couldn't find that delivery.")
    m.status, m.attempts, m.next_attempt_at, m.last_error = "pending", 0, now(), None
    return {"ok": True}


# ---- Calls ------------------------------------------------------------------------------------------

@router.get("/admin/meetings", dependencies=[Depends(require_admin)])
def meetings(app_id: str | None = None, db: Session = Depends(_get_db)):
    q = select(Meeting).order_by(Meeting.created_at.desc()).limit(100)
    if app_id:
        q = q.where(Meeting.client_id == app_id)
    names = {c.id: c.name for c in db.scalars(select(Client))}
    return jsonable_encoder([{**{k: v for k, v in service.meeting_view(m).items() if k != "transcript"}, "app": names.get(m.client_id)}
                             for m in db.scalars(q)])


@router.get("/admin/meetings/{meeting_id}", dependencies=[Depends(require_admin)])
def meeting(meeting_id: str, db: Session = Depends(_get_db)):
    m = db.get(Meeting, meeting_id)
    if not m:
        raise HTTPException(404, "We couldn't find that meeting.")
    v = service.meeting_view(m)
    v["timeline"] = [{"label": states.LABELS.get(e.status, e.status), "detail": e.detail, "at": e.created_at} for e in m.events]
    v["app"] = m.client.name
    return jsonable_encoder(v)


class TryIn(BaseModel):
    app_id: str
    meeting_url: HttpUrl
    title: str | None = None


@router.post("/admin/meetings", dependencies=[Depends(require_admin)], status_code=201)
def try_meeting(body: TryIn, db: Session = Depends(_get_db)):
    c = _one(db, body.app_id)
    m, _ = service.schedule(db, c, meeting_url=str(body.meeting_url), title=body.title, metadata={"sent_from": "console"})
    return jsonable_encoder(service.meeting_view(m))


@router.delete("/admin/meetings/{meeting_id}", dependencies=[Depends(require_admin)])
def stop_meeting(meeting_id: str, db: Session = Depends(_get_db)):
    m = db.get(Meeting, meeting_id)
    if not m:
        raise HTTPException(404, "We couldn't find that meeting.")
    service.cancel(db, m)
    return {"ok": True}
