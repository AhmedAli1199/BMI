"""Your writing profile ("Teach the Brain how you write", app/proposals/style.py) and the proposal requests report."""
from __future__ import annotations

import statistics
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.messaging import current_user
from app.automations import llm
from app.core.identity import Identity, get_identity
from app.db.session import get_db
from app.models import Contact, ReviewQueueItem, SalesDeal, User
from app.proposals import style
from app.roles import CAN_USE_AUTOMATIONS

router = APIRouter(prefix="/proposal-style", tags=["proposals"])


def _out(db: Session, wp, user: User) -> dict:
    return {
        "status": wp.status if wp else "draft",
        "profile": style.normalise(wp.profile if wp and wp.profile else None),
        "built_by": wp.built_by if wp else None, "built_at": wp.built_at.isoformat() if wp and wp.built_at else None,
        "notes": (wp.notes if wp else None) or "",
        "samples": [{"id": s["id"], "name": s["name"], "source": s["source"], "chars": len(s["text"]), "preview": s["text"][:220],
                     "added_at": s.get("added_at")} for s in (wp.samples if wp else []) or []],
        "learned": (wp.learned if wp else []) or [],
        "edits": len((wp.edits if wp else []) or []),
        "items": style.ITEMS, "situations": style.SITUATIONS, "ai_on": llm.is_configured(), "mailbox": user.email,
    }


@router.get("")
def get_profile(db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    return _out(db, style.get(db, user.id), user)


@router.post("/samples")
async def upload_sample(request: Request, name: str = "Proposal", db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    """A past proposal as a file (Word, PDF, text or a saved email) - sent as the request body."""
    data = await request.body()
    if not data:
        raise HTTPException(422, "That file was empty.")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "That file is over 15 MB. Try a smaller one, or paste the text instead.")
    try:
        text = style.read_file(name, data)
    except Exception:
        raise HTTPException(422, "We couldn't read that file. Try a Word document or PDF, or paste the text instead.")
    wp = style.get_or_create(db, user.id)
    try:
        style.add_sample(wp, name.rsplit(".", 1)[0], text, "upload")
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return _out(db, wp, user)


class PasteIn(BaseModel):
    name: str = Field(default="Pasted proposal", max_length=120)
    text: str = Field(min_length=1, max_length=60000)


@router.post("/samples/paste")
def paste_sample(p: PasteIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    wp = style.get_or_create(db, user.id)
    try:
        style.add_sample(wp, p.name, p.text, "paste")
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return _out(db, wp, user)


@router.delete("/samples/{sid}")
def delete_sample(sid: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    wp = style.get_or_create(db, user.id)
    wp.samples = [s for s in wp.samples or [] if s["id"] != sid]
    db.commit()
    return _out(db, wp, user)


@router.post("/find-sent")
def find_sent(db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    """Looks in your Outlook Sent Items for emails that read like proposals, and adds the best ones."""
    from app.graph_client import GraphRequestError
    try:
        found = style.find_in_sent(user.email)
    except GraphRequestError:
        raise HTTPException(409, "We couldn't look in your Sent Items just now. Upload or paste a few proposals instead.")
    except Exception:
        raise HTTPException(409, "Looking in Sent Items isn't set up for this account. Upload or paste a few proposals instead.")
    wp = style.get_or_create(db, user.id)
    have = {s["name"] for s in wp.samples or []}
    added = 0
    for f in found:
        if f["name"] in have:
            continue
        try:
            style.add_sample(wp, f["name"], f["text"], "sent")
            added += 1
        except ValueError:
            break
    db.commit()
    return {**_out(db, wp, user), "found": added}


class NotesIn(BaseModel):
    notes: str = Field(default="", max_length=8000)


@router.put("/notes")
def save_notes(p: NotesIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    wp = style.get_or_create(db, user.id)
    wp.notes = p.notes.strip() or None
    db.commit()
    return _out(db, wp, user)


@router.post("/build")
def build(db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    """Drafts your profile from your proposals and note. Nothing changes in your drafts until you save it."""
    wp = style.get_or_create(db, user.id)
    if not wp.samples and not wp.notes:
        raise HTTPException(422, "Add a few past proposals, or tell us how you work, first.")
    style.build(db, wp, user)
    db.commit()
    return _out(db, wp, user)


class ProfileIn(BaseModel):
    profile: dict


@router.put("")
def save(p: ProfileIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    wp = style.get_or_create(db, user.id)
    wp.profile, wp.status = style.normalise(p.profile), "ready"
    wp.built_at = wp.built_at or datetime.now(timezone.utc)
    db.commit()
    return _out(db, wp, user)


@router.post("/reset")
def reset(db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    """Back to the standard style (your proposals and note are kept)."""
    wp = style.get_or_create(db, user.id)
    wp.profile, wp.status, wp.learned, wp.edits = {}, "draft", [], []
    db.commit()
    return _out(db, wp, user)


class LearnedIn(BaseModel):
    active: bool


@router.put("/learned/{key}")
def set_learned(key: str, p: LearnedIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    wp = style.get_or_create(db, user.id)
    wp.learned = [{**x, "active": p.active} if x.get("key") == key else x for x in wp.learned or []]
    db.commit()
    return _out(db, wp, user)


# ---- report -------------------------------------------------------------------------------------------

report_router = APIRouter(prefix="/proposal-report", tags=["proposals"])


def _company_of(db: Session, it: ReviewQueueItem) -> uuid.UUID | None:
    if it.entity_type == "company":
        return it.entity_id
    if it.entity_type == "contact" and it.entity_id:
        c = db.get(Contact, it.entity_id)
        return c.company_id if c else None
    return None


@report_router.get("")
def report(days: int = 90, user_id: uuid.UUID | None = None, db: Session = Depends(get_db), user: User = Depends(current_user),
           identity: Identity = Depends(get_identity)) -> dict:
    """Proposal requests in the last `days`: how many came in, how fast each got a reply, and how many became bookings.
    Managers see everyone; a salesperson sees their own."""
    staff = not identity.is_known or identity.role in CAN_USE_AUTOMATIONS
    who = user_id if staff else user.id
    since = datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 730)))
    q = select(ReviewQueueItem).where(ReviewQueueItem.kind == "proposal_request", ReviewQueueItem.created_at >= since)
    items = list(db.scalars(q))
    if who:
        items = [i for i in items if (i.payload or {}).get("owner_user_id") == str(who)]
    names = {u.id: u.name for u in db.scalars(select(User))}
    rows: dict[str, dict] = {}
    by_type: dict[str, int] = {}
    by_mag: dict[str, int] = {}
    for it in items:
        p = it.payload or {}
        owner = p.get("owner_user_id") or "none"
        r = rows.setdefault(owner, {"user_id": owner if owner != "none" else None,
                                    "name": names.get(uuid.UUID(owner), "Someone") if owner != "none" else "No owner",
                                    "received": 0, "replied": 0, "not_requests": 0, "waiting": 0, "proposals": 0, "bookings": 0,
                                    "booked_gbp": 0.0, "hours": []})
        r["received"] += 1
        f = p.get("facets") or {}
        by_type[f.get("type", "Other")] = by_type.get(f.get("type", "Other"), 0) + 1
        by_mag[f.get("magazine", "Not sure")] = by_mag.get(f.get("magazine", "Not sure"), 0) + 1
        if it.status == "pending":
            r["waiting"] += 1
            continue
        if it.resolved_action == "not_request":
            r["not_requests"] += 1
            continue
        if it.resolved_action in ("send", "replied", "proposal"):
            r["replied"] += 1
            if it.reviewed_at and it.created_at:
                r["hours"].append((it.reviewed_at - it.created_at).total_seconds() / 3600)
        if p.get("proposal_id"):
            r["proposals"] += 1
        company_id = _company_of(db, it)
        deals = []
        if p.get("proposal_id"):
            deals += list(db.scalars(select(SalesDeal).where(SalesDeal.proposal_id == uuid.UUID(p["proposal_id"]))))
        if company_id:
            deals += list(db.scalars(select(SalesDeal).where(SalesDeal.company_id == company_id, SalesDeal.created_at >= it.created_at,
                                                             SalesDeal.status != "cancelled")))
        uniq = {d.id: d for d in deals if d.status != "cancelled"}
        if uniq:
            r["bookings"] += 1
            r["booked_gbp"] += sum(float(d.total_gbp or 0) for d in uniq.values())
    out = []
    for r in rows.values():
        hrs = r.pop("hours")
        r["median_hours"] = round(statistics.median(hrs), 1) if hrs else None
        r["booked_gbp"] = round(r["booked_gbp"], 2)
        out.append(r)
    out.sort(key=lambda r: -r["received"])
    total = {k: sum(r[k] for r in out) for k in ("received", "replied", "not_requests", "waiting", "proposals", "bookings", "booked_gbp")}
    all_hours = [h for it in items for h in ([(it.reviewed_at - it.created_at).total_seconds() / 3600]
                                              if it.reviewed_at and it.created_at and it.resolved_action in ("send", "replied", "proposal") else [])]
    total["median_hours"] = round(statistics.median(all_hours), 1) if all_hours else None
    people = [{"id": str(u.id), "name": u.name} for u in db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.name))] if staff else []
    return {"days": days, "rows": out, "total": total, "by_type": by_type, "by_magazine": by_mag, "staff": staff, "people": people}
