from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas import (
    MANUAL_SOURCE_DB,
    AddressOut,
    CompaniesPage,
    CompanyCreate,
    CompanyDetail,
    CompanyListItem,
    CompanyUpdate,
    ContactListItem,
    EmailOut,
    NoteOut,
    PhoneOut,
)
from app.db.session import get_db
from app.models import Activity, Company, Contact, Email, HistoryEntry, Note, Opportunity
from app.models.contact_channel import Address, Phone

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=CompaniesPage)
def list_companies(
    q: str | None = Query(None, description="Search by company name"),
    source_db: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> CompaniesPage:
    contact_count_subq = (
        select(func.count(Contact.id))
        .where(Contact.company_id == Company.id)
        .correlate(Company)
        .scalar_subquery()
    )

    stmt = select(Company, contact_count_subq.label("contact_count"))
    if source_db:
        stmt = stmt.where(Company.source_db == source_db)
    if q:
        stmt = stmt.where(Company.name.ilike(f"%{q}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    stmt = stmt.order_by(Company.name.asc()).offset((page - 1) * page_size).limit(page_size)
    rows = db.execute(stmt).all()

    items = [
        CompanyListItem(
            id=company.id,
            source_db=company.source_db,
            name=company.name,
            industry=company.industry,
            category=company.category,
            contact_count=contact_count,
        )
        for company, contact_count in rows
    ]
    return CompaniesPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{company_id}", response_model=CompanyDetail)
def get_company(company_id: uuid.UUID, db: Session = Depends(get_db)) -> CompanyDetail:
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    addresses = db.scalars(select(Address).where(Address.company_id == company_id)).all()
    phones = db.scalars(select(Phone).where(Phone.company_id == company_id)).all()
    emails = db.scalars(select(Email).where(Email.company_id == company_id)).all()
    contacts = db.scalars(
        select(Contact).where(Contact.company_id == company_id)
        .order_by(Contact.last_name.asc().nulls_last())
        .limit(200)
    ).all()
    notes = db.scalars(
        select(Note).where(Note.entity_type == "company", Note.entity_id == company_id)
        .order_by(Note.act_created_at.desc().nulls_last())
        .limit(100)
    ).all()

    return CompanyDetail(
        id=company.id,
        source_db=company.source_db,
        source_act_id=company.source_act_id,
        name=company.name,
        description=company.description,
        industry=company.industry,
        category=company.category,
        territory=company.territory,
        region=company.region,
        website=company.website,
        num_employees=company.num_employees,
        custom_fields=company.custom_fields,
        addresses=[AddressOut.model_validate(a) for a in addresses],
        phones=[PhoneOut.model_validate(p) for p in phones],
        emails=[EmailOut.model_validate(e) for e in emails],
        contacts=[
            ContactListItem(
                id=c.id, source_db=c.source_db, full_name=c.full_name,
                first_name=c.first_name, last_name=c.last_name,
                job_title=c.job_title, company_id=c.company_id, company_name=company.name,
            )
            for c in contacts
        ],
        notes=[NoteOut.model_validate(n) for n in notes],
    )


@router.post("", response_model=CompanyDetail, status_code=201)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)) -> CompanyDetail:
    company = Company(
        id=uuid.uuid4(),
        source_db=MANUAL_SOURCE_DB,
        source_act_id=str(uuid.uuid4()),
        name=payload.name,
        industry=payload.industry,
        category=payload.category,
        website=payload.website,
        custom_fields={},
    )
    db.add(company)
    db.commit()
    return get_company(company.id, db)


@router.patch("/{company_id}", response_model=CompanyDetail)
def update_company(company_id: uuid.UUID, payload: CompanyUpdate, db: Session = Depends(get_db)) -> CompanyDetail:
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    db.commit()
    return get_company(company_id, db)


@router.delete("/{company_id}", status_code=204, response_model=None)
def delete_company(company_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Nothing that merely references this company gets deleted with it -
    # contacts, activities, opportunities and any child company are just
    # detached (their FK is nullable). Everything with a real FK straight
    # into companies.id needs handling before the delete, same reasoning
    # as delete_contact.
    db.execute(Contact.__table__.update().where(Contact.company_id == company_id).values(company_id=None))
    db.execute(Company.__table__.update().where(Company.parent_company_id == company_id).values(parent_company_id=None))
    db.execute(Activity.__table__.update().where(Activity.company_id == company_id).values(company_id=None))
    db.execute(Opportunity.__table__.update().where(Opportunity.company_id == company_id).values(company_id=None))
    db.execute(Address.__table__.delete().where(Address.company_id == company_id))
    db.execute(Phone.__table__.delete().where(Phone.company_id == company_id))
    db.execute(Email.__table__.delete().where(Email.company_id == company_id))
    db.execute(Note.__table__.delete().where(Note.entity_type == "company", Note.entity_id == company_id))
    db.execute(HistoryEntry.__table__.delete().where(HistoryEntry.entity_type == "company", HistoryEntry.entity_id == company_id))
    db.delete(company)
    db.commit()
