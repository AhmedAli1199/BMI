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
from app.models import CallRecording, Company, Contact, User
from app.models.calendar import CalendarAttendance, CalendarConnection, CalendarMeeting
from app.roles import CAN_USE_AUTOMATIONS
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
    call = db.get(CallRecording, m.call_id) if m.call_id else None
    if not call:
        call = db.scalar(select(CallRecording).where(CallRecording.calendar_meeting_id == m.id).order_by(CallRecording.created_at.desc()).limit(1))
    base = {"id": str(m.id), "start_at": m.start_at, "end_at": m.end_at, "is_all_day": m.is_all_day, "status": m.status,
            "mine": bool(mine), "my_response": mine.response if mine else None}
    if private and not mine:
        return {**base, "private": True, "title": "Private meeting", "bmi_people": [], "outside_people": [], "platform": None,
                "join_url": None, "decision": {"record": d.record, "reason": "Private"}, "override": None, "call": None,
                "contact": None, "company": None}
    contact = db.get(Contact, m.contact_id) if m.contact_id else None
    company = db.get(Company, m.company_id) if m.company_id else None
    return {**base, "private": private, "title": m.title or "Untitled meeting", "platform": m.platform, "join_url": m.join_url,
            "organizer": m.organizer_name or m.organizer_email,
            "bmi_people": [{"name": names.get(a.user_id, "Someone"), "response": a.response} for a in atts],
            "outside_people": [{"name": p.get("name") or p["email"], "email": p["email"]} for p in cs.outside_people(m, domains)],
            "decision": {"record": d.record, "reason": d.reason}, "override": m.record_override,
            # only worth showing while there's still time to act on it
            "last_error": m.last_error if m.end_at and m.end_at > cs.now() else None,
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
