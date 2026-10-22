"""Connect Zoom (app/services/zoom.py): the sign-in link, Zoom's way back, and disconnecting."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.routes.messaging import current_user
from app.core.identity import Identity, get_identity
from app.db.session import get_db
from app.models import User
from app.services import zoom

router = APIRouter(prefix="/zoom", tags=["zoom"])


@router.get("/start")
def start(return_to: str = "/calls/meetings", user: User = Depends(current_user)):
    try:
        return {"url": zoom.authorize_url(user.id, return_to if return_to.startswith("/") else "/calls/meetings")}
    except zoom.ZoomError as e:
        raise HTTPException(400, str(e))


class CallbackIn(BaseModel):
    code: str
    state: str | None = None


@router.post("/callback")
def callback(payload: CallbackIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)):
    """Called by the frontend's /api/zoom/callback with what Zoom sent back - the signed state says who it is (or,
    without one, whoever is signed in)."""
    try:
        _conn, return_to = zoom.complete(db, payload.code, payload.state, identity.user_uuid)
    except zoom.ZoomError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"return_to": return_to}


@router.get("/connection")
def my_connection(db: Session = Depends(get_db), user: User = Depends(current_user)):
    conn = zoom.connection(db, user.id)
    if conn:
        zoom.check(db, conn)
        db.commit()
    return zoom.view(db, user.id)


@router.delete("/connection", status_code=204)
def disconnect(db: Session = Depends(get_db), user: User = Depends(current_user)):
    zoom.disconnect(db, user.id)
    db.commit()
