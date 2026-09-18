from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.schemas import ScheduledJobOut
from app.automations.business_card import process_business_card_photo
from app.automations.returned_copy import process_returned_copy_photo
from app.automations.scheduler import all_jobs, is_enabled
from app.db.session import get_db

router = APIRouter(prefix="/automations", tags=["automations"])


@router.get("/jobs", response_model=list[ScheduledJobOut])
def list_jobs() -> list[ScheduledJobOut]:
    """Status of every registered producer job (see
    app/automations/scheduler.py) - purely informational, so the overview
    screen can show "what's live vs. still switched off" without exposing
    any way to flip it from here. Toggling stays an env-var + restart
    decision, deliberately outside the app's own reach."""
    return [
        ScheduledJobOut(
            id=j.id,
            label=j.label,
            description=j.description,
            cron=j.cron,
            enabled=is_enabled(j),
        )
        for j in all_jobs()
    ]


@router.post("/business-cards/upload")
async def upload_business_card(
    file: UploadFile = File(...),
    source_db: str = Form(...),
    show_context: str | None = Form(None),
    db: Session = Depends(get_db),
) -> dict:
    """SALES-001/002 intake - a rep uploads a photo (possibly several cards
    in one shot) from a trade show; see business_card.py for the full
    read -> match -> queue flow. Synchronous (the vision call happens
    inline, not queued) since a single-image OpenAI round trip is fast
    enough not to need a background job for this - matches how the rest
    of this codebase avoids infrastructure it doesn't need yet."""
    image_bytes = await file.read()
    result = process_business_card_photo(
        db, image_bytes, file.content_type or "image/jpeg",
        source_db=source_db, show_context=show_context,
    )
    return result


@router.post("/returned-copies/upload")
async def upload_returned_copy(
    file: UploadFile = File(...),
    source_db: str = Form(...),
    db: Session = Depends(get_db),
) -> dict:
    """CS-005 intake - a rep uploads a photo of a returned-mail label; see
    returned_copy.py for the full read -> match -> queue flow."""
    image_bytes = await file.read()
    result = process_returned_copy_photo(db, image_bytes, file.content_type or "image/jpeg", source_db=source_db)
    return result
