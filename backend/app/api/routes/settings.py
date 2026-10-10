from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.schemas import (
    PreferenceDefOut,
    PreferenceOptionOut,
    UserPreferencesOut,
    UserPreferencesUpdate,
)
from app.core.identity import Identity, get_identity
from app.db.session import get_db
from app.models import User
from app.preferences import PREFERENCE_DEFS, get_def, resolve

router = APIRouter(tags=["settings"])


def require_admin(identity: Identity = Depends(get_identity)) -> Identity:
    """Platform settings are for administrators only. Like require_staff, it lets
    the shared-key system caller through when no person is signed in."""
    if identity.is_known and identity.role != "admin":
        raise HTTPException(status_code=403, detail="Only administrators can change this setting.")
    return identity


# ---- Sections shown to each role -------------------------------------------------

class SectionOut(BaseModel):
    key: str
    label: str
    group: str
    description: str


class SectionsOut(BaseModel):
    sections: list[SectionOut]
    roles: list[str]
    hidden: dict[str, list[str]]  # role -> hidden section keys (only filled in for admins)
    mine: list[str]  # what's hidden for the person asking


class SectionsIn(BaseModel):
    hidden: dict[str, list[str]]


@router.get("/ui/sections", response_model=SectionsOut)
def get_sections(db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> SectionsOut:
    from app import ui_sections as us

    is_admin = not identity.is_known or identity.role == "admin"
    return SectionsOut(
        sections=[SectionOut(**s.__dict__) for s in us.SECTIONS], roles=list(us.HIDEABLE_ROLES),
        hidden=us.hidden_by_role(db) if is_admin else {}, mine=us.hidden_for(db, identity.role if identity.is_known else None),
    )


@router.put("/ui/sections", response_model=SectionsOut)
def save_sections(payload: SectionsIn, db: Session = Depends(get_db), identity: Identity = Depends(require_admin)) -> SectionsOut:
    from app import ui_sections as us

    us.save(db, payload.hidden)
    db.commit()
    return get_sections(db, identity)


@router.get("/settings/definitions", response_model=list[PreferenceDefOut])
def list_preference_definitions() -> list[PreferenceDefOut]:
    """Every registered preference, with its full label/description/choices
    - the Settings page renders entirely from this, so a new preference
    (app/preferences.py) shows up with zero frontend changes."""
    return [
        PreferenceDefOut(
            key=p.key, label=p.label, description=p.description, group=p.group, default=p.default,
            options=[PreferenceOptionOut(value=o.value, label=o.label, description=o.description) for o in p.options],
        )
        for p in PREFERENCE_DEFS
    ]


def _try_parse_uuid(user_id: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(user_id)
    except ValueError:
        return None


@router.get("/users/{user_id}/preferences", response_model=UserPreferencesOut)
def get_user_preferences(user_id: str, db: Session = Depends(get_db)) -> UserPreferencesOut:
    # user_id is a plain str, not uuid.UUID, specifically so a non-UUID
    # value (the frontend's "local-dev" bypass session, which has no real
    # user row) falls through to registry defaults below instead of a 422
    # before this code even runs - reading preferences should never be a
    # hard failure for a page that also renders everything else just fine.
    parsed = _try_parse_uuid(user_id)
    user = db.get(User, parsed) if parsed else None
    stored = user.preferences if user else {}
    return UserPreferencesOut(values=resolve(stored))


@router.patch("/users/{user_id}/preferences", response_model=UserPreferencesOut)
def update_user_preferences(
    user_id: str, payload: UserPreferencesUpdate, db: Session = Depends(get_db)
) -> UserPreferencesOut:
    parsed = _try_parse_uuid(user_id)
    user = db.get(User, parsed) if parsed else None
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for key, value in payload.values.items():
        pref_def = get_def(key)
        if not pref_def:
            raise HTTPException(status_code=400, detail=f"Unknown preference: {key}")
        if not any(o.value == value for o in pref_def.options):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid value {value!r} for {key} - choose one of {[o.value for o in pref_def.options]}",
            )

    # Merge, don't replace - a PATCH with one key shouldn't wipe every
    # other preference the user has already set.
    user.preferences = {**user.preferences, **payload.values}
    db.commit()
    return UserPreferencesOut(values=resolve(user.preferences))
