"""Company and contact addresses (Craig, feedback #5 and #9).

A company's address is for invoicing and the office. A contact keeps their own address (people working from home get
the magazine there), so nothing is copied without asking - except one thing: when a company moves, the contacts whose
address was the same as the company's old one move with it. Anyone with a different address is left alone.
"""
from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Contact
from app.models.contact_channel import Address
from app.services.field_audit import describe_channel, record_channel_change

FIELDS = ("line1", "line2", "line3", "city", "state", "postal_code", "country")


def _norm(v: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (v or "").lower())


def key(a: Address | dict) -> tuple:
    get = (lambda f: a.get(f)) if isinstance(a, dict) else (lambda f: getattr(a, f))
    return tuple(_norm(get(f)) for f in FIELDS)


def snapshot(a: Address) -> dict:
    return {f: getattr(a, f) for f in FIELDS}


def move_contacts_with_company(db: Session, company_id: uuid.UUID, old: dict, new: Address,
                               changed_by: uuid.UUID | None) -> int:
    """Contacts at this company whose address matched the company's old address get the new one. Returns how many."""
    old_key = key(old)
    if not any(old_key) or old_key == key(new):
        return 0
    rows = db.scalars(select(Address).join(Contact, Contact.id == Address.contact_id)
                      .where(Contact.company_id == company_id)).all()
    moved = 0
    for a in rows:
        if key(a) != old_key:
            continue
        before = describe_channel(a)
        for f in FIELDS:
            setattr(a, f, getattr(new, f))
        record_channel_change(db, owner_field="contact_id", owner_id=a.contact_id, row=a, before=before,
                              after=describe_channel(a), changed_by_user_id=changed_by)
        moved += 1
    return moved


def company_address(db: Session, company_id: uuid.UUID) -> Address | None:
    rows = db.scalars(select(Address).where(Address.company_id == company_id)).all()
    return next((a for a in rows if a.is_primary), rows[0] if rows else None)


def use_company_address(db: Session, contact: Contact, changed_by: uuid.UUID | None) -> Address | None:
    """Copy the company's address onto the contact: their main address is replaced, or one is added."""
    if not contact.company_id:
        return None
    src = company_address(db, contact.company_id)
    if not src:
        return None
    rows = db.scalars(select(Address).where(Address.contact_id == contact.id)).all()
    mine = next((a for a in rows if a.is_primary), rows[0] if rows else None)
    if mine:
        before = describe_channel(mine)
        for f in FIELDS:
            setattr(mine, f, getattr(src, f))
        record_channel_change(db, owner_field="contact_id", owner_id=contact.id, row=mine, before=before,
                              after=describe_channel(mine), changed_by_user_id=changed_by)
        return mine
    from app.api.schemas import MANUAL_SOURCE_DB
    mine = Address(id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()), contact_id=contact.id, type_label=src.type_label or "Business", is_primary=True,
                   **{f: getattr(src, f) for f in FIELDS})
    db.add(mine)
    db.flush()
    record_channel_change(db, owner_field="contact_id", owner_id=contact.id, row=mine, before=None,
                          after=describe_channel(mine), changed_by_user_id=changed_by)
    return mine
