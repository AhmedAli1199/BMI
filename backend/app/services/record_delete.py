"""Deleting and merging CRM records properly: every row that points at the record is either removed (when it
only describes that record) or moved/unlinked, in the caller's transaction, so nothing is left dangling and
nothing fails half way. Used by the contact and company Delete buttons and Merge companies."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import or_, select, text, update
from sqlalchemy.orm import Session

from app.models import Activity, Company, Contact, Email, GroupMembership, HistoryEntry, Note, Opportunity
from app.models.activity_link import ActivityCompany, ActivityContact
from app.models.contact import ContactCompanyLink
from app.models.contact_channel import Address, Phone
from app.models.email_signal import EmailSignal
from app.models.email_thread_state import EmailThreadState
from app.api.schemas import MANUAL_SOURCE_DB


def delete_contact_rows(db: Session, contact: Contact) -> None:
    """Removes a contact with everything that only describes them; activities and deals stay, unlinked."""
    cid = contact.id
    for model in (ActivityContact, ContactCompanyLink, EmailSignal, EmailThreadState, GroupMembership, Address, Phone, Email):
        db.execute(model.__table__.delete().where(model.contact_id == cid))
    db.execute(update(Activity).where(Activity.contact_id == cid).values(contact_id=None))
    db.execute(update(Opportunity).where(Opportunity.contact_id == cid).values(contact_id=None))
    db.execute(Note.__table__.delete().where(Note.entity_type == "contact", Note.entity_id == cid))
    db.execute(HistoryEntry.__table__.delete().where(HistoryEntry.entity_type == "contact", HistoryEntry.entity_id == cid))
    db.delete(contact)


# ---- companies ---------------------------------------------------------------------

_SUFFIX = re.compile(r"\b(the|ltd|limited|plc|inc|incorporated|llc|llp|co|company|corp|corporation|group|uk|gmbh|sa|srl|bv)\b")


def name_key(name: str | None) -> str:
    """"Acme Travel Ltd." and "ACME travel" compare equal."""
    s = re.sub(r"[^a-z0-9 ]+", " ", (name or "").lower().replace("&", " and "))
    return " ".join(_SUFFIX.sub(" ", s).split())


def similar_companies(db: Session, name: str, *, visible=None, exclude: uuid.UUID | None = None, limit: int = 6) -> list[dict]:
    """Companies whose name is the same or close to `name` (spelling, Ltd/Limited, punctuation), best first."""
    key = name_key(name)
    if len(key) < 2:
        return []
    stmt = (select(Company.id, Company.name, Company.source_db, text("similarity(lower(companies.name), lower(:n)) AS score"))
            .where(or_(text("similarity(lower(companies.name), lower(:n)) > 0.45"), Company.name.ilike(f"%{key}%")))
            .order_by(text("score DESC")).limit(40))
    if visible is not None:
        stmt = stmt.where(visible)
    if exclude:
        stmt = stmt.where(Company.id != exclude)
    rows = db.execute(stmt, {"n": name.strip()}).all()
    found = []
    for cid, cname, sdb, score in rows:
        k = name_key(cname)
        same = k == key
        if not same and score < 0.45 and not (k.startswith(key) or key.startswith(k)):
            continue
        found.append({"id": cid, "name": cname, "source_db": sdb, "exact": same, "score": float(score or 0)})
    found.sort(key=lambda f: (not f["exact"], -f["score"]))
    found = found[:limit]
    if found:
        counts = dict(db.execute(select(Contact.company_id, text("count(*)")).where(Contact.company_id.in_([f["id"] for f in found]))
                                 .group_by(Contact.company_id)).all())
        for f in found:
            f["contacts"] = int(counts.get(f["id"], 0))
    return found


def _bookings(db: Session, company_id: uuid.UUID) -> int:
    from app.models import SalesOrder
    return db.scalar(select(text("count(*)")).select_from(SalesOrder).where(SalesOrder.company_id == company_id)) or 0


def company_usage(db: Session, company_id: uuid.UUID) -> dict:
    from app.models import SalesDeal
    return {
        "contacts": db.scalar(select(text("count(*)")).select_from(Contact).where(Contact.company_id == company_id)) or 0,
        "bookings": _bookings(db, company_id),
        "deals": db.scalar(select(text("count(*)")).select_from(SalesDeal).where(SalesDeal.company_id == company_id)) or 0,
        "proposals": db.scalar(text("SELECT count(*) FROM proposals WHERE company_id = :c"), {"c": company_id}) or 0,
    }


def _move_unique(db: Session, model, key_col: str, source: uuid.UUID, target: uuid.UUID) -> None:
    """Re-points link rows from source to target, dropping the ones target already has (unique pairs)."""
    other = getattr(model, key_col)
    have = set(db.scalars(select(other).where(model.company_id == target)))
    for row in db.scalars(select(model).where(model.company_id == source)).all():
        if getattr(row, key_col) in have:
            db.delete(row)
        else:
            row.company_id = target
            have.add(getattr(row, key_col))


def merge_companies(db: Session, source: Company, target: Company, user_id: uuid.UUID | None) -> dict:
    """Moves everything from `source` into `target` (contacts, notes, history, activities, bookings, deals,
    proposals, owners, addresses, phones, emails), notes the merge on target, then deletes source."""
    from app.models import SalesDeal, SalesOrder

    s, t = source.id, target.id
    moved = company_usage(db, s)
    for model in (Contact, Activity, Address, Phone, Email, Opportunity, SalesDeal, SalesOrder):
        db.execute(update(model).where(model.company_id == s).values(company_id=t))
    db.execute(text("UPDATE proposals SET company_id = :t WHERE company_id = :s"), {"t": t, "s": s})
    db.execute(text("UPDATE reminders SET company_id = :t WHERE company_id = :s"), {"t": t, "s": s})
    db.execute(text("DELETE FROM client_owners o WHERE o.company_id = :s AND EXISTS "
                    "(SELECT 1 FROM client_owners x WHERE x.company_id = :t AND x.area = o.area)"), {"t": t, "s": s})
    db.execute(text("UPDATE client_owners SET company_id = :t WHERE company_id = :s"), {"t": t, "s": s})
    _move_unique(db, ActivityCompany, "activity_id", s, t)
    _move_unique(db, ContactCompanyLink, "contact_id", s, t)
    db.execute(update(Company).where(Company.parent_company_id == s, Company.id != t).values(parent_company_id=t))
    for model in (Note, HistoryEntry):
        db.execute(update(model).where(model.entity_type == "company", model.entity_id == s).values(entity_id=t))
    db.flush()
    db.add(HistoryEntry(id=uuid.uuid4(), source_db=MANUAL_SOURCE_DB, source_act_id=str(uuid.uuid4()), entity_type="company",
                        entity_id=t, history_type="Merged", subject=f"Merged in \"{source.name}\"",
                        details=f"{moved['contacts']} contacts, {moved['bookings']} bookings and everything else moved here.",
                        occurred_at=datetime.now(timezone.utc), created_by_user_id=user_id))
    db.delete(source)
    return moved


def delete_company_rows(db: Session, company: Company, *, delete_contacts: bool) -> int:
    """Deletes a company. Its contacts are kept (no company any more) or deleted with it. Returns contacts deleted.
    Callers must refuse first when it has bookings, deals or proposals (those would be lost)."""
    from app.models import SalesDeal

    c = company.id
    gone = 0
    if delete_contacts:
        for contact in db.scalars(select(Contact).where(Contact.company_id == c)).all():
            delete_contact_rows(db, contact)
            gone += 1
    db.execute(update(Contact).where(Contact.company_id == c).values(company_id=None))
    for model in (ActivityCompany, ContactCompanyLink, Address, Phone, Email):
        db.execute(model.__table__.delete().where(model.company_id == c))
    for model in (Activity, Opportunity, SalesDeal):
        db.execute(update(model).where(model.company_id == c).values(company_id=None))
    db.execute(update(Company).where(Company.parent_company_id == c).values(parent_company_id=None))
    db.execute(Note.__table__.delete().where(Note.entity_type == "company", Note.entity_id == c))
    db.execute(HistoryEntry.__table__.delete().where(HistoryEntry.entity_type == "company", HistoryEntry.entity_id == c))
    db.flush()
    db.delete(company)
    return gone
