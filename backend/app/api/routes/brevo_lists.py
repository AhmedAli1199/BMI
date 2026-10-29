"""TEMPORARY (29 Oct 2026): shows BMI's Brevo lists, so the right list for each magazine can be found once and set in
"Brevo list for each magazine". Delete this file, its page (frontend/src/app/(app)/automations/brevo-lists) and its
line in main.py once that's done."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.identity import Identity, get_identity
from app.roles import ROLE_ADMIN
from app.services import brevo

router = APIRouter(prefix="/brevo", tags=["automations"])


@router.get("/lists")
def brevo_lists(identity: Identity = Depends(get_identity)) -> list[dict]:
    if identity.is_known and identity.role != ROLE_ADMIN:
        raise HTTPException(403, "Only administrators can see the Brevo lists.")
    try:
        return brevo.lists()
    except brevo.BrevoError as exc:
        raise HTTPException(400, str(exc)) from exc
