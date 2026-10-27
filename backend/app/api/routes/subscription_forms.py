"""Subscription sign-up forms (app/automations/subscription_forms.py): the four addresses, and receiving an entry."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.automations import subscription_forms as sf
from app.core.config import settings
from app.core.identity import Identity, get_identity
from app.db.session import get_db
from app.models import ReviewQueueItem
from app.roles import CAN_USE_AUTOMATIONS

router = APIRouter(prefix="/subscription-forms", tags=["automations"])


@router.get("")
def list_forms(db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> list[dict]:
    """Each form's address to paste into Wufoo, Elementor or Stova (administrators and data managers)."""
    if identity.is_known and identity.role not in CAN_USE_AUTOMATIONS:
        raise HTTPException(403, "Only administrators and data managers can see the sign-up form addresses.")
    tokens = sf.tokens(db)
    db.commit()
    form_key = ReviewQueueItem.payload["form"].astext.label("form_key")
    counts = dict(db.execute(select(form_key, func.count()).where(ReviewQueueItem.kind == sf.KIND).group_by("form_key")).all())
    base = settings.app_base_url.rstrip("/")
    return [{"key": f.key, "title": f.title, "tool": f.tool, "received": counts.get(f.key, 0),
             "address": f"{base}/api/subscribe-forms/{f.key}/{tokens[f.key]}"} for f in sf.FORMS.values()]


@router.post("/receive/{key}/{token}")
async def receive(key: str, token: str, request: Request, db: Session = Depends(get_db)) -> dict:
    """An entry from the form itself (forwarded by the frontend's public /api/subscribe-forms/{key}/{token})."""
    f = sf.form_for(db, key, token)
    if not f:
        raise HTTPException(404, "Not found.")
    ctype = request.headers.get("content-type", "")
    if "multipart/form-data" in ctype or "application/x-www-form-urlencoded" in ctype:
        form = await request.form()
        ref, answers = sf.parse(ctype, b"", {k: v for k, v in form.items() if isinstance(v, str)})
    else:
        ref, answers = sf.parse(ctype, await request.body())
    if not answers:
        raise HTTPException(422, "The entry had no answers in it.")
    item = sf.receive(db, f, ref, answers)
    db.commit()
    return {"ok": True, "queued": bool(item)}
