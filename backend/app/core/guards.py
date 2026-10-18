"""Role checks shared by the routes. Same trust model as identity.py: a call with no
signed-in person (the shared-key system caller) passes; a real person must have the role.
Messages are plain sentences - they reach the screen through friendlyError."""
from __future__ import annotations

from fastapi import Depends, HTTPException

from app.core.identity import Identity, get_identity
from app.roles import CAN_USE_AUTOMATIONS, ROLE_ADMIN


def need_admin(identity: Identity, detail: str = "Only administrators can do this.") -> None:
    if identity.is_known and identity.role != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail=detail)


def need_staff(identity: Identity, detail: str = "Only administrators and data managers can do this.") -> None:
    """Administrators and data managers."""
    if identity.is_known and identity.role not in CAN_USE_AUTOMATIONS:
        raise HTTPException(status_code=403, detail=detail)


def need_self_or_admin(identity: Identity, user_id: str, detail: str = "You can only change your own settings.") -> None:
    if identity.is_known and identity.role != ROLE_ADMIN and str(identity.user_id) != str(user_id):
        raise HTTPException(status_code=403, detail=detail)


def admin_only(identity: Identity = Depends(get_identity)) -> Identity:
    """Route dependency form of need_admin."""
    need_admin(identity)
    return identity
