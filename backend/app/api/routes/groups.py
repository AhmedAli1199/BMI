from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.schemas import (
    ContactListItem,
    GroupCreate,
    GroupDetail,
    GroupListItem,
    GroupsPage,
    GroupUpdate,
)
from app.db.session import get_db
from app.models import Company, Contact, Group, GroupMembership

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=GroupsPage)
def list_groups(
    q: str | None = Query(None, description="Search by group name"),
    source_db: str | None = Query(None),
    root_group_id: uuid.UUID | None = Query(
        None, description="Restrict to this group plus every descendant subgroup - used for group-scoped user access"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> GroupsPage:
    member_count_subq = (
        select(func.count(GroupMembership.id))
        .where(GroupMembership.group_id == Group.id)
        .correlate(Group)
        .scalar_subquery()
    )

    stmt = select(Group, member_count_subq.label("member_count"))
    if source_db:
        stmt = stmt.where(Group.source_db == source_db)
    if root_group_id:
        subtree_ids = db.execute(
            text(
                "WITH RECURSIVE subtree AS ("
                "  SELECT id FROM groups WHERE id = :gid"
                "  UNION ALL"
                "  SELECT g.id FROM groups g JOIN subtree s ON g.parent_group_id = s.id"
                ") SELECT id FROM subtree"
            ),
            {"gid": str(root_group_id)},
        ).scalars().all()
        stmt = stmt.where(Group.id.in_(subtree_ids))
    if q:
        stmt = stmt.where(Group.name.ilike(f"%{q}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    # Order by hier_path (Act!'s own "Parent\Sub" tree path string) rather
    # than name alone, so a page of results groups every sub-group right
    # next to its parent instead of scattering them alphabetically -
    # hier_level then drives the frontend's indentation.
    stmt = stmt.order_by(Group.hier_path.asc().nulls_first(), Group.name.asc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = db.execute(stmt).all()

    items = [
        GroupListItem(
            id=g.id, source_db=g.source_db, name=g.name, description=g.description, member_count=count,
            hier_level=g.hier_level, parent_group_id=g.parent_group_id,
        )
        for g, count in rows
    ]
    return GroupsPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{group_id}", response_model=GroupDetail)
def get_group(group_id: uuid.UUID, db: Session = Depends(get_db)) -> GroupDetail:
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    members = db.execute(
        select(Contact, Company.name.label("company_name"))
        .join(GroupMembership, GroupMembership.contact_id == Contact.id)
        .outerjoin(Company, Contact.company_id == Company.id)
        .where(GroupMembership.group_id == group_id)
        .order_by(Contact.last_name.asc().nulls_last())
        .limit(500)
    ).all()

    return GroupDetail(
        id=group.id,
        source_db=group.source_db,
        name=group.name,
        description=group.description,
        parent_group_id=group.parent_group_id,
        members=[
            ContactListItem(
                id=c.id, source_db=c.source_db, full_name=c.full_name,
                first_name=c.first_name, last_name=c.last_name,
                job_title=c.job_title, company_id=c.company_id, company_name=company_name,
            )
            for c, company_name in members
        ],
    )


@router.post("", response_model=GroupDetail, status_code=201)
def create_group(payload: GroupCreate, db: Session = Depends(get_db)) -> GroupDetail:
    if payload.parent_group_id and not db.get(Group, payload.parent_group_id):
        raise HTTPException(status_code=400, detail="parent_group_id does not exist")

    group = Group(
        id=uuid.uuid4(),
        source_db="manual",
        source_act_id=str(uuid.uuid4()),
        name=payload.name,
        description=payload.description,
        parent_group_id=payload.parent_group_id,
        custom_fields={},
    )
    db.add(group)
    db.commit()
    return get_group(group.id, db)


@router.patch("/{group_id}", response_model=GroupDetail)
def update_group(group_id: uuid.UUID, payload: GroupUpdate, db: Session = Depends(get_db)) -> GroupDetail:
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if payload.parent_group_id:
        if payload.parent_group_id == group_id:
            raise HTTPException(status_code=400, detail="A group cannot be its own parent")
        if not db.get(Group, payload.parent_group_id):
            raise HTTPException(status_code=400, detail="parent_group_id does not exist")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(group, field, value)
    db.commit()
    return get_group(group_id, db)


@router.delete("/{group_id}", status_code=204, response_model=None)
def delete_group(group_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Child groups are detached, not deleted; memberships are removed.
    db.execute(Group.__table__.update().where(Group.parent_group_id == group_id).values(parent_group_id=None))
    db.execute(GroupMembership.__table__.delete().where(GroupMembership.group_id == group_id))
    db.delete(group)
    db.commit()
