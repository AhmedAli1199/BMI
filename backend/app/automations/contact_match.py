"""Shared "find the one real contact behind this email address" helper -
used by every mailbox-driven automation (bounce_handling.py, email_summary.py,
and anything else that needs to turn a raw From/To address into a Contact).
Kept in one place so the ambiguity rule below is enforced identically
everywhere, rather than each automation re-deciding what to do about a
shared inbox or a duplicate email on file.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Contact, Email


def find_contact_by_email(db: Session, email: str | None) -> Contact | None:
    """Only returns a match when it's unambiguous - two different contacts
    sharing one email address (a shared team inbox, a couple with the same
    address on file) is real in this data, and guessing wrong here means
    silently attributing a mailbox signal to the wrong person. Ambiguous or
    zero-match both come back None; callers route that to a manual-pick
    path instead of the confident one."""
    if not email:
        return None
    matches = db.scalars(
        select(Contact)
        .join(Email, Email.contact_id == Contact.id)
        .where(func.lower(Email.address) == email.lower())
        .distinct()
    ).all()
    return matches[0] if len(matches) == 1 else None
