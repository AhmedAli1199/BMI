"""Connect Zoom. Zoom only lets a notetaker into a call "on behalf of" a signed-in person who is in it (Zoom's rule
for notetakers since March 2026), so each person connects their Zoom once. The notetaker service holds the Zoom
app's keys and the sign-in itself (its README, "Zoom"); BMI Brain sends people to Zoom's sign-in page, hands the
code Zoom sends back to the notetaker, and remembers whose Zoom it is (ZoomConnection).

For a Zoom meeting on the shared calendar, the notetaker joins on behalf of someone from BMI who is going and has
connected Zoom - the organiser first. It can only get in once that person has joined, and the recording ends if
they leave.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ZoomConnection
from app.services import notetaker, outlook

PURPOSE = "zoom"


class ZoomError(Exception):
    """A plain sentence for the person connecting."""


def redirect_uri() -> str:
    return settings.zoom_redirect_uri or f"{settings.app_base_url.rstrip('/')}/api/zoom/callback"


def available() -> bool:
    return bool(notetaker.zoom_info().get("available"))


def authorize_url(user_id: uuid.UUID, return_to: str = "/calls/meetings") -> str:
    info = notetaker.zoom_info(fresh=True)
    if not info.get("available") or not info.get("client_id"):
        raise ZoomError("Zoom isn't set up on the notetaker yet. Ask whoever runs BMI Brain to add the Zoom app's keys to the notetaker.")
    q = {"response_type": "code", "client_id": info["client_id"], "redirect_uri": redirect_uri(),
         "state": outlook.make_state(user_id, return_to, purpose=PURPOSE)}
    return f"https://zoom.us/oauth/authorize?{urlencode(q)}"


def complete(db: Session, code: str, state: str | None, signed_in: uuid.UUID | None = None) -> tuple[ZoomConnection, str]:
    """state: from our own sign-in link. Without one (Zoom's own "Add App Now", or adding the app from Zoom's side)
    it's connected for whoever is signed in to BMI Brain in that browser."""
    if state:
        if outlook.state_purpose(state) != PURPOSE:
            raise ZoomError("That sign-in link isn't valid any more - please try connecting Zoom again.")
        try:
            user_id, return_to = outlook.read_state(state)
        except outlook.OutlookAuthError as e:
            raise ZoomError(str(e))
    elif signed_in:
        user_id, return_to = signed_in, "/calls/meetings"
    else:
        raise ZoomError("Sign in to BMI Brain first, then press Connect Zoom.")
    try:
        got = notetaker.zoom_connect(code, redirect_uri(), str(user_id))
    except notetaker.NotetakerError as e:
        raise ZoomError(str(e))
    conn = connection(db, user_id)
    if conn is None:
        conn = ZoomConnection(id=uuid.uuid4(), user_id=user_id, zoom_user_id=got["zoom_user_id"])
        db.add(conn)
    conn.zoom_user_id, conn.status, conn.last_error = got["zoom_user_id"], "connected", None
    conn.connected_at = conn.checked_at = datetime.now(timezone.utc)
    db.flush()
    return conn, return_to


def connection(db: Session, user_id: uuid.UUID | None) -> ZoomConnection | None:
    return db.scalar(select(ZoomConnection).where(ZoomConnection.user_id == user_id)) if user_id else None


def disconnect(db: Session, user_id: uuid.UUID) -> None:
    conn = connection(db, user_id)
    if conn:
        notetaker.zoom_disconnect(conn.zoom_user_id)
        db.delete(conn)
        db.flush()


def check(db: Session, conn: ZoomConnection) -> ZoomConnection:
    """Ask the notetaker whether the sign-in still works (someone can remove the app from their Zoom)."""
    state = notetaker.zoom_state(conn.zoom_user_id)
    if state == "disconnected":
        conn.status, conn.last_error = "error", "Zoom says it isn't connected any more. Press Reconnect."
    elif state == "connected":
        conn.status, conn.last_error = "connected", None
    conn.checked_at = datetime.now(timezone.utc)
    return conn


def view(db: Session, user_id: uuid.UUID) -> dict:
    conn = connection(db, user_id)
    return {"available": available(), "connected": bool(conn), "status": conn.status if conn else None,
            "last_error": conn.last_error if conn else None, "connected_at": conn.connected_at if conn else None}
