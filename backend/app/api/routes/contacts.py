from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.schemas import (
    MANUAL_SOURCE_DB,
    AddressOut,
    CompanySummary,
    ContactCreate,
    ContactDetail,
    ContactListItem,
    ContactsPage,
    ContactUpdate,
    EmailOut,
    GroupOut,
    HistoryOut,
    NoteOut,
    PhoneOut,
)
from app.db.session import get_db
from app.models import (
    Activity,
    Company,
    Contact,
    Email,
    Group,
    GroupMembership,
    HistoryEntry,
    Note,
    Opportunity,
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


@router.post("", response_model=ContactDetail, status_code=201)
def create_contact(payload: ContactCreate, db: Session = Depends(get_db)) -> ContactDetail:
    if payload.company_id and not db.get(Company, payload.company_id):
        raise HTTPException(status_code=400, detail="company_id does not exist")

    contact = Contact(
        id=uuid.uuid4(),
        source_db=MANUAL_SOURCE_DB,
        source_act_id=str(uuid.uuid4()),  # provenance columns are NOT NULL even for manual rows
        first_name=payload.first_name,
        last_name=payload.last_name,
        full_name=payload.full_name or " ".join(filter(None, [payload.first_name, payload.last_name])) or None,
        job_title=payload.job_title,
        department=payload.department,
        company_id=payload.company_id,
        custom_fields={},
    )
    db.add(contact)
    db.flush()

    if payload.email:
        db.add(Email(
            id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()),
            contact_id=contact.id, address=payload.email, is_primary=True,
        ))
    if payload.phone:
        db.add(Phone(
            id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()),
            contact_id=contact.id, number=payload.phone, is_primary=True,
        ))
    db.commit()
    return get_contact(contact.id, db)


@router.patch("/{contact_id}", response_model=ContactDetail)
def update_contact(contact_id: uuid.UUID, payload: ContactUpdate, db: Session = Depends(get_db)) -> ContactDetail:
    contact = db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    if payload.company_id and not db.get(Company, payload.company_id):
        raise HTTPException(status_code=400, detail="company_id does not exist")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    db.commit()
    return get_contact(contact_id, db)


@router.delete("/{contact_id}", status_code=204, response_model=None)
def delete_contact(contact_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    contact = db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # No cascade at the DB level (see contact_channel.py) - clean up every
    # row that actually has a foreign key into contacts.id ourselves, in one
    # transaction, before deleting the contact itself. Notes/History use
    # entity_id (not a real FK) so they can't block the delete, but we still
    # remove them - nothing should reference a contact that no longer exists.
    db.execute(GroupMembership.__table__.delete().where(GroupMembership.contact_id == contact_id))
    db.execute(Activity.__table__.update().where(Activity.contact_id == contact_id).values(contact_id=None))
    db.execute(Opportunity.__table__.update().where(Opportunity.contact_id == contact_id).values(contact_id=None))
    db.execute(Address.__table__.delete().where(Address.contact_id == contact_id))
    db.execute(Phone.__table__.delete().where(Phone.contact_id == contact_id))
    db.execute(Email.__table__.delete().where(Email.contact_id == contact_id))
    db.execute(Note.__table__.delete().where(Note.entity_type == "contact", Note.entity_id == contact_id))
    db.execute(HistoryEntry.__table__.delete().where(HistoryEntry.entity_type == "contact", HistoryEntry.entity_id == contact_id))
    db.delete(contact)
    db.commit()


@router.post("/{contact_id}/groups/{group_id}", status_code=204, response_model=None)
def add_to_group(contact_id: uuid.UUID, group_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    if not db.get(Contact, contact_id):
        raise HTTPException(status_code=404, detail="Contact not found")
    if not db.get(Group, group_id):
        raise HTTPException(status_code=404, detail="Group not found")

    exists = db.scalar(
        select(GroupMembership).where(GroupMembership.contact_id == contact_id, GroupMembership.group_id == group_id)
    )
    if not exists:
        db.add(GroupMembership(id=uuid.uuid4(), contact_id=contact_id, group_id=group_id))
        db.commit()


@router.delete("/{contact_id}/groups/{group_id}", status_code=204, response_model=None)
def remove_from_group(contact_id: uuid.UUID, group_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    db.execute(
        GroupMembership.__table__.delete().where(
            GroupMembership.contact_id == contact_id, GroupMembership.group_id == group_id
        )
    )
    db.commit()
