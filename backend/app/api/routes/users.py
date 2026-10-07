from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import RoleDefOut, UserAccessOut, UserCreate, UserOut, UserUpdate
from app.core.security import hash_password
from app.db.session import get_db
from app.models import Group, Publication, SalesRep, User, UserAccess
from app.roles import ALL_ROLES, ROLE_DEFS

router = APIRouter(tags=["users"])


def _validate_access(db: Session, access: list) -> None:
    known_slugs = {p.slug for p in db.execute(select(Publication)).scalars().all()}
    for a in access:
        if a.source_db not in known_slugs:
            raise HTTPException(status_code=400, detail=f"Unknown database: {a.source_db!r}")
        if a.group_id:
            group = db.get(Group, a.group_id)
            if not group:
                raise HTTPException(status_code=400, detail=f"Group not found: {a.group_id}")
            if group.source_db != a.source_db:
                raise HTTPException(
                    status_code=400,
                    detail=f"Group {group.name!r} belongs to {group.source_db!r}, not {a.source_db!r}",
                )


def _user_out(db: Session, user: User) -> UserOut:
    rows = db.execute(
        select(UserAccess, Group.name)
        .outerjoin(Group, Group.id == UserAccess.group_id)
        .where(UserAccess.user_id == user.id)
    ).all()
    access = [
        UserAccessOut(source_db=a.source_db, group_id=a.group_id, group_name=group_name)
        for a, group_name in rows
    ]
    rep = db.scalars(select(SalesRep).where(SalesRep.user_id == user.id)).first()
    return UserOut(id=user.id, email=user.email, name=user.name, role=user.role, is_active=user.is_active, access=access,
                   sales_rep_id=rep.id if rep else None, sales_rep_code=rep.code if rep else None)


def _set_sales_rep(db: Session, user: User, rep_id: uuid.UUID | None) -> None:
    """One login per salesperson: links this login to the rep (unlinking any other rep it had)."""
    for r in db.scalars(select(SalesRep).where(SalesRep.user_id == user.id)):
        if r.id != rep_id:
            r.user_id = None
    if rep_id:
        rep = db.get(SalesRep, rep_id)
        if not rep:
            raise HTTPException(status_code=400, detail="Unknown salesperson")
        if rep.user_id and rep.user_id != user.id:
            other = db.get(User, rep.user_id)
            raise HTTPException(status_code=409, detail=f"{rep.code} is already linked to {other.name if other else 'another login'} - unlink it there first.")
        rep.user_id = user.id


@router.get("/roles", response_model=list[RoleDefOut])
def list_roles() -> list[RoleDefOut]:
    """Every role and what it grants - drives the admin UI's role picker,
    same generic-registry pattern as /api/settings/definitions."""
    return [RoleDefOut(value=r.value, label=r.label, description=r.description) for r in ROLE_DEFS]


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list[UserOut]:
    users = db.execute(select(User).order_by(User.name.asc())).scalars().all()
    return [_user_out(db, u) for u in users]


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    if payload.role not in ALL_ROLES:
        raise HTTPException(status_code=400, detail=f"Unknown role: {payload.role!r} - choose one of {ALL_ROLES}")
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(status_code=409, detail=f"A user with email {payload.email!r} already exists.")
    _validate_access(db, payload.access)

    user = User(
        id=uuid.uuid4(),
        email=payload.email.lower(),
        name=payload.name.strip(),
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.flush()
    for a in payload.access:
        db.add(UserAccess(id=uuid.uuid4(), user_id=user.id, source_db=a.source_db, group_id=a.group_id))
    if payload.sales_rep_id:
        _set_sales_rep(db, user, payload.sales_rep_id)
    db.commit()
    return _user_out(db, user)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: uuid.UUID, payload: UserUpdate, db: Session = Depends(get_db)) -> UserOut:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.role is not None:
        if payload.role not in ALL_ROLES:
            raise HTTPException(status_code=400, detail=f"Unknown role: {payload.role!r} - choose one of {ALL_ROLES}")
        user.role = payload.role
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password:
        user.hashed_password = hash_password(payload.password)
    if payload.access is not None:
        _validate_access(db, payload.access)
        db.execute(UserAccess.__table__.delete().where(UserAccess.user_id == user.id))
        for a in payload.access:
            db.add(UserAccess(id=uuid.uuid4(), user_id=user.id, source_db=a.source_db, group_id=a.group_id))
    if "sales_rep_id" in payload.model_fields_set:
        _set_sales_rep(db, user, payload.sales_rep_id)

    db.commit()
    return _user_out(db, user)
