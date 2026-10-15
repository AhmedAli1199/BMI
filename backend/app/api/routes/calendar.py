"""The shared calendar: connecting Google/Outlook calendars, the merged meetings, per-meeting Record/Skip,
and each person's recording preference."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.messaging import current_user
from app.db.session import get_db
from app.models import AutomationJobRun, CallRecording, Company, Contact, User
from app.models.calendar import CalendarAttendance, CalendarConnection, CalendarMeeting
from app.roles import CAN_MANAGE_USERS, CAN_USE_AUTOMATIONS
from app.services import calendar_providers as cp
from app.services import calendar_sync as cs
from app.services import notetaker, outlook

router = APIRouter(prefix="/calendar", tags=["calendar"])


def _sees_all(user: User) -> bool:
    return user.role in CAN_USE_AUTOMATIONS


# ---- Connections --------------------------------------------------------------------------------

def _conn_view(c: CalendarConnection) -> dict:
    return {"provider": c.provider, "email": c.email, "status": c.status, "last_error": c.last_error,
            "last_synced_at": c.last_synced_at, "connected_at": c.connected_at}


@router.get("/connections")
def connections(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.scalars(select(CalendarConnection).where(CalendarConnection.user_id == user.id)).all()
    return {"connections": [_conn_view(c) for c in rows], "google_available": cp.google_configured(),
            "microsoft_available": outlook.is_configured(), "notetaker_available": notetaker.configured(),
            "preference": cs.pref(user)}


@router.get("/microsoft/start")
def microsoft_start(return_to: str = "/calls/meetings", user: User = Depends(current_user)):
    try:
        return {"url": cp.ms_authorize_url(user.id, return_to)}
    except outlook.OutlookNotConfigured:
        raise HTTPException(400, "Outlook sign-in isn't set up yet.")


@router.get("/google/start")
def google_start(return_to: str = "/calls/meetings", user: User = Depends(current_user)):
    try:
        return {"url": cp.google_authorize_url(user.id, return_to)}
    except cp.CalendarNotConfigured:
        raise HTTPException(400, "Google Calendar isn't set up yet. Ask an administrator to add it.")


def _save_connection(db: Session, user_id: uuid.UUID, provider: str, body: dict, email: str) -> CalendarConnection:
    conn = db.scalar(select(CalendarConnection).where(CalendarConnection.user_id == user_id, CalendarConnection.provider == provider))
    if not conn:
        conn = CalendarConnection(id=uuid.uuid4(), user_id=user_id, provider=provider, email=email, refresh_token_enc="")
        db.add(conn)
    if not body.get("refresh_token") and not conn.refresh_token_enc:
        raise HTTPException(400, "The sign-in didn't give lasting access. Please remove BMI Brain from your account's connected apps and connect again.")
    conn.email = email or conn.email
    cp._store(conn, body)
    conn.last_synced_at = None
    db.flush()
    cs.sync_connection(db, conn)
    db.commit()
    return conn


def complete_microsoft(db: Session, code: str, state: str) -> dict:
    user_id, return_to = outlook.read_state(state)
    try:
        body, email = cp.ms_complete(code)
    except cp.CalendarAuthError as e:
        raise HTTPException(400, str(e))
    conn = _save_connection(db, user_id, "microsoft", body, email)
    return {"email": conn.email, "return_to": return_to}


class CallbackIn(BaseModel):
    code: str
    state: str


@router.post("/google/callback")
def google_callback(payload: CallbackIn, db: Session = Depends(get_db)):
    try:
        user_id, return_to = outlook.read_state(payload.state)
        body, email = cp.google_complete(payload.code)
    except (outlook.OutlookAuthError, cp.CalendarAuthError) as e:
        raise HTTPException(400, str(e))
    conn = _save_connection(db, user_id, "google", body, email)
    return {"email": conn.email, "return_to": return_to}


@router.delete("/connections/{provider}", status_code=204)
def disconnect(provider: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    conn = db.scalar(select(CalendarConnection).where(CalendarConnection.user_id == user.id, CalendarConnection.provider == provider))
    if not conn:
        return
    mids = {a.meeting_id for a in db.scalars(select(CalendarAttendance).where(CalendarAttendance.connection_id == conn.id))}
    db.delete(conn)
    db.flush()
    for mid in mids:
        if not db.scalar(select(CalendarAttendance.id).where(CalendarAttendance.meeting_id == mid).limit(1)):
            m = db.get(CalendarMeeting, mid)
            if m:
                m.status = "cancelled"
    cs.plan(db)


@router.post("/sync")
def sync_now(db: Session = Depends(get_db), user: User = Depends(current_user)):
    for conn in db.scalars(select(CalendarConnection).where(CalendarConnection.user_id == user.id)):
        cs.sync_connection(db, conn)
    db.commit()
    return cs.plan(db)


class PreferenceIn(BaseModel):
    mode: str


@router.put("/preference")
def set_preference(body: PreferenceIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if body.mode not in ("auto", "remind", "off"):
        raise HTTPException(422, "Choose join automatically, just remind me, or off.")
    user.preferences = {**(user.preferences or {}), cs.PREF_KEY: body.mode}
    db.commit()
    cs.plan(db)
    return {"preference": body.mode}


# ---- The shared calendar ------------------------------------------------------------------------

def _meeting_view(db: Session, m: CalendarMeeting, user: User, domains: set[str], names: dict) -> dict | None:
    atts = cs.attending(db, m)
    mine = next((a for a in atts if a.user_id == user.id), None)
    if not mine and not _sees_all(user):
        return None
    private = bool(atts) and all(a.is_private for a in atts)
    d = cs.should_record(db, m, domains)
    call = cs.latest_call(db, m)
    base = {"id": str(m.id), "start_at": m.start_at, "end_at": m.end_at, "is_all_day": m.is_all_day, "status": m.status,
            "mine": bool(mine), "my_response": mine.response if mine else None}
    if private and not mine:
        return {**base, "private": True, "title": "Private meeting", "bmi_people": [], "outside_people": [], "platform": None,
                "join_url": None, "decision": {"record": d.record, "reason": "Private"}, "override": None, "call": None,
                "outcome": {"tone": "muted", "text": "Private"},
                "contact": None, "company": None}
    contact = db.get(Contact, m.contact_id) if m.contact_id else None
    company = db.get(Company, m.company_id) if m.company_id else None
    return {**base, "private": private, "title": m.title or "Untitled meeting", "platform": m.platform, "join_url": m.join_url,
            "organizer": m.organizer_name or m.organizer_email,
            "bmi_people": [{"name": names.get(a.user_id, "Someone"), "response": a.response} for a in atts],
            "outside_people": [{"name": p.get("name") or p["email"], "email": p["email"]} for p in cs.outside_people(m, domains)],
            "decision": {"record": d.record, "reason": d.reason}, "override": m.record_override,
            "outcome": cs.outcome(m, call, d),
            "last_error": m.last_error,
            "call": {"id": str(call.id), "status": call.status, "status_label": call.status_label} if call else None,
            "contact": {"id": str(contact.id), "name": contact.full_name} if contact else None,
            "company": {"id": str(company.id), "name": company.name} if company else None}


@router.get("/meetings")
def meetings(days_back: int = 1, days_ahead: int = 14, mine_only: bool = False,
             db: Session = Depends(get_db), user: User = Depends(current_user)):
    now = datetime.now(timezone.utc)
    q = (select(CalendarMeeting).where(CalendarMeeting.start_at >= now - timedelta(days=min(days_back, 30)),
                                       CalendarMeeting.start_at <= now + timedelta(days=min(days_ahead, 30)),
                                       CalendarMeeting.status == "active")
         .order_by(CalendarMeeting.start_at))
    if mine_only or not _sees_all(user):
        q = q.where(CalendarMeeting.id.in_(select(CalendarAttendance.meeting_id).where(CalendarAttendance.user_id == user.id)))
    domains = cs.internal_domains(db)
    names = {u.id: u.name for u in db.scalars(select(User))}
    rows = [v for m in db.scalars(q).all() if (v := _meeting_view(db, m, user, domains, names))]
    return {"meetings": rows, "people": sorted({p["name"] for r in rows for p in r["bmi_people"]})}


class OverrideIn(BaseModel):
    choice: str | None   # record | skip | None (follow the rules)


@router.post("/meetings/{meeting_id}/override")
def override(meeting_id: uuid.UUID, body: OverrideIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    m = db.get(CalendarMeeting, meeting_id)
    mine = m and db.scalar(select(CalendarAttendance.id).where(CalendarAttendance.meeting_id == m.id, CalendarAttendance.user_id == user.id).limit(1))
    if not m or not (mine or _sees_all(user)):
        raise HTTPException(404, "We couldn't find that meeting.")
    if body.choice not in ("record", "skip", None):
        raise HTTPException(422, "Choose record or skip.")
    m.record_override, m.override_by_user_id = body.choice, user.id if body.choice else None
    db.commit()
    cs.plan(db)
    domains = cs.internal_domains(db)
    return _meeting_view(db, m, user, domains, {u.id: u.name for u in db.scalars(select(User))})


# ---- Admin: is it working, and starting over ----------------------------------------------------

def _admin(user: User) -> None:
    if user.role not in CAN_MANAGE_USERS:
        raise HTTPException(403, "Only an administrator can do this.")


def _ago(t: datetime | None) -> str:
    if not t:
        return "never"
    mins = int((cs.now() - t).total_seconds() // 60)
    return "just now" if mins < 1 else f"{mins} min ago" if mins < 120 else f"{mins // 60} hours ago" if mins < 2880 else f"{mins // 1440} days ago"


@router.get("/health")
def health(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """The Notetaker check: each thing the automatic notetaker needs, and whether it's working."""
    _admin(user)
    from app.automations.scheduler import all_jobs, is_enabled
    from app.core.config import settings
    checks: list[dict] = []
    ok, text = notetaker.check()
    checks.append({"label": "The notetaker service", "ok": ok, "text": text})
    checks.append({"label": "Notes coming back", "ok": bool(settings.notetaker_webhook_secret),
                   "text": "Set up" if settings.notetaker_webhook_secret else
                   "NOTETAKER_WEBHOOK_SECRET isn't set, so BMI Brain can't accept the notes and status updates the notetaker sends back."})
    job = next((j for j in all_jobs() if j.id == "calendar_sync"), None)
    on = bool(job and is_enabled(job))
    last = db.scalar(select(AutomationJobRun).where(AutomationJobRun.job_id == "calendar_sync").order_by(AutomationJobRun.started_at.desc()).limit(1))
    if not on:
        checks.append({"label": "Calendar job", "ok": False, "text": "Switched off in Automations, so meetings aren't read and the notetaker is never booked."})
    elif not last:
        checks.append({"label": "Calendar job", "ok": False, "text": "Switched on but it hasn't run yet. It runs every 3 minutes while the backend is up."})
    elif last.status == "failed":
        checks.append({"label": "Calendar job", "ok": False, "text": f"Last run {_ago(last.started_at)} went wrong. See Automations, Scanners, Shared calendar for details."})
    elif cs.now() - last.started_at > timedelta(minutes=15):
        checks.append({"label": "Calendar job", "ok": False, "text": f"Hasn't run since {_ago(last.started_at)}. It should run every 3 minutes - the backend may have restarted or stopped its jobs."})
    else:
        checks.append({"label": "Calendar job", "ok": True, "text": f"Running - last run {_ago(last.started_at)}"})
    names = {u.id: u.name for u in db.scalars(select(User))}
    conns = db.scalars(select(CalendarConnection)).all()
    if not conns:
        checks.append({"label": "Calendars", "ok": False, "text": "Nobody has connected a calendar yet."})
    for c in conns:
        label = f"{names.get(c.user_id, 'Someone')}'s {'Outlook' if c.provider == 'microsoft' else 'Google'} calendar"
        if c.status == "error":
            checks.append({"label": label, "ok": False, "text": c.last_error or "Needs reconnecting."})
        elif c.last_error:
            checks.append({"label": label, "ok": False, "text": c.last_error})
        elif not c.last_synced_at or cs.now() - c.last_synced_at > timedelta(minutes=20):
            checks.append({"label": label, "ok": False, "text": f"Last read {_ago(c.last_synced_at)}."})
        else:
            checks.append({"label": label, "ok": True, "text": f"Read {_ago(c.last_synced_at)}"})
    week = cs.now() - timedelta(days=7)
    domains = cs.internal_domains(db)
    missed = []
    for m in db.scalars(select(CalendarMeeting).where(CalendarMeeting.start_at >= week, CalendarMeeting.end_at <= cs.now(),
                                                      CalendarMeeting.status == "active").order_by(CalendarMeeting.start_at.desc())):
        d = cs.should_record(db, m, domains)
        o = cs.outcome(m, cs.latest_call(db, m), d)
        if o["tone"] == "bad":
            missed.append({"title": m.title or "Untitled meeting", "start_at": m.start_at, "text": o["text"]})
    return {"checks": checks, "missed": missed[:20], "missed_count": len(missed)}


@router.post("/start-over")
def start_over(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Clears the meeting history (connections stay) and reads every calendar again from scratch."""
    _admin(user)
    out = cs.start_over(db)
    cs.sync_all(db, force=True)
    out.update(cs.plan(db))
    return out
