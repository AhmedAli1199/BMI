"""Who may approve bookings, and when a booking is locked.

Accounts people (users with can_approve_bookings, e.g. Samantha) are the only ones who can:
  - pass or send back the accounts check on a booking (review kind "order_check");
  - change a booking once it's been checked - everyone else sends a change request (review kind
    "booking_change") that an accounts person approves or declines.

Until at least one person has the Accounts permission, nothing is locked and administrators/data managers
handle the checks as before - so switching this on never leaves bookings stuck with nobody to approve them.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automations import runtime_settings
from app.models import SalesDeal, User
from app.roles import CAN_USE_AUTOMATIONS


def accounts_people(db: Session) -> list[User]:
    return db.scalars(select(User).where(User.can_approve_bookings.is_(True), User.is_active.is_(True))).all()


def accounts_assigned(db: Session) -> bool:
    return bool(db.scalar(select(User.id).where(User.can_approve_bookings.is_(True), User.is_active.is_(True)).limit(1)))


def can_approve(db: Session, user_id: uuid.UUID | None, role: str | None = None) -> bool:
    """May this person pass booking checks and approve changes?"""
    user = db.get(User, user_id) if user_id else None
    if accounts_assigned(db):
        return bool(user and user.can_approve_bookings)
    role = role or (user.role if user else None)
    return role in CAN_USE_AUTOMATIONS or user_id is None   # nobody assigned yet: managers, as before


def locked(db: Session, d: SalesDeal) -> bool:
    """A checked booking can only be changed by accounts (others request the change)."""
    return bool(d.checked_at and accounts_assigned(db) and runtime_settings.get_bool(db, "orders_lock_after_check"))
