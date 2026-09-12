from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.schemas import (
    AddressOut,
    CompanySummary,
    ContactDetail,
    ContactListItem,
    ContactsPage,
    EmailOut,
    GroupOut,
    HistoryOut,
    NoteOut,
    PhoneOut,
)
from app.db.session import get_db
from app.models import (
    Company,
    Contact,
    Email,
    Group,
    GroupMembership,
    HistoryEntry,
    Note,
)
from app.models.contact_channel import Address, Phone

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=ContactsPage)
def list_contacts(
    q: str | None = Query(None, description="Search by name or email"),
    source_db: str | None = Query(None),
    company_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ContactsPage:
    # Primary email per contact, via a scalar subquery - cheap correlated
    # lookup, fine at this row count (~118k contacts across all sources).
    primary_email_subq = (
        select(Email.address)
        .where(Email.contact_id == Contact.id)
        .order_by(Email.is_primary.desc())
        .limit(1)
        .correlate(Contact)
        .scalar_subquery()
    )

    stmt = (
        select(
            Contact,
            Company.name.label("company_name"),
            primary_email_subq.label("primary_email"),
        )
        .outerjoin(Company, Contact.company_id == Company.id)
    )

    if source_db:
        stmt = stmt.where(Contact.source_db == source_db)
    if company_id:
        stmt = stmt.where(Contact.company_id == company_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Contact.full_name.ilike(like),
                Contact.first_name.ilike(like),
                Contact.last_name.ilike(like),
                Contact.id.in_(select(Email.contact_id).where(Email.address.ilike(like))),
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    stmt = stmt.order_by(Contact.last_name.asc().nulls_last(), Contact.first_name.asc().nulls_last())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    rows = db.execute(stmt).all()
    items = [
        ContactListItem(
            id=contact.id,
            source_db=contact.source_db,
            full_name=contact.full_name,
            first_name=contact.first_name,
            last_name=contact.last_name,
            job_title=contact.job_title,
            company_id=contact.company_id,
            company_name=company_name,
            primary_email=primary_email,
        )
        for contact, company_name, primary_email in rows
    ]
    return ContactsPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{contact_id}", response_model=ContactDetail)
def get_contact(contact_id: uuid.UUID, db: Session = Depends(get_db)) -> ContactDetail:
    contact = db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    company = db.get(Company, contact.company_id) if contact.company_id else None
    addresses = db.scalars(select(Address).where(Address.contact_id == contact_id)).all()
    phones = db.scalars(select(Phone).where(Phone.contact_id == contact_id)).all()
    emails = db.scalars(select(Email).where(Email.contact_id == contact_id)).all()
    groups = db.scalars(
        select(Group).join(GroupMembership, GroupMembership.group_id == Group.id)
        .where(GroupMembership.contact_id == contact_id)
    ).all()
    notes = db.scalars(
        select(Note).where(Note.entity_type == "contact", Note.entity_id == contact_id)
        .order_by(Note.act_created_at.desc().nulls_last())
        .limit(100)
    ).all()
    history = db.scalars(
        select(HistoryEntry).where(HistoryEntry.entity_type == "contact", HistoryEntry.entity_id == contact_id)
        .order_by(HistoryEntry.occurred_at.desc())
        .limit(100)
    ).all()

    return ContactDetail(
        id=contact.id,
        source_db=contact.source_db,
        source_act_id=contact.source_act_id,
        first_name=contact.first_name,
        middle_name=contact.middle_name,
        last_name=contact.last_name,
        full_name=contact.full_name,
        job_title=contact.job_title,
        department=contact.department,
        category=contact.category,
        referred_by=contact.referred_by,
        birthdate=contact.birthdate,
        custom_fields=contact.custom_fields,
        company=CompanySummary.model_validate(company) if company else None,
        addresses=[AddressOut.model_validate(a) for a in addresses],
        phones=[PhoneOut.model_validate(p) for p in phones],
        emails=[EmailOut.model_validate(e) for e in emails],
        groups=[GroupOut.model_validate(g) for g in groups],
        notes=[NoteOut.model_validate(n) for n in notes],
        history=[HistoryOut.model_validate(h) for h in history],
    )
