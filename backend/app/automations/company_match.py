"""Best-effort "which company is this inbound sender probably from"
guess for SALES-011 - a suggestion the reviewer confirms or overrides,
never a write on its own. See app/automations/inbound_capture.py.
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Company, Contact, Email

# Free/consumer providers never imply a company - an inbound lead from
# @gmail.com tells us nothing about who they work for.
_FREE_EMAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "yahoo.com",
    "yahoo.co.uk", "icloud.com", "aol.com", "live.com", "me.com", "msn.com",
}


def domain_of(email: str | None) -> str:
    if not email or "@" not in email:
        return ""
    return email.rsplit("@", 1)[-1].strip().lower()


def suggest_company(db: Session, source_db: str, sender_email: str | None) -> Company | None:
    """The company most of this domain's existing contacts (in the same
    source database) already belong to, if any - a majority-domain-match
    guess, not a certainty. Returns None for a free-email domain or a
    domain nobody else in the CRM shares."""
    domain = domain_of(sender_email)
    if not domain or domain in _FREE_EMAIL_DOMAINS:
        return None

    row = (
        db.query(Contact.company_id, func.count().label("n"))
        .join(Email, Email.contact_id == Contact.id)
        .filter(
            Contact.source_db == source_db,
            Contact.company_id.isnot(None),
            func.lower(Email.address).like(f"%@{domain}"),
        )
        .group_by(Contact.company_id)
        .order_by(func.count().desc())
        .first()
    )
    return db.get(Company, row[0]) if row else None
