"""The one list of contact fields.

Search, the advanced filter, Excel export, bulk update and the import
wizard's column matching all read this registry, so adding or renaming a
field here changes all of them at once. Nothing else should hard-code
"which fields a contact has".

Custom fields (the Act! fields BMI added over the years - ABTA number, Type
and so on) are not listed here by hand: they are discovered from the data
(`custom_field_defs`). Until BMI tells us what each Act! custom field means,
they show under their stored names (e.g. "user3"). When they do, put the
real names in `CUSTOM_FIELD_LABELS` below (or save them from the API, see
`set_custom_labels`) and every screen picks them up - no other change.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.automations.state import get_state, set_state

# ---- Edit me when BMI tells us what the Act! custom fields mean -----------------
# {"user3": "ABTA number", "user4": "Type"}. Names saved through the API
# (stored in the database) win over this dict, so the dict is only a default.
CUSTOM_FIELD_LABELS: dict[str, str] = {}
# Which custom fields can be edited in bulk. None = all visible ones.
CUSTOM_FIELD_BULK_EDITABLE: set[str] | None = None
# ---------------------------------------------------------------------------------

LABELS_STATE_KEY = "contact_custom_field_labels"


@dataclass(frozen=True)
class FieldDef:
    key: str                  # stable id used in URLs, filters, bulk updates ("job_title", "custom:user3")
    label: str                # what people see
    group: str                # "Name" | "Job" | "Company" | "Email" | "Phone" | "Address" | "Status" | "Dates" | "Other" | "Custom"
    kind: str = "text"        # text | bool | date | number
    store: str = "contact"    # contact | company | email | phone | address | note | group | custom
    column: str | None = None  # attribute / jsonb key / address column
    bulk: bool = False        # may be changed for many contacts at once
    export: bool = True
    # import: column-header words that mean this field (see app/contacts/import_mapper.py)
    aliases: tuple[str, ...] = ()


def _t(key, label, group, column=None, *, bulk=False, aliases=(), store="contact", kind="text", export=True) -> FieldDef:
    return FieldDef(key, label, group, kind, store, column or key, bulk, export, aliases)


# Order here is the order fields appear in pickers.
BASE_FIELDS: list[FieldDef] = [
    _t("first_name", "First name", "Name", bulk=True),
    _t("middle_name", "Middle name", "Name", bulk=True),
    _t("last_name", "Last name", "Name", bulk=True),
    _t("full_name", "Full name", "Name"),
    _t("name_prefix", "Title (Mr, Mrs…)", "Name", bulk=True),
    _t("name_suffix", "Name suffix", "Name", bulk=True),
    _t("salutation", "Salutation", "Name", bulk=True),
    _t("job_title", "Job title", "Job", bulk=True),
    _t("department", "Department", "Job", bulk=True),
    _t("category", "Category", "Job", bulk=True),
    _t("referred_by", "Referred by", "Job", bulk=True),
    FieldDef("company", "Company", "Company", "text", "company", "name", False, True),
    FieldDef("email", "Email (any)", "Email", "text", "email", "address", False, True),
    FieldDef("phone", "Phone (any)", "Phone", "text", "phone", "number", False, True),
    FieldDef("mobile", "Mobile", "Phone", "text", "phone", "number", False, True),
    FieldDef("address", "Street address", "Address", "text", "address", "line1", False, True),
    FieldDef("city", "City / town", "Address", "text", "address", "city", False, True),
    FieldDef("state", "County / state", "Address", "text", "address", "state", False, True),
    FieldDef("postcode", "Postcode", "Address", "text", "address", "postal_code", False, True),
    FieldDef("country", "Country", "Address", "text", "address", "country", False, True),
    FieldDef("notes", "Notes (text)", "Other", "text", "note", "body", False, False),
    FieldDef("group", "In group", "Other", "text", "group", "name", False, False),
    _t("source_db", "Database", "Other", export=False),
    _t("last_results", "Last results", "Other", bulk=True),
    _t("is_unsubscribed", "Unsubscribed", "Status", bulk=True, kind="bool"),
    _t("is_email_opted_out", "Opted out of email", "Status", bulk=True, kind="bool"),
    _t("has_bounced", "Email bounced", "Status", kind="bool"),
    _t("is_private", "Private", "Status", bulk=True, kind="bool"),
    _t("birthdate", "Birthday", "Dates", kind="date"),
    _t("created_at", "Added to the CRM", "Dates", kind="date"),
    _t("last_email_date", "Last emailed", "Dates", kind="date"),
    _t("last_meet_date", "Last met", "Dates", kind="date"),
    _t("last_reach_date", "Last reached", "Dates", kind="date"),
]
BY_KEY = {f.key: f for f in BASE_FIELDS}

OPS_BY_KIND = {
    "text": ("contains", "not_contains", "equals", "starts_with", "is_empty", "is_not_empty"),
    "bool": ("is_yes", "is_no"),
    "date": ("on", "before", "after", "is_empty", "is_not_empty"),
    "number": ("equals", "greater", "less", "is_empty", "is_not_empty"),
}
OP_LABELS = {
    "contains": "contains", "not_contains": "doesn't contain", "equals": "is exactly", "starts_with": "starts with",
    "is_empty": "is empty", "is_not_empty": "has a value", "is_yes": "is yes", "is_no": "is no",
    "on": "is on", "before": "is before", "after": "is after", "greater": "is more than", "less": "is less than",
}

# ---- custom fields ----------------------------------------------------------------

_cache: dict[str, tuple[float, list[str]]] = {}
_CACHE_SECONDS = 600


def get_custom_labels(db: Session) -> dict[str, str]:
    return {**CUSTOM_FIELD_LABELS, **{k: v for k, v in get_state(db, LABELS_STATE_KEY).items() if isinstance(v, str) and v.strip()}}


def set_custom_labels(db: Session, labels: dict[str, str]) -> None:
    """Saves the real names for custom fields ({"user3": "ABTA number"}). Blank names remove the override."""
    clean = {k: v.strip() for k, v in labels.items() if k and isinstance(v, str) and v.strip()}
    set_state(db, LABELS_STATE_KEY, clean)
    db.commit()


def custom_keys(db: Session, *, refresh: bool = False) -> list[str]:
    """Every custom-field key that appears on at least one contact (cached for a few minutes).
    Internal keys that start with "_" are ours and never shown."""
    hit = _cache.get("keys")
    if hit and not refresh and time.time() - hit[0] < _CACHE_SECONDS:
        return hit[1]
    rows = db.execute(text(
        "SELECT DISTINCT k FROM contacts, LATERAL jsonb_object_keys(custom_fields) AS k WHERE jsonb_typeof(custom_fields) = 'object'"
    )).scalars().all()
    keys = sorted(k for k in rows if k and not k.startswith("_"))
    _cache["keys"] = (time.time(), keys)
    return keys


def forget_custom_keys() -> None:
    _cache.clear()


def pretty_key(key: str) -> str:
    return key.replace("_", " ").strip().capitalize() if key else key


def custom_field_defs(db: Session) -> list[FieldDef]:
    labels = get_custom_labels(db)
    out = []
    for k in custom_keys(db):
        editable = CUSTOM_FIELD_BULK_EDITABLE is None or k in CUSTOM_FIELD_BULK_EDITABLE
        out.append(FieldDef(f"custom:{k}", labels.get(k) or pretty_key(k), "Custom", "text", "custom", k, editable, True,
                            (labels[k],) if k in labels else ()))
    return out


def all_fields(db: Session) -> list[FieldDef]:
    return [*BASE_FIELDS, *custom_field_defs(db)]


def get_field(db: Session, key: str) -> FieldDef | None:
    if key in BY_KEY:
        return BY_KEY[key]
    if key.startswith("custom:"):
        k = key[7:]
        return next((f for f in custom_field_defs(db) if f.column == k), None) or (
            FieldDef(key, get_custom_labels(db).get(k) or pretty_key(k), "Custom", "text", "custom", k, True, True) if k and not k.startswith("_") else None)
    return None
