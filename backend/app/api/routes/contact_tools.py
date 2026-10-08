"""Contact power tools asked for by BMI's Act! users: the field list for
search/bulk update, "copy email addresses", and bulk update with undo.
(Import lives in contact_imports.py.) Registered *before* contacts.py so
/contacts/fields etc. aren't read as a contact id."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.messaging import current_user
from app.contacts import fields as F
from app.contacts.scope import Scope, resolve
from app.core.identity import Identity, get_identity
from app.db.session import get_db
from app.models import BulkEdit, Contact, Email, User
from app.roles import CAN_USE_AUTOMATIONS
from app.services.field_audit import record_field_changes

router = APIRouter(prefix="/contacts", tags=["contact tools"])


# ---- field list ---------------------------------------------------------------

class FieldOut(BaseModel):
    key: str
    label: str
    group: str
    kind: str
    ops: list[dict]
    bulk: bool
    custom: bool


@router.get("/fields", response_model=list[FieldOut])
def list_fields(db: Session = Depends(get_db)) -> list[FieldOut]:
    """Every field that can be searched on, with the ways it can be compared."""
    return [FieldOut(key=f.key, label=f.label, group=f.group, kind=f.kind,
                     ops=[{"op": o, "label": F.OP_LABELS[o]} for o in F.OPS_BY_KIND[f.kind]],
                     bulk=f.bulk and f.store in ("contact", "custom"), custom=f.store == "custom")
            for f in F.all_fields(db)]


class CustomLabelsOut(BaseModel):
    keys: list[str]
    labels: dict[str, str]


@router.get("/fields/custom", response_model=CustomLabelsOut)
def custom_fields(db: Session = Depends(get_db)) -> CustomLabelsOut:
    return CustomLabelsOut(keys=F.custom_keys(db, refresh=True), labels=F.get_custom_labels(db))


@router.put("/fields/custom", response_model=CustomLabelsOut)
def save_custom_labels(payload: dict[str, str], db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> CustomLabelsOut:
    """Give the Act! custom fields their real names ({"user3": "ABTA number"}). Admins and data managers only."""
    if identity.is_known and identity.role not in CAN_USE_AUTOMATIONS:
        raise HTTPException(403, "Only admins and data managers can rename fields.")
    F.set_custom_labels(db, payload)
    return CustomLabelsOut(keys=F.custom_keys(db), labels=F.get_custom_labels(db))


# ---- copy email addresses -------------------------------------------------------

MAX_COPY = 5000  # more than this is too many to paste anywhere useful (Outlook takes ~500 per email)


class EmailsOut(BaseModel):
    count: int
    too_many: bool = False
    text: str  # "a@x.com; b@y.com" - ready to paste into Outlook
    contacts: int
    skipped_unsubscribed: int
    skipped_bounced: int
    skipped_no_email: int
    duplicates_removed: int


@router.post("/emails", response_model=EmailsOut)
def email_addresses(scope: Scope, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> EmailsOut:
    """The email addresses for a search or selection, for pasting into Outlook's Bcc box.
    Leaves out people who unsubscribed or whose address bounced, and says how many."""
    ids = resolve(db, scope, identity)
    if len(ids) > MAX_COPY:
        return EmailsOut(count=0, too_many=True, text="", contacts=len(ids), skipped_unsubscribed=0, skipped_bounced=0,
                         skipped_no_email=0, duplicates_removed=0)
    seen: dict[str, str] = {}
    unsub = bounced = no_email = dup = 0
    for i in range(0, len(ids), 2000):
        chunk = ids[i:i + 2000]
        flags = {c.id: c for c in db.scalars(select(Contact).where(Contact.id.in_(chunk)))}
        best: dict[uuid.UUID, str] = {}
        for cid, addr in db.execute(select(Email.contact_id, Email.address).where(Email.contact_id.in_(chunk), Email.address.isnot(None))
                                    .order_by(Email.is_primary.desc(), Email.address)):
            if addr and addr.strip() and cid not in best:
                best[cid] = addr.strip()
        for cid in chunk:
            c = flags.get(cid)
            if not c:
                continue
            if c.is_unsubscribed or c.is_email_opted_out:
                unsub += 1
            elif c.has_bounced:
                bounced += 1
            elif cid not in best:
                no_email += 1
            else:
                key = best[cid].lower()
                if key in seen:
                    dup += 1
                else:
                    seen[key] = best[cid]
    addrs = list(seen.values())
    return EmailsOut(count=len(addrs), text="; ".join(addrs), contacts=len(ids), skipped_unsubscribed=unsub,
                     skipped_bounced=bounced, skipped_no_email=no_email, duplicates_removed=dup)


# ---- bulk update ----------------------------------------------------------------

class BulkIn(BaseModel):
    scope: Scope
    field: str
    op: str = Field(pattern="^(set|clear|replace)$")
    value: str | None = None
    find: str | None = None


class BulkSample(BaseModel):
    id: uuid.UUID
    name: str | None
    old: str | None
    new: str | None


class BulkPreview(BaseModel):
    field_label: str
    total: int
    will_change: int
    unchanged: int
    samples: list[BulkSample]


class BulkEditOut(BaseModel):
    id: uuid.UUID
    field_label: str
    op: str
    new_value: str | None
    find_text: str | None
    scope_label: str | None
    total: int
    changed: int
    status: str
    created_at: datetime
    undone_at: datetime | None
    by: str | None


def _bulk_field(db: Session, key: str) -> F.FieldDef:
    f = F.get_field(db, key)
    if f is None or not (f.bulk and f.store in ("contact", "custom")):
        raise HTTPException(422, "That field can't be changed in bulk.")
    return f


def _current(c: Contact, f: F.FieldDef):
    if f.store == "custom":
        v = (c.custom_fields or {}).get(f.column)
        return None if v is None else (v if isinstance(v, str) else str(v))
    return getattr(c, f.column)


def _yes(value: str | None) -> bool | None:
    if value is None:
        return None
    v = value.strip().lower()
    if v in ("yes", "y", "true", "1", "on"):
        return True
    if v in ("no", "n", "false", "0", "off"):
        return False
    raise HTTPException(422, "Choose yes or no.")


def _new_value(f: F.FieldDef, p: BulkIn, old):
    """What the field becomes (None = empty). `old` is the current value."""
    if p.op == "clear":
        return False if f.kind == "bool" else None
    if f.kind == "bool":
        if p.op != "set":
            raise HTTPException(422, "Yes/no fields can only be set or cleared.")
        return _yes(p.value)
    if p.op == "set":
        v = (p.value or "").strip()
        if not v:
            raise HTTPException(422, "Type the new value, or choose “Clear it”.")
        return v
    # replace
    if not (p.find or "").strip():
        raise HTTPException(422, "Type the text to find.")
    if old is None:
        return old
    out = old.replace(p.find, p.value or "") if p.find in old else old
    return out.strip() or None


def _max_len(f: F.FieldDef) -> int | None:
    if f.store != "contact":
        return None
    return getattr(Contact.__table__.c[f.column].type, "length", None)


def _plan(db: Session, p: BulkIn, identity: Identity) -> tuple[F.FieldDef, list[uuid.UUID], list[tuple[Contact, object, object]]]:
    f = _bulk_field(db, p.field)
    ids = resolve(db, p.scope, identity)
    if not ids:
        raise HTTPException(404, "No contacts match.")
    limit = _max_len(f)
    if p.op == "set" and limit and len((p.value or "").strip()) > limit:
        raise HTTPException(422, f"{f.label} can be at most {limit} characters.")
    changes = []
    for i in range(0, len(ids), 2000):
        for c in db.scalars(select(Contact).where(Contact.id.in_(ids[i:i + 2000]))):
            old = _current(c, f)
            new = _new_value(f, p, old)
            if f.kind == "bool":
                old = bool(old)
            if new != old and not (old in (None, "") and new in (None, "")):
                changes.append((c, old, new))
    return f, ids, changes


def _display(v) -> str | None:
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return "Yes" if v else "No"
    return str(v)


@router.post("/bulk-update/preview", response_model=BulkPreview)
def bulk_preview(p: BulkIn, db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> BulkPreview:
    f, ids, changes = _plan(db, p, identity)
    return BulkPreview(field_label=f.label, total=len(ids), will_change=len(changes), unchanged=len(ids) - len(changes),
                       samples=[BulkSample(id=c.id, name=c.full_name, old=_display(o), new=_display(n)) for c, o, n in changes[:8]])


def _apply(db: Session, c: Contact, f: F.FieldDef, new, user_id) -> None:
    if f.store == "custom":
        cf = dict(c.custom_fields or {})
        before = {f"custom:{f.column}": cf.get(f.column)}
        if new in (None, ""):
            cf.pop(f.column, None)
        else:
            cf[f.column] = new
        c.custom_fields = cf
        record_field_changes(db, entity_type="contact", entity_id=c.id, before=before, updates={f"custom:{f.column}": cf.get(f.column)},
                             changed_by_user_id=user_id)
        return
    updates = {f.column: new}
    before = {f.column: getattr(c, f.column)}
    if f.column in ("first_name", "last_name"):
        first = new if f.column == "first_name" else c.first_name
        last = new if f.column == "last_name" else c.last_name
        updates["full_name"] = " ".join(filter(None, [first, last])) or None
        before["full_name"] = c.full_name
    for k, v in updates.items():
        setattr(c, k, v)
    record_field_changes(db, entity_type="contact", entity_id=c.id, before=before, updates=updates, changed_by_user_id=user_id)


@router.post("/bulk-update", response_model=BulkEditOut)
def bulk_apply(p: BulkIn, db: Session = Depends(get_db), user: User = Depends(current_user),
               identity: Identity = Depends(get_identity)) -> BulkEditOut:
    """Applies the change to every contact in the search/selection. Every change is in each
    contact's history, and the whole update can be undone."""
    f, ids, changes = _plan(db, p, identity)
    if not changes:
        raise HTTPException(409, "Nothing would change - those contacts already have that value.")
    before: dict[str, object] = {}
    for c, old, new in changes:
        before[str(c.id)] = {"old": old, "new": new}  # what Undo needs: put "old" back if it still says "new"
        _apply(db, c, f, new, user.id)
    edit = BulkEdit(id=uuid.uuid4(), user_id=user.id, field_key=f.key, field_label=f.label, op=p.op, new_value=p.value,
                    find_text=p.find, scope_label=p.scope.label, total=len(ids), changed=len(changes), before=before)
    db.add(edit)
    db.commit()
    F.forget_custom_keys()
    return _edit_out(db, edit)


def _edit_out(db: Session, e: BulkEdit) -> BulkEditOut:
    u = db.get(User, e.user_id) if e.user_id else None
    return BulkEditOut(id=e.id, field_label=e.field_label, op=e.op, new_value=e.new_value, find_text=e.find_text,
                       scope_label=e.scope_label, total=e.total, changed=e.changed, status=e.status, created_at=e.created_at,
                       undone_at=e.undone_at, by=u.name if u else None)


@router.get("/bulk-update/history", response_model=list[BulkEditOut])
def bulk_history(db: Session = Depends(get_db)) -> list[BulkEditOut]:
    return [_edit_out(db, e) for e in db.scalars(select(BulkEdit).order_by(BulkEdit.created_at.desc()).limit(30))]


class UndoOut(BaseModel):
    restored: int
    skipped: int


@router.post("/bulk-update/{edit_id}/undo", response_model=UndoOut)
def bulk_undo(edit_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)) -> UndoOut:
    """Puts the old values back - but leaves alone anyone whose value has been changed again since."""
    e = db.get(BulkEdit, edit_id)
    if not e:
        raise HTTPException(404, "Update not found")
    if e.status == "undone":
        raise HTTPException(409, "This update has already been undone.")
    f = F.get_field(db, e.field_key)
    if f is None:
        raise HTTPException(409, "That field no longer exists.")
    restored = skipped = 0
    for cid, pair in e.before.items():
        c = db.get(Contact, uuid.UUID(cid))
        if not c:
            skipped += 1
            continue
        now = _current(c, f)
        if f.kind == "bool":
            now = bool(now)
        if now != pair["new"]:  # changed again since - leave it alone
            skipped += 1
            continue
        _apply(db, c, f, pair["old"], user.id)
        restored += 1
    e.status, e.undone_at = "undone", datetime.now(timezone.utc)
    db.commit()
    return UndoOut(restored=restored, skipped=skipped)
