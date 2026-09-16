from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.db.session import get_db
from app.models import Group, User, UserAccess

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginAccess(BaseModel):
    source_db: str
    group_id: str | None = None
    group_name: str | None = None


class LoginResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    access: list[LoginAccess] = []


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account has been disabled",
        )

    # Baked into the session JWT so every page/action can restrict what it
    # shows/does without a round-trip - see lib/session.ts and
    # app/roles.py. An admin gets no rows here (role alone grants
    # everything); the frontend must treat role == "admin" as unrestricted
    # rather than expecting access rows for them.
    rows = db.execute(
        select(UserAccess, Group.name)
        .outerjoin(Group, Group.id == UserAccess.group_id)
        .where(UserAccess.user_id == user.id)
    ).all()
    access = [
        LoginAccess(source_db=a.source_db, group_id=str(a.group_id) if a.group_id else None, group_name=group_name)
        for a, group_name in rows
    ]

    return LoginResponse(id=str(user.id), email=user.email, name=user.name, role=user.role, access=access)
