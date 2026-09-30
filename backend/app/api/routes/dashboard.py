from __future__ import annotations

import uuid

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, Query

from app.api.schemas import (
    DashboardStats,
    DataHealthMetric,
    DataHealthStats,
    RecentCompany,
    RecentContact,
    SourceBreakdown,
    TopCompany,
)
from app.db.session import get_db
from app.models import Company, Contact, Email, Group, GroupMembership, HistoryEntry, Note, Phone, ReviewQueueItem

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

RECENT_LIMIT = 6
TOP_COMPANIES_LIMIT = 6

# The automation kinds that represent a data-quality problem rather than a
# sales workflow (see frontend/src/lib/automation-style.tsx's
# categoryForKind "hygiene" bucket, mirrored here so the Data Health page
# and the Automations Hub agree on what counts as hygiene).
_HYGIENE_KINDS = {
    "ooo_ambiguous": "Ambiguous out-of-office replies",
    "departure_unconfirmed": "Unconfirmed departures",
    "duplicate_contact": "Possible duplicate contacts",
    "bounce_uncertain": "Uncertain bounces",
    "bounce_unmatched": "Unmatched bounces",
    "returned_copy": "Returned copy / undeliverable mail",
}


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    source_db: str | None = Query(None, description="Restrict every figure to one publication's data"),
    group_id: uuid.UUID | None = Query(
        None, description="Further restrict contact figures to this group's subtree - for a group-scoped user's session"
    ),
    recent_activity_sort: str = Query(
        "record_edit",
        description="'record_edit' (default) or 'engagement' - see app/preferences.py's recent_activity_sort def",
    ),
    db: Session = Depends(get_db),
) -> DashboardStats:
    contact_filter = [Contact.source_db == source_db] if source_db else []
    company_filter = [Company.source_db == source_db] if source_db else []
    group_filter = [Group.source_db == source_db] if source_db else []

    # Companies/groups aren't group-scoped (a group is a contact-level
    # concept - see app/models/user_access.py's docstring), so a
    # group-scoped session only tightens the contact-level figures here.
    if group_id:
        subtree_ids = db.execute(
            text(
                "WITH RECURSIVE subtree AS ("
                "  SELECT id FROM groups WHERE id = :gid"
                "  UNION ALL"
                "  SELECT g.id FROM groups g JOIN subtree s ON g.parent_group_id = s.id"
                ") SELECT id FROM subtree"
            ),
            {"gid": str(group_id)},
        ).scalars().all()
        contact_filter.append(
            Contact.id.in_(select(GroupMembership.contact_id).where(GroupMembership.group_id.in_(subtree_ids)))
        )

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

    # "Recently active" has to mean something real, and there isn't one
    # universally-right answer - see app/preferences.py's recent_activity_sort
    # def for the two options this implements:
    #
    # "record_edit" (default): Act!'s own act_edited_at/act_created_at,
    # i.e. when the RECORD ITSELF was last touched in Act! (any field
    # edit) - not when someone actually engaged with the person. Never
    # empty (falls back to our own created_at for a manually-created CRM
    # contact), but can rank a record with zero notes above one with real
    # history behind it, purely from a data edit.
    #
    # "engagement": the latest Note or logged History entry against the
    # record - genuine engagement, but deliberately has NO fallback: a
    # contact/company with no notes or history yet simply doesn't appear
    # here rather than silently reverting to the record-edit date (which
    # would just re-introduce the same "looks active but isn't" problem).
    if recent_activity_sort == "engagement":
        contact_activity_at = func.greatest(
            select(func.max(Note.act_created_at))
            .where(Note.entity_type == "contact", Note.entity_id == Contact.id)
            .correlate(Contact)
            .scalar_subquery(),
            select(func.max(HistoryEntry.occurred_at))
            .where(HistoryEntry.entity_type == "contact", HistoryEntry.entity_id == Contact.id)
            .correlate(Contact)
            .scalar_subquery(),
        )
        company_activity_at = func.greatest(
            select(func.max(Note.act_created_at))
            .where(Note.entity_type == "company", Note.entity_id == Company.id)
            .correlate(Company)
            .scalar_subquery(),
            select(func.max(HistoryEntry.occurred_at))
            .where(HistoryEntry.entity_type == "company", HistoryEntry.entity_id == Company.id)
            .correlate(Company)
            .scalar_subquery(),
        )
        contact_activity_filter = [contact_activity_at.isnot(None)]
        company_activity_filter = [company_activity_at.isnot(None)]
    else:
        contact_activity_at = func.coalesce(Contact.act_edited_at, Contact.act_created_at, Contact.created_at)
        company_activity_at = func.coalesce(Company.act_edited_at, Company.act_created_at, Company.created_at)
        contact_activity_filter = []
        company_activity_filter = []

    recent_contacts_rows = db.execute(
        select(Contact, Company.name.label("company_name"), contact_activity_at.label("activity_at"))
        .outerjoin(Company, Contact.company_id == Company.id)
        .where(*contact_filter, *contact_activity_filter)
        .order_by(contact_activity_at.desc())
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
            created_at=activity_at,
        )
        for c, company_name, activity_at in recent_contacts_rows
    ]

    recent_companies_rows = db.execute(
        select(Company, company_activity_at.label("activity_at"))
        .where(*company_filter, *company_activity_filter)
        .order_by(company_activity_at.desc())
        .limit(RECENT_LIMIT)
    ).all()
    recent_companies = [
        RecentCompany(id=c.id, name=c.name, industry=c.industry, created_at=activity_at)
        for c, activity_at in recent_companies_rows
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


@router.get("/data-health", response_model=DataHealthStats)
def get_data_health(
    source_db: str | None = Query(None, description="Restrict every figure to one publication's data"),
    db: Session = Depends(get_db),
) -> DataHealthStats:
    """Data-quality picture for the BMI Brain Data Health page: record
    completeness (missing email/phone/industry) plus the pending count of
    every automation that exists specifically to fix bad data (see
    _HYGIENE_KINDS). Company-only ("keep things simple" - see
    contact_channel.py) figures aren't group-scoped, matching /stats."""
    contact_filter = [Contact.source_db == source_db] if source_db else []
    company_filter = [Company.source_db == source_db] if source_db else []

    total_contacts = db.scalar(select(func.count()).select_from(Contact).where(*contact_filter)) or 0
    total_companies = db.scalar(select(func.count()).select_from(Company).where(*company_filter)) or 0

    contacts_missing_email = db.scalar(
        select(func.count())
        .select_from(Contact)
        .where(*contact_filter, ~Contact.id.in_(select(Email.contact_id).where(Email.contact_id.isnot(None))))
    ) or 0
    contacts_missing_phone = db.scalar(
        select(func.count())
        .select_from(Contact)
        .where(*contact_filter, ~Contact.id.in_(select(Phone.contact_id).where(Phone.contact_id.isnot(None))))
    ) or 0
    companies_missing_industry = db.scalar(
        select(func.count())
        .select_from(Company)
        .where(*company_filter, (Company.industry.is_(None)) | (Company.industry == ""))
    ) or 0
    unsubscribed_contacts = db.scalar(
        select(func.count()).select_from(Contact).where(*contact_filter, Contact.is_unsubscribed.is_(True))
    ) or 0

    hygiene_filter = [ReviewQueueItem.source_db == source_db] if source_db else []
    hygiene_rows = dict(
        db.execute(
            select(ReviewQueueItem.kind, func.count())
            .where(
                ReviewQueueItem.status == "pending",
                ReviewQueueItem.kind.in_(_HYGIENE_KINDS.keys()),
                *hygiene_filter,
            )
            .group_by(ReviewQueueItem.kind)
        ).all()
    )

    metrics = [
        DataHealthMetric(
            key="missing_email",
            label="Contacts without an email address",
            description="Can't be reached for renewals, follow-ups, or automated bounce/OOO detection.",
            count=contacts_missing_email,
            total=total_contacts,
            entity_type="contact",
        ),
        DataHealthMetric(
            key="missing_phone",
            label="Contacts without a phone number",
            description="No fallback channel when email goes unanswered or bounces.",
            count=contacts_missing_phone,
            total=total_contacts,
            entity_type="contact",
        ),
        DataHealthMetric(
            key="missing_industry",
            label="Companies without an industry",
            description="Weakens segmentation, targeting, and the Top Companies breakdown.",
            count=companies_missing_industry,
            total=total_companies,
            entity_type="company",
        ),
        DataHealthMetric(
            key="unsubscribed",
            label="Unsubscribed / hard-bounced contacts",
            description="Confirmed undeliverable by the bounce-handling automation - excluded from outreach.",
            count=unsubscribed_contacts,
            total=total_contacts,
            entity_type="contact",
        ),
    ] + [
        DataHealthMetric(
            key=kind,
            label=label,
            description="Flagged by the automations engine and waiting for a human decision.",
            count=hygiene_rows.get(kind, 0),
            total=total_contacts,
            review_kind=kind,
        )
        for kind, label in _HYGIENE_KINDS.items()
    ]

    return DataHealthStats(total_contacts=total_contacts, total_companies=total_companies, metrics=metrics)
