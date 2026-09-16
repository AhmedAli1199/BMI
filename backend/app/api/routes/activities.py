from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import ActivitiesPage, ActivityCreate, ActivityOut, ActivityUpdate
from app.api.routes._creators import creator_summary, resolve_creators
from app.db.session import get_db
from app.models import Activity, Company, Contact, User

router = APIRouter(prefix="/activities", tags=["activities"])


def _out(
    activity: Activity,
    creators: dict[uuid.UUID, User],
    contacts: dict[uuid.UUID, Contact] | None = None,
    companies: dict[uuid.UUID, Company] | None = None,
) -> ActivityOut:
    out = ActivityOut.model_validate(activity)
    out.created_by = creator_summary(activity, creators)
    if activity.contact_id and contacts:
        contact = contacts.get(activity.contact_id)
        if contact:
            out.contact_name = contact.full_name or f"{contact.first_name or ''} {contact.last_name or ''}".strip() or None
    if activity.company_id and companies:
        company = companies.get(activity.company_id)
        if company:
            out.company_name = company.name
    return out


def _resolve_names(db: Session, rows: list[Activity]) -> tuple[dict[uuid.UUID, Contact], dict[uuid.UUID, Company]]:
    contact_ids = {r.contact_id for r in rows if r.contact_id}
    company_ids = {r.company_id for r in rows if r.company_id}
    contacts = {c.id: c for c in db.scalars(select(Contact).where(Contact.id.in_(contact_ids)))} if contact_ids else {}
    companies = {c.id: c for c in db.scalars(select(Company).where(Company.id.in_(company_ids)))} if company_ids else {}
    return contacts, companies


@router.get("", response_model=ActivitiesPage)
def list_activities(
    source_db: str | None = Query(None),
    assigned_user_id: uuid.UUID | None = Query(None, description="Only this user's scheduled activities"),
    start_after: datetime | None = Query(None, description="Only activities starting on/after this instant"),
    start_before: datetime | None = Query(None, description="Only activities starting on/before this instant"),
    is_cleared: bool | None = Query(None, description="Filter to done (true) or not-yet-done (false) items"),
    contact_id: uuid.UUID | None = Query(None),
    company_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ActivitiesPage:
    stmt = select(Activity)
    if source_db:
        stmt = stmt.where(Activity.source_db == source_db)
    if assigned_user_id:
        stmt = stmt.where(Activity.created_by_user_id == assigned_user_id)
    if start_after:
        stmt = stmt.where(Activity.start_at >= start_after)
    if start_before:
        stmt = stmt.where(Activity.start_at <= start_before)
    if is_cleared is not None:
        stmt = stmt.where(Activity.is_cleared == is_cleared)
    if contact_id:
        stmt = stmt.where(Activity.contact_id == contact_id)
    if company_id:
        stmt = stmt.where(Activity.company_id == company_id)

    total = len(db.scalars(stmt).all())
    rows = db.scalars(
        stmt.order_by(Activity.start_at.asc()).offset((page - 1) * page_size).limit(page_size)
    ).all()

    creators = resolve_creators(db, rows)
    contacts, companies = _resolve_names(db, rows)

    return ActivitiesPage(
        items=[_out(r, creators, contacts, companies) for r in rows], total=total, page=page, page_size=page_size
    )


@router.post("", response_model=ActivityOut, status_code=201)
def create_activity(payload: ActivityCreate, db: Session = Depends(get_db)) -> ActivityOut:
    if not payload.contact_id and not payload.company_id:
        raise HTTPException(status_code=400, detail="Must be linked to a contact or a company")
    if payload.contact_id and payload.company_id:
        raise HTTPException(status_code=400, detail="Link to a contact or a company, not both")
    if payload.contact_id and not db.get(Contact, payload.contact_id):
        raise HTTPException(status_code=404, detail="Contact not found")
    if payload.company_id and not db.get(Company, payload.company_id):
        raise HTTPException(status_code=404, detail="Company not found")

    activity = Activity(
        id=uuid.uuid4(),
        source_db=payload.source_db,
        source_act_id=str(uuid.uuid4()),
        contact_id=payload.contact_id,
        company_id=payload.company_id,
        activity_type=payload.activity_type,
        subject=payload.subject,
        details=payload.details,
        location=payload.location,
        start_at=payload.start_at,
        end_at=payload.end_at,
        is_timeless=payload.is_timeless,
        is_private=payload.is_private,
        recurrence=payload.recurrence,
        created_by_user_id=payload.created_by_user_id,
    )
    db.add(activity)
    db.commit()
    contacts, companies = _resolve_names(db, [activity])
    return _out(activity, resolve_creators(db, [activity]), contacts, companies)


@router.patch("/{activity_id}", response_model=ActivityOut)
def update_activity(activity_id: uuid.UUID, payload: ActivityUpdate, db: Session = Depends(get_db)) -> ActivityOut:
    activity = db.get(Activity, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(activity, field, value)
    db.commit()

    contacts, companies = _resolve_names(db, [activity])
    return _out(activity, resolve_creators(db, [activity]), contacts, companies)


@router.delete("/{activity_id}", status_code=204, response_model=None)
def delete_activity(activity_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    activity = db.get(Activity, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    db.delete(activity)
    db.commit()
