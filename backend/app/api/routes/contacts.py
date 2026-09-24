from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.api.schemas import (
    MANUAL_SOURCE_DB,
    AddressOut,
    AddressWrite,
    ActivityOut,
    CompanySummary,
    ContactCreate,
    ContactDetail,
    ContactListItem,
    ContactPosition,
    ContactsPage,
    ContactUpdate,
    EmailOut,
    EmailWrite,
    FieldChangeOut,
    GroupOut,
    HistoryCreate,
    HistoryOut,
    NoteCreate,
    NoteOut,
    PhoneOut,
    PhoneWrite,
    UserSummary,
)
from app.api.routes._channels import create_channel, delete_channel, delete_entity_row, update_channel
from app.api.routes._creators import creator_summary, resolve_creators
from app.api.routes._publications import resolve_source_db
from app.core.identity import Identity, get_identity
from app.db.session import get_db
from app.services.contact_transfer import reassign_contact_records
from app.services.field_audit import record_field_changes
from app.models import (
    Activity,
    Company,
    Contact,
    Email,
    FieldChange,
    Group,
    GroupMembership,
    HistoryEntry,
    Note,
    Opportunity,
    User,
)
from app.models.contact_channel import Address, Phone

router = APIRouter(prefix="/contacts", tags=["contacts"])


def _apply_contact_filters(
    db: Session,
    stmt,
    q: str | None,
    source_db: str | None,
    company_id: uuid.UUID | None,
    group_id: uuid.UUID | None,
):
    """Shared by list_contacts and get_contact_position - same filters, same
    row set, so record-navigation (prev/next) walks exactly what the list
    view that got you here was showing, not some other, unfiltered order."""
    if source_db:
        stmt = stmt.where(Contact.source_db == source_db)
    if company_id:
        stmt = stmt.where(Contact.company_id == company_id)
    if group_id:
        # Groups are hierarchical (see Group.parent_group_id) - a
        # group-scoped grant covers the whole subtree, not just direct
        # members, so someone scoped to "BUSINESS" also sees contacts
        # filed under its subfolders, matching how Act!'s own group view
        # works.
        subtree_ids = db.execute(
            text(
                "WITH RECURSIVE subtree AS ("
                "  SELECT id FROM groups WHERE id = :gid"
                "  UNION ALL"
                "  SELECT g.id FROM groups g JOIN subtree s ON g.parent_group_id = s.id"
                ") SELECT id FROM subtree"
            ),
            {"gid": str(group_id)},
        ).scalars().all()
        stmt = stmt.where(
            Contact.id.in_(select(GroupMembership.contact_id).where(GroupMembership.group_id.in_(subtree_ids)))
        )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Contact.full_name.ilike(like),
                Contact.first_name.ilike(like),
                Contact.last_name.ilike(like),
                Contact.id.in_(select(Email.contact_id).where(Email.address.ilike(like))),
            )
        )
    return stmt


@router.get("", response_model=ContactsPage)
def list_contacts(
    q: str | None = Query(None, description="Search by name or email"),
    source_db: str | None = Query(None),
    company_id: uuid.UUID | None = Query(None),
    group_id: uuid.UUID | None = Query(
        None, description="Restrict to this group's members plus every descendant subgroup's - used for group-scoped user access, see app/models/user_access.py"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ContactsPage:
    # Primary email per contact, via a scalar subquery - cheap correlated
    # lookup, fine at this row count (~118k contacts across all sources).
    primary_email_subq = (
        select(Email.address)
        .where(Email.contact_id == Contact.id)
        .order_by(Email.is_primary.desc())
        .limit(1)
        .correlate(Contact)
        .scalar_subquery()
    )

    stmt = (
        select(
            Contact,
            Company.name.label("company_name"),
            primary_email_subq.label("primary_email"),
        )
        .outerjoin(Company, Contact.company_id == Company.id)
    )
    stmt = _apply_contact_filters(db, stmt, q, source_db, company_id, group_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    stmt = stmt.order_by(Contact.last_name.asc().nulls_last(), Contact.first_name.asc().nulls_last())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    rows = db.execute(stmt).all()
    items = [
        ContactListItem(
            id=contact.id,
            source_db=contact.source_db,
            full_name=contact.full_name,
            first_name=contact.first_name,
            last_name=contact.last_name,
            job_title=contact.job_title,
            company_id=contact.company_id,
            company_name=company_name,
            primary_email=primary_email,
        )
        for contact, company_name, primary_email in rows
    ]
    return ContactsPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{contact_id}/position", response_model=ContactPosition)
def get_contact_position(
    contact_id: uuid.UUID,
    q: str | None = Query(None),
    source_db: str | None = Query(None),
    company_id: uuid.UUID | None = Query(None),
    group_id: uuid.UUID | None = Query(None),
    db: Session = Depends(get_db),
) -> ContactPosition:
    """Powers the VCR-style record stepper on the contact detail page - same
    filters as whatever list view the user came from, so Next/Previous
    walks that exact set in that exact order rather than a different one."""
    stmt = select(Contact.id).order_by(Contact.last_name.asc().nulls_last(), Contact.first_name.asc().nulls_last())
    stmt = _apply_contact_filters(db, stmt, q, source_db, company_id, group_id)
    ids = [str(row) for row in db.scalars(stmt).all()]

    first_id = ids[0] if ids else None
    last_id = ids[-1] if ids else None

    try:
        index = ids.index(str(contact_id))
    except ValueError:
        # The record itself doesn't match the current filters (e.g. the
        # filter changed since navigating here) - report just the total so
        # the UI can still show a count, with no prev/next to step to.
        return ContactPosition(position=None, total=len(ids), prev_id=None, next_id=None, first_id=first_id, last_id=last_id)

    return ContactPosition(
        position=index + 1,
        total=len(ids),
        prev_id=ids[index - 1] if index > 0 else None,
        next_id=ids[index + 1] if index < len(ids) - 1 else None,
        first_id=first_id,
        last_id=last_id,
    )


@router.get("/{contact_id}", response_model=ContactDetail)
def get_contact(contact_id: uuid.UUID, db: Session = Depends(get_db)) -> ContactDetail:
    contact = db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    company = db.get(Company, contact.company_id) if contact.company_id else None
    addresses = db.scalars(select(Address).where(Address.contact_id == contact_id)).all()
    phones = db.scalars(select(Phone).where(Phone.contact_id == contact_id)).all()
    emails = db.scalars(select(Email).where(Email.contact_id == contact_id)).all()
    groups = db.scalars(
        select(Group).join(GroupMembership, GroupMembership.group_id == Group.id)
        .where(GroupMembership.contact_id == contact_id)
    ).all()
    notes = db.scalars(
        select(Note).where(Note.entity_type == "contact", Note.entity_id == contact_id)
        .order_by(Note.act_created_at.desc().nulls_last())
        .limit(500)
    ).all()
    history = db.scalars(
        select(HistoryEntry).where(HistoryEntry.entity_type == "contact", HistoryEntry.entity_id == contact_id)
        .order_by(HistoryEntry.occurred_at.desc())
        .limit(500)
    ).all()
    activities = db.scalars(
        select(Activity).where(Activity.contact_id == contact_id)
        .order_by(Activity.start_at.desc())
        .limit(500)
    ).all()

    creators = resolve_creators(db, [*notes, *history, *activities])

    def _note_out(n: Note) -> NoteOut:
        out = NoteOut.model_validate(n)
        out.created_by = creator_summary(n, creators)
        return out

    def _history_out(h: HistoryEntry) -> HistoryOut:
        out = HistoryOut.model_validate(h)
        out.created_by = creator_summary(h, creators)
        return out

    def _activity_out(a: Activity) -> ActivityOut:
        out = ActivityOut.model_validate(a)
        out.created_by = creator_summary(a, creators)
        return out

    return ContactDetail(
        id=contact.id,
        source_db=contact.source_db,
        source_act_id=contact.source_act_id,
        first_name=contact.first_name,
        middle_name=contact.middle_name,
        last_name=contact.last_name,
        full_name=contact.full_name,
        job_title=contact.job_title,
        department=contact.department,
        category=contact.category,
        referred_by=contact.referred_by,
        birthdate=contact.birthdate,
        last_meet_date=contact.last_meet_date,
        last_reach_date=contact.last_reach_date,
        last_attempt_date=contact.last_attempt_date,
        last_letter_date=contact.last_letter_date,
        is_unsubscribed=contact.is_unsubscribed,
        custom_fields=contact.custom_fields,
        company=CompanySummary.model_validate(company) if company else None,
        addresses=[AddressOut.model_validate(a) for a in addresses],
        phones=[PhoneOut.model_validate(p) for p in phones],
        emails=[EmailOut.model_validate(e) for e in emails],
        groups=[GroupOut.model_validate(g) for g in groups],
        notes=[_note_out(n) for n in notes],
        history=[_history_out(h) for h in history],
        activities=[_activity_out(a) for a in activities],
    )


@router.post("/{contact_id}/notes", response_model=NoteOut, status_code=201)
def add_contact_note(contact_id: uuid.UUID, payload: NoteCreate, db: Session = Depends(get_db)) -> NoteOut:
    if not db.get(Contact, contact_id):
        raise HTTPException(status_code=404, detail="Contact not found")

    note = Note(
        id=uuid.uuid4(),
        source_db=MANUAL_SOURCE_DB,
        source_act_id=str(uuid.uuid4()),
        entity_type="contact",
        entity_id=contact_id,
        note_type=payload.note_type,
        body=payload.body,
        is_private=payload.is_private,
        act_created_at=datetime.now(timezone.utc),
        created_by_user_id=payload.created_by_user_id,
    )
    db.add(note)
    db.commit()
    out = NoteOut.model_validate(note)
    out.created_by = creator_summary(note, resolve_creators(db, [note]))
    return out


@router.post("/{contact_id}/history", response_model=HistoryOut, status_code=201)
def add_contact_history(contact_id: uuid.UUID, payload: HistoryCreate, db: Session = Depends(get_db)) -> HistoryOut:
    if not db.get(Contact, contact_id):
        raise HTTPException(status_code=404, detail="Contact not found")

    entry = HistoryEntry(
        id=uuid.uuid4(),
        source_db=MANUAL_SOURCE_DB,
        source_act_id=str(uuid.uuid4()),
        entity_type="contact",
        entity_id=contact_id,
        history_type=payload.history_type,
        subject=payload.subject,
        details=payload.details,
        duration_minutes=payload.duration_minutes,
        is_private=payload.is_private,
        occurred_at=payload.occurred_at,
        created_by_user_id=payload.created_by_user_id,
    )
    db.add(entry)
    db.commit()
    out = HistoryOut.model_validate(entry)
    out.created_by = creator_summary(entry, resolve_creators(db, [entry]))
    return out


@router.delete("/{contact_id}/notes/{note_id}", status_code=204, response_model=None)
def delete_contact_note(contact_id: uuid.UUID, note_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    delete_entity_row(db, Note, "contact", contact_id, note_id)


@router.delete("/{contact_id}/history/{history_id}", status_code=204, response_model=None)
def delete_contact_history(contact_id: uuid.UUID, history_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    delete_entity_row(db, HistoryEntry, "contact", contact_id, history_id)


def _require_contact(db: Session, contact_id: uuid.UUID) -> None:
    if not db.get(Contact, contact_id):
        raise HTTPException(status_code=404, detail="Contact not found")


@router.post("/{contact_id}/emails", response_model=EmailOut, status_code=201)
def add_contact_email(contact_id: uuid.UUID, payload: EmailWrite, db: Session = Depends(get_db)) -> EmailOut:
    _require_contact(db, contact_id)
    return EmailOut.model_validate(create_channel(db, Email, "contact_id", contact_id, payload))


@router.patch("/{contact_id}/emails/{email_id}", response_model=EmailOut)
def update_contact_email(
    contact_id: uuid.UUID, email_id: uuid.UUID, payload: EmailWrite, db: Session = Depends(get_db)
) -> EmailOut:
    _require_contact(db, contact_id)
    return EmailOut.model_validate(update_channel(db, Email, "contact_id", contact_id, email_id, payload))


@router.delete("/{contact_id}/emails/{email_id}", status_code=204, response_model=None)
def delete_contact_email(contact_id: uuid.UUID, email_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    _require_contact(db, contact_id)
    delete_channel(db, Email, "contact_id", contact_id, email_id)


@router.post("/{contact_id}/phones", response_model=PhoneOut, status_code=201)
def add_contact_phone(contact_id: uuid.UUID, payload: PhoneWrite, db: Session = Depends(get_db)) -> PhoneOut:
    _require_contact(db, contact_id)
    return PhoneOut.model_validate(create_channel(db, Phone, "contact_id", contact_id, payload))


@router.patch("/{contact_id}/phones/{phone_id}", response_model=PhoneOut)
def update_contact_phone(
    contact_id: uuid.UUID, phone_id: uuid.UUID, payload: PhoneWrite, db: Session = Depends(get_db)
) -> PhoneOut:
    _require_contact(db, contact_id)
    return PhoneOut.model_validate(update_channel(db, Phone, "contact_id", contact_id, phone_id, payload))


@router.delete("/{contact_id}/phones/{phone_id}", status_code=204, response_model=None)
def delete_contact_phone(contact_id: uuid.UUID, phone_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    _require_contact(db, contact_id)
    delete_channel(db, Phone, "contact_id", contact_id, phone_id)


@router.post("/{contact_id}/addresses", response_model=AddressOut, status_code=201)
def add_contact_address(contact_id: uuid.UUID, payload: AddressWrite, db: Session = Depends(get_db)) -> AddressOut:
    _require_contact(db, contact_id)
    return AddressOut.model_validate(create_channel(db, Address, "contact_id", contact_id, payload))


@router.patch("/{contact_id}/addresses/{address_id}", response_model=AddressOut)
def update_contact_address(
    contact_id: uuid.UUID, address_id: uuid.UUID, payload: AddressWrite, db: Session = Depends(get_db)
) -> AddressOut:
    _require_contact(db, contact_id)
    return AddressOut.model_validate(update_channel(db, Address, "contact_id", contact_id, address_id, payload))


@router.delete("/{contact_id}/addresses/{address_id}", status_code=204, response_model=None)
def delete_contact_address(contact_id: uuid.UUID, address_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    _require_contact(db, contact_id)
    delete_channel(db, Address, "contact_id", contact_id, address_id)


@router.post("", response_model=ContactDetail, status_code=201)
def create_contact(payload: ContactCreate, db: Session = Depends(get_db)) -> ContactDetail:
    if payload.company_id and not db.get(Company, payload.company_id):
        raise HTTPException(status_code=400, detail="company_id does not exist")
    source_db = resolve_source_db(db, payload.source_db)

    contact = Contact(
        id=uuid.uuid4(),
        source_db=source_db,
        source_act_id=str(uuid.uuid4()),  # provenance columns are NOT NULL even for manual rows
        first_name=payload.first_name,
        last_name=payload.last_name,
        full_name=payload.full_name or " ".join(filter(None, [payload.first_name, payload.last_name])) or None,
        job_title=payload.job_title,
        department=payload.department,
        company_id=payload.company_id,
        custom_fields={},
    )
    db.add(contact)
    db.flush()

    if payload.email:
        db.add(Email(
            id=uuid.uuid4(), source_db=source_db, source_act_id=str(uuid.uuid4()),
            contact_id=contact.id, address=payload.email, is_primary=True,
        ))
    if payload.phone:
        db.add(Phone(
            id=uuid.uuid4(), source_db=source_db, source_act_id=str(uuid.uuid4()),
            contact_id=contact.id, number=payload.phone, is_primary=True,
        ))
    db.commit()
    return get_contact(contact.id, db)


@router.patch("/{contact_id}", response_model=ContactDetail)
def update_contact(
    contact_id: uuid.UUID, payload: ContactUpdate,
    db: Session = Depends(get_db), identity: Identity = Depends(get_identity),
) -> ContactDetail:
    contact = db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    if payload.company_id and not db.get(Company, payload.company_id):
        raise HTTPException(status_code=400, detail="company_id does not exist")

    updates = payload.model_dump(exclude_unset=True)
    # full_name is derived from first/last at create time (see
    # create_contact) but was never recomputed here - clearing both name
    # fields left the old full_name behind, so the record still displayed
    # its old name everywhere (the header, contacts list, EntityAvatar)
    # even though first_name/last_name had genuinely changed underneath.
    # Skipped only if the caller explicitly set full_name itself.
    if ("first_name" in updates or "last_name" in updates) and "full_name" not in updates:
        new_first = updates.get("first_name", contact.first_name)
        new_last = updates.get("last_name", contact.last_name)
        updates["full_name"] = " ".join(filter(None, [new_first, new_last])) or None
    before = {field: getattr(contact, field) for field in updates}
    for field, value in updates.items():
        setattr(contact, field, value)
    record_field_changes(
        db, entity_type="contact", entity_id=contact.id, before=before, updates=updates,
        changed_by_user_id=identity.user_uuid,
    )
    db.commit()
    return get_contact(contact_id, db)


@router.get("/{contact_id}/field-changes", response_model=list[FieldChangeOut])
def list_contact_field_changes(contact_id: uuid.UUID, db: Session = Depends(get_db)) -> list[FieldChangeOut]:
    """"This might be a bit obvious but the ability to identify which BMI
    user has made changes to specific data" - BMI's own Act pain-points
    doc. Newest first - most useful reading direction for "what just
    changed on this record"."""
    rows = db.scalars(
        select(FieldChange)
        .where(FieldChange.entity_type == "contact", FieldChange.entity_id == contact_id)
        .order_by(FieldChange.changed_at.desc())
        .limit(200)
    ).all()
    user_ids = {r.changed_by_user_id for r in rows if r.changed_by_user_id}
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_(user_ids)))} if user_ids else {}
    return [
        FieldChangeOut(
            id=r.id, field=r.field, old_value=r.old_value, new_value=r.new_value, changed_at=r.changed_at,
            changed_by=UserSummary.model_validate(users[r.changed_by_user_id]) if r.changed_by_user_id in users else None,
        )
        for r in rows
    ]


@router.post("/{contact_id}/reassign/{successor_id}", status_code=204, response_model=None)
def reassign_contact(contact_id: uuid.UUID, successor_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    """"When a contact leaves a particular company, we can easily move
    notes in ACT from that person to a new person" - BMI's own Act pain-
    points doc. A manual, rep-initiated action (the rep already knows who
    left and who replaced them) - see app/services/contact_transfer.py's
    docstring for why the actual move logic lives there rather than here,
    shared with a future CS-003 automation instead of being reimplemented."""
    if contact_id == successor_id:
        raise HTTPException(status_code=400, detail="Pick a different contact to move records to.")
    source = db.get(Contact, contact_id)
    if not source:
        raise HTTPException(status_code=404, detail="Contact not found")
    destination = db.get(Contact, successor_id)
    if not destination:
        raise HTTPException(status_code=400, detail="The contact to move records to doesn't exist.")

    reassign_contact_records(db, source=source, destination=destination)
    db.commit()


@router.delete("/{contact_id}", status_code=204, response_model=None)
def delete_contact(contact_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    contact = db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # No cascade at the DB level (see contact_channel.py) - clean up every
    # row that actually has a foreign key into contacts.id ourselves, in one
    # transaction, before deleting the contact itself. Notes/History use
    # entity_id (not a real FK) so they can't block the delete, but we still
    # remove them - nothing should reference a contact that no longer exists.
    db.execute(GroupMembership.__table__.delete().where(GroupMembership.contact_id == contact_id))
    db.execute(Activity.__table__.update().where(Activity.contact_id == contact_id).values(contact_id=None))
    db.execute(Opportunity.__table__.update().where(Opportunity.contact_id == contact_id).values(contact_id=None))
    db.execute(Address.__table__.delete().where(Address.contact_id == contact_id))
    db.execute(Phone.__table__.delete().where(Phone.contact_id == contact_id))
    db.execute(Email.__table__.delete().where(Email.contact_id == contact_id))
    db.execute(Note.__table__.delete().where(Note.entity_type == "contact", Note.entity_id == contact_id))
    db.execute(HistoryEntry.__table__.delete().where(HistoryEntry.entity_type == "contact", HistoryEntry.entity_id == contact_id))
    db.delete(contact)
    db.commit()


@router.post("/{contact_id}/groups/{group_id}", status_code=204, response_model=None)
def add_to_group(contact_id: uuid.UUID, group_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    if not db.get(Contact, contact_id):
        raise HTTPException(status_code=404, detail="Contact not found")
    if not db.get(Group, group_id):
        raise HTTPException(status_code=404, detail="Group not found")

    exists = db.scalar(
        select(GroupMembership).where(GroupMembership.contact_id == contact_id, GroupMembership.group_id == group_id)
    )
    if not exists:
        db.add(GroupMembership(id=uuid.uuid4(), contact_id=contact_id, group_id=group_id))
        db.commit()


@router.delete("/{contact_id}/groups/{group_id}", status_code=204, response_model=None)
def remove_from_group(contact_id: uuid.UUID, group_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    db.execute(
        GroupMembership.__table__.delete().where(
            GroupMembership.contact_id == contact_id, GroupMembership.group_id == group_id
        )
    )
    db.commit()
