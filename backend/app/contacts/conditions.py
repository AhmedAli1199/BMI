"""Advanced-search conditions ("Postcode starts with SW1" AND "Type is exactly
Travel Counsellor") turned into SQL against the contact table.

A condition is {"field": <FieldDef.key>, "op": <op>, "value": <text>}. The
field list and the operators each kind of field allows come from
app/contacts/fields.py, so a new field is searchable the moment it is added
there. Many-valued fields (emails, phones, addresses, notes, groups) match if
*any* of a contact's values matches; "doesn't contain" / "is empty" on those
mean *none* does.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import and_, exists, func, not_, or_, select
from sqlalchemy.orm import Session

from app.contacts.fields import OPS_BY_KIND, FieldDef, get_field
from app.models import Company, Contact, Email, Group, GroupMembership, Note
from app.models.contact_channel import Address, Phone

MAX_CONDITIONS = 12


class BadCondition(ValueError):
    """The message is shown to the person who built the search."""


@dataclass(frozen=True)
class Condition:
    field: str
    op: str
    value: str = ""


def parse_conditions(raw: str | None) -> list[Condition]:
    if not raw or not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise BadCondition("The advanced search couldn't be read - clear it and try again.")
    if not isinstance(data, list) or len(data) > MAX_CONDITIONS:
        raise BadCondition(f"Use up to {MAX_CONDITIONS} conditions.")
    return [Condition(str(c.get("field", "")), str(c.get("op", "")), str(c.get("value", "") or "").strip())
            for c in data if isinstance(c, dict)]


def _like(value: str, mode: str = "contains") -> str:
    esc = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return {"contains": f"%{esc}%", "starts_with": f"{esc}%"}[mode]


def _text(col, op: str, value: str):
    """A text column against an operator. Empty-ish values count as empty."""
    blank = or_(col.is_(None), func.btrim(col) == "")
    if op == "contains":
        return col.ilike(_like(value), escape="\\")
    if op == "not_contains":
        return or_(col.is_(None), not_(col.ilike(_like(value), escape="\\")))
    if op == "equals":
        return func.lower(func.btrim(col)) == value.lower()
    if op == "starts_with":
        return col.ilike(_like(value, "starts_with"), escape="\\")
    if op == "is_empty":
        return blank
    if op == "is_not_empty":
        return not_(blank)
    raise BadCondition(f"“{op}” can't be used on a text field.")


def _parse_date(value: str) -> date:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise BadCondition(f"“{value}” isn't a date - use day/month/year.")


def _date(col, op: str, value: str):
    d = func.date(col)
    if op == "is_empty":
        return col.is_(None)
    if op == "is_not_empty":
        return col.isnot(None)
    day = _parse_date(value)
    return {"on": d == day, "before": d < day, "after": d > day}[op]


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def _related(model, owner_col, predicate, op: str):
    """Many-valued field: positive ops need one matching row; negative ops need none."""
    negative = op in ("not_contains", "is_empty")
    inner = select(model.id).where(owner_col == Contact.id, predicate).correlate(Contact)
    return not_(exists(inner)) if negative else exists(inner)


def _positive_op(op: str) -> str:
    return {"not_contains": "contains", "is_empty": "is_not_empty"}.get(op, op)


def clause(db: Session, c: Condition):
    f: FieldDef | None = get_field(db, c.field)
    if f is None:
        raise BadCondition(f"There's no field called “{c.field}”.")
    if c.op not in OPS_BY_KIND[f.kind]:
        raise BadCondition(f"“{c.op}” can't be used on {f.label}.")
    if c.op not in ("is_empty", "is_not_empty", "is_yes", "is_no") and not c.value:
        raise BadCondition(f"Type something for “{f.label}”.")
    op = c.op

    if f.kind == "bool":
        col = getattr(Contact, f.column)
        return col.is_(True) if op == "is_yes" else col.isnot(True)

    if f.store == "contact":
        col = getattr(Contact, f.column)
        return _date(col, op, c.value) if f.kind == "date" else _text(col, op, c.value)

    if f.store == "custom":
        col = Contact.custom_fields.op("->>")(f.column)
        return _text(col, op, c.value)

    if f.store == "company":
        pos = _positive_op(op)
        linked = _related_company(pos, c.value)
        free = _text(Contact.company_name_freetext, pos, c.value)
        both = or_(linked, free)
        return not_(both) if op in ("not_contains", "is_empty") else both

    pos = _positive_op(op)
    if f.store == "email":
        return _related(Email, Email.contact_id, _text(Email.address, pos, c.value), op)
    if f.store == "phone":
        col = Phone.number
        pred = _text(col, pos, c.value)
        digits = _digits(c.value)
        if pos == "contains" and len(digits) >= 3:
            pred = or_(pred, func.regexp_replace(col, r"\D", "", "g").like(f"%{digits}%"))
        if f.key == "mobile":
            pred = and_(pred, func.lower(func.coalesce(Phone.type_label, "")).like("mob%"))
        return _related(Phone, Phone.contact_id, pred, op)
    if f.store == "address":
        cols = [Address.line1, Address.line2, Address.line3] if f.key == "address" else [getattr(Address, f.column)]
        pred = or_(*[_text(col, pos, c.value) for col in cols])
        return _related(Address, Address.contact_id, pred, op)
    if f.store == "note":
        return _related(Note, Note.entity_id, and_(Note.entity_type == "contact", _text(Note.body, pos, c.value)), op)
    if f.store == "group":
        inner = select(GroupMembership.contact_id).join(Group, Group.id == GroupMembership.group_id).where(
            GroupMembership.contact_id == Contact.id, _text(Group.name, pos, c.value)).correlate(Contact)
        return not_(exists(inner)) if op in ("not_contains", "is_empty") else exists(inner)
    raise BadCondition(f"{f.label} can't be searched yet.")


def _related_company(op: str, value: str):
    return Contact.company_id.in_(select(Company.id).where(_text(Company.name, op, value)))


def build(db: Session, conditions: list[Condition], match_any: bool = False):
    if not conditions:
        return None
    parts = [clause(db, c) for c in conditions]
    return or_(*parts) if match_any else and_(*parts)
