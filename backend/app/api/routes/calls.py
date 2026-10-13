"""Calls recorded by the notetaker: send it into a Meet or Teams call, follow its progress, read
the notes, save them to the contact's history."""
from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.routes.messaging import current_user
from app.automations import call_notes
from app.db.session import get_db
from app.models import CallRecording, Company, Contact, User
from app.roles import CAN_USE_AUTOMATIONS
from app.services import notetaker

router = APIRouter(prefix="/calls", tags=["calls"])


def _sees_all(user: User) -> bool:
    return user.role in CAN_USE_AUTOMATIONS


def _view(db: Session, c: CallRecording, full: bool = False) -> dict:
    contact = db.get(Contact, c.contact_id) if c.contact_id else None
    company = db.get(Company, c.company_id) if c.company_id else None
    owner = db.get(User, c.user_id) if c.user_id else None
    v = {
        "id": str(c.id), "title": c.title, "meeting_url": c.meeting_url, "platform": c.platform, "status": c.status,
        "status_label": c.status_label or c.status, "status_detail": c.status_detail, "participants": c.participants or [],
        "contact": {"id": str(contact.id), "name": contact.full_name} if contact else None,
        "company": {"id": str(company.id), "name": company.name} if company else None,
        "owner": owner.name if owner else None, "started_at": c.started_at, "ended_at": c.ended_at,
        "saved_to_history_at": c.saved_to_history_at, "created_at": c.created_at,
        "summary": (c.notes or {}).get("summary"),
    }
    if full:
        v["notes"] = c.notes
        v["transcript"] = c.transcript or []
    return v


def _own(db: Session, user: User, call_id: uuid.UUID) -> CallRecording:
    c = db.get(CallRecording, call_id)
    if not c or (not _sees_all(user) and c.user_id != user.id):
        raise HTTPException(404, "We couldn't find that call.")
    return c


@router.get("/status")
def status():
    return {"available": notetaker.configured()}


@router.get("")
def list_calls(contact_id: uuid.UUID | None = None, company_id: uuid.UUID | None = None, limit: int = 100,
               db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = select(CallRecording).order_by(CallRecording.created_at.desc()).limit(min(limit, 500))
    if not _sees_all(user):
        q = q.where(CallRecording.user_id == user.id)
    if contact_id:
        q = q.where(CallRecording.contact_id == contact_id)
    if company_id:
        q = q.where(or_(CallRecording.company_id == company_id))
    return [_view(db, c) for c in db.scalars(q)]


@router.get("/{call_id}")
def get_call(call_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _view(db, _own(db, user, call_id), full=True)


class CallIn(BaseModel):
    meeting_url: str
    title: str | None = None
    contact_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None


@router.post("", status_code=201)
def send_notetaker(body: CallIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not notetaker.configured():
        raise HTTPException(409, "The notetaker isn't set up yet. Ask an administrator to connect it.")
    company_id = body.company_id
    if body.contact_id and not company_id:
        contact = db.get(Contact, body.contact_id)
        company_id = getattr(contact, "company_id", None) if contact else None
    c = CallRecording(id=uuid.uuid4(), user_id=user.id, contact_id=body.contact_id, company_id=company_id,
                      meeting_url=body.meeting_url.strip(), title=(body.title or "").strip() or None, status="scheduled",
                      status_label="Scheduled")
    db.add(c)
    db.flush()
    try:
        m = notetaker.send_bot(meeting_url=c.meeting_url, external_id=str(c.id), title=c.title,
                               metadata={"bmi_call_id": str(c.id), "bmi_user_id": str(user.id)})
    except notetaker.NotetakerError as e:
        db.rollback()
        raise HTTPException(422, str(e))
    c.notetaker_id, c.platform, c.status, c.status_label = m["id"], m.get("platform"), m.get("status", "scheduled"), m.get("status_label")
    db.commit()
    return _view(db, c)


@router.post("/{call_id}/stop")
def stop(call_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = _own(db, user, call_id)
    if c.notetaker_id:
        try:
            notetaker.stop_bot(c.notetaker_id)
        except notetaker.NotetakerError as e:
            raise HTTPException(422, str(e))
    return _view(db, c)


class LinkIn(BaseModel):
    contact_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    title: str | None = None


@router.patch("/{call_id}")
def update_call(call_id: uuid.UUID, body: LinkIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = _own(db, user, call_id)
    data = body.model_dump(exclude_unset=True)
    for k in ("contact_id", "company_id"):
        if k in data:
            setattr(c, k, data[k])
    if "title" in data:
        c.title = (data["title"] or "").strip() or None
    db.commit()
    return _view(db, c, full=True)


@router.post("/{call_id}/save-to-history")
def save(call_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = _own(db, user, call_id)
    if c.status != "completed" or not c.notes:
        raise HTTPException(409, "The notes aren't ready yet.")
    try:
        call_notes.save_to_history(db, c, user.id)
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return _view(db, c, full=True)


# ---- From the Notetaker service (forwarded by the frontend's public /api/notetaker/webhook) ----

def _dt(v) -> datetime | None:
    try:
        return datetime.fromisoformat(v) if v else None
    except (TypeError, ValueError):
        return None


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    if not notetaker.verify(body, request.headers.get("x-notetaker-timestamp", ""), request.headers.get("x-notetaker-signature", "")):
        raise HTTPException(401, "Not allowed.")
    msg = json.loads(body)
    data = msg.get("data") or {}
    call_id = (data.get("metadata") or {}).get("bmi_call_id")
    c = db.get(CallRecording, uuid.UUID(call_id)) if call_id else None
    if not c:
        return {"ok": True, "ignored": True}
    c.notetaker_id = c.notetaker_id or data.get("id")
    c.status, c.status_label, c.status_detail = data.get("status", c.status), data.get("status_label"), data.get("status_detail")
    c.platform = data.get("platform") or c.platform
    c.title = c.title or data.get("title")
    c.participants = data.get("participants") or c.participants
    c.started_at, c.ended_at = _dt(data.get("started_at")) or c.started_at, _dt(data.get("ended_at")) or c.ended_at
    if msg.get("event") == "meeting.completed":
        c.notes, c.transcript = data.get("notes"), data.get("transcript") or []
        if c.notes:
            call_notes.queue_for_review(db, c)
            if c.user_id:
                from app.services.notify import create_notification
                create_notification(db, c.user_id, "call_notes", f"Notes ready: {c.title or 'your call'}",
                                    (c.notes or {}).get("summary"), link=f"/calls/{c.id}")
    elif msg.get("event") == "meeting.failed" and c.user_id:
        from app.services.notify import create_notification
        create_notification(db, c.user_id, "call_notes", f"The notetaker couldn't record {c.title or 'your call'}",
                            c.status_detail, link=f"/calls/{c.id}", email=False)
    db.commit()
    return {"ok": True}
