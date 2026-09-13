from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, Query

from app.api.schemas import (
    DashboardStats,
    RecentCompany,
    RecentContact,
    SourceBreakdown,
    TopCompany,
)
from app.db.session import get_db
from app.models import Company, Contact, Group

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

RECENT_LIMIT = 6
TOP_COMPANIES_LIMIT = 6


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    source_db: str | None = Query(None, description="Restrict every figure to one publication's data"),
    db: Session = Depends(get_db),
) -> DashboardStats:
    contact_filter = [Contact.source_db == source_db] if source_db else []
    company_filter = [Company.source_db == source_db] if source_db else []
    group_filter = [Group.source_db == source_db] if source_db else []

    total_contacts = db.scalar(select(func.count()).select_from(Contact).where(*contact_filter)) or 0
    total_companies = db.scalar(select(func.count()).select_from(Company).where(*company_filter)) or 0
    total_groups = db.scalar(select(func.count()).select_from(Group).where(*group_filter)) or 0

    contacts_by_source = [
        SourceBreakdown(source_db=s, count=count)
        for s, count in db.execute(
            select(Contact.source_db, func.count())
            .where(*contact_filter)
            .group_by(Contact.source_db)
            .order_by(func.count().desc())
        ).all()
    ]
    companies_by_source = [
        SourceBreakdown(source_db=s, count=count)
        for s, count in db.execute(
            select(Company.source_db, func.count())
            .where(*company_filter)
            .group_by(Company.source_db)
            .order_by(func.count().desc())
        ).all()
    ]

    recent_contacts_rows = db.execute(
        select(Contact, Company.name.label("company_name"))
        .outerjoin(Company, Contact.company_id == Company.id)
        .where(*contact_filter)
        .order_by(Contact.created_at.desc())
        .limit(RECENT_LIMIT)
    ).all()
    recent_contacts = [
        RecentContact(
            id=c.id,
            full_name=c.full_name,
            first_name=c.first_name,
            last_name=c.last_name,
            job_title=c.job_title,
            company_id=c.company_id,
            company_name=company_name,
            created_at=c.created_at,
        )
        for c, company_name in recent_contacts_rows
    ]

    recent_companies_rows = db.scalars(
        select(Company).where(*company_filter).order_by(Company.created_at.desc()).limit(RECENT_LIMIT)
    ).all()
    recent_companies = [
        RecentCompany(id=c.id, name=c.name, industry=c.industry, created_at=c.created_at)
        for c in recent_companies_rows
    ]

    # Contacts counted per company must respect the same publication filter -
    # otherwise switching to one title would still rank companies by their
    # total contact count across every title.
    contact_count_subq = (
        select(func.count(Contact.id))
        .where(Contact.company_id == Company.id, *contact_filter)
        .correlate(Company)
        .scalar_subquery()
    )
    top_companies_rows = db.execute(
        select(Company, contact_count_subq.label("contact_count"))
        .where(*company_filter)
        .order_by(contact_count_subq.desc())
        .limit(TOP_COMPANIES_LIMIT)
    ).all()
    top_companies = [
        TopCompany(id=c.id, name=c.name, industry=c.industry, contact_count=count)
        for c, count in top_companies_rows
        if count > 0
    ]

    return DashboardStats(
        total_contacts=total_contacts,
        total_companies=total_companies,
        total_groups=total_groups,
        contacts_by_source=contacts_by_source,
        companies_by_source=companies_by_source,
        recent_contacts=recent_contacts,
        recent_companies=recent_companies,
        top_companies=top_companies,
    )
