"""One definition of "a lookup" - Act!'s word for a filtered list of
contacts - shared by the contacts list, the record stepper, Excel export,
"add all to group" and mail-merge recipient selection, so every one of
them means exactly the same set of people in exactly the same order.

BMI look people up mainly by company, then first/last name and email;
city (really "where they are" - towns too) and country when targeting;
and sort the result by any column.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from app.models import Company, Contact, Email, GroupMembership
from app.models.contact_channel import Address

SORTS = ("name", "first_name", "company", "city", "country", "title", "email", "added")


@dataclass
class LookupFilters:
    q: str | None = None  # name, email, company or job title
    source_db: str | None = None
    company_id: uuid.UUID | None = None
    group_id: uuid.UUID | None = None
    company: str | None = None
    city: str | None = None
    country: str | None = None
    title: str | None = None
    contact_ids: list[uuid.UUID] = field(default_factory=list)
    sort: str = "name"
    desc: bool = False


def primary_email_expr():
    return (select(Email.address).where(Email.contact_id == Contact.id)
            .order_by(Email.is_primary.desc()).limit(1).correlate(Contact).scalar_subquery())


def primary_address_expr(column):
    return (select(column).where(Address.contact_id == Contact.id)
            .order_by(Address.is_primary.desc()).limit(1).correlate(Contact).scalar_subquery())


def _group_subtree(db: Session, group_id: uuid.UUID) -> list:
    # Groups are hierarchical - a group covers its subfolders too, same as
    # Act!'s own group view.
    return db.execute(text(
        "WITH RECURSIVE subtree AS (SELECT id FROM groups WHERE id = :gid "
        "UNION ALL SELECT g.id FROM groups g JOIN subtree s ON g.parent_group_id = s.id) SELECT id FROM subtree"
    ), {"gid": str(group_id)}).scalars().all()


def apply_filters(db: Session, stmt, f: LookupFilters):
    if f.source_db:
        stmt = stmt.where(Contact.source_db == f.source_db)
    if f.company_id:
        stmt = stmt.where(Contact.company_id == f.company_id)
    if f.group_id:
        stmt = stmt.where(Contact.id.in_(
            select(GroupMembership.contact_id).where(GroupMembership.group_id.in_(_group_subtree(db, f.group_id)))))
    if f.contact_ids:
        stmt = stmt.where(Contact.id.in_(f.contact_ids))
    if f.q and f.q.strip():
        like = f"%{f.q.strip()}%"
        stmt = stmt.where(or_(
            Contact.full_name.ilike(like), Contact.first_name.ilike(like), Contact.last_name.ilike(like),
            Contact.job_title.ilike(like), Contact.company_name_freetext.ilike(like),
            Contact.company_id.in_(select(Company.id).where(Company.name.ilike(like))),
            Contact.id.in_(select(Email.contact_id).where(Email.address.ilike(like))),
        ))
    if f.company and f.company.strip():
        like = f"%{f.company.strip()}%"
        stmt = stmt.where(or_(Contact.company_name_freetext.ilike(like),
                              Contact.company_id.in_(select(Company.id).where(Company.name.ilike(like)))))
    if f.city and f.city.strip():
        stmt = stmt.where(Contact.id.in_(select(Address.contact_id).where(Address.city.ilike(f"%{f.city.strip()}%"))))
    if f.country and f.country.strip():
        stmt = stmt.where(Contact.id.in_(select(Address.contact_id).where(Address.country.ilike(f"%{f.country.strip()}%"))))
    if f.title and f.title.strip():
        stmt = stmt.where(Contact.job_title.ilike(f"%{f.title.strip()}%"))
    return stmt


def apply_sort(stmt, f: LookupFilters, company_name_col=None):
    """Order by the chosen column, always tie-broken by last then first
    name so equal values (every contact in "London") read alphabetically."""
    key = {
        "first_name": Contact.first_name,
        "company": company_name_col if company_name_col is not None else
        select(Company.name).where(Company.id == Contact.company_id).correlate(Contact).scalar_subquery(),
        "city": primary_address_expr(Address.city),
        "country": primary_address_expr(Address.country),
        "title": Contact.job_title,
        "email": primary_email_expr(),
        "added": Contact.created_at,
    }.get(f.sort, Contact.last_name)
    first = key.desc().nulls_last() if f.desc else key.asc().nulls_last()
    return stmt.order_by(first, Contact.last_name.asc().nulls_last(), Contact.first_name.asc().nulls_last(), Contact.id)


def lookup_ids(db: Session, f: LookupFilters, limit: int | None = None) -> list[uuid.UUID]:
    stmt = apply_sort(apply_filters(db, select(Contact.id), f), f)
    if limit:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt).all())
