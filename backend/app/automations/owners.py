"""Whose Review Queue a card about a client belongs in.

A card made from someone's email (a promised callback, a personal touchpoint) is theirs: it goes to the person whose
inbox it was read from. Otherwise it goes to whoever made the activity, then whoever looks after the contact (their
Act! record manager), then the company. With nobody to give it to, only administrators see it.
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Company, Contact, User


def owner_for(db: Session, *, mailbox: str | None = None, contact: Contact | None = None,
              company: Company | None = None, made_by: uuid.UUID | None = None) -> uuid.UUID | None:
    if mailbox:
        uid = db.scalar(select(User.id).where(func.lower(User.email) == mailbox.lower(), User.is_active.is_(True)))
        if uid:
            return uid
    if made_by:
        return made_by
    if contact is not None and contact.owner_user_id:
        return contact.owner_user_id
    if company is None and contact is not None and contact.company_id:
        company = db.get(Company, contact.company_id)
    if company is not None and company.owner_user_id:
        return company.owner_user_id
    return None
