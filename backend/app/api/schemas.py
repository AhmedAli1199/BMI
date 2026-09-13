"""Pydantic response shapes for the read endpoints. Kept separate from the
SQLAlchemy models (app/models/) on purpose - these are what the frontend
sees, the models are what the database looks like, and they're allowed to
diverge (e.g. we never expose custom_fields' internal shape directly
without deciding it's stable API surface).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

# source_db used for anything created directly in the CRM (not migrated
# from an Act! database). Kept distinct from the three real source
# databases (see app.models.base.SOURCE_DBS) so it's always obvious in
# provenance data which rows came from Act! vs. were typed in here.
MANUAL_SOURCE_DB = "manual"


class CompanySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    source_db: str
    industry: str | None = None
    category: str | None = None


class ContactListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_db: str
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    company_id: uuid.UUID | None = None
    company_name: str | None = None
    primary_email: str | None = None


class Page(BaseModel):
    items: list
    total: int
    page: int
    page_size: int


class ContactsPage(Page):
    items: list[ContactListItem]


class AddressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type_label: str | None = None
    line1: str | None = None
    line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None


class PhoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type_label: str | None = None
    number: str | None = None


class EmailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type_label: str | None = None
    address: str | None = None


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    note_type: str | None = None
    body: str | None = None
    act_created_at: datetime | None = None


class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    history_type: str
    subject: str | None = None
    occurred_at: datetime


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str


class ContactDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_db: str
    source_act_id: str
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    job_title: str | None = None
    department: str | None = None
    category: str | None = None
    referred_by: str | None = None
    birthdate: date | None = None
    custom_fields: dict
    company: CompanySummary | None = None
    addresses: list[AddressOut] = []
    phones: list[PhoneOut] = []
    emails: list[EmailOut] = []
    groups: list[GroupOut] = []
    notes: list[NoteOut] = []
    history: list[HistoryOut] = []


class CompanyListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_db: str
    name: str
    industry: str | None = None
    category: str | None = None
    contact_count: int = 0


class CompaniesPage(Page):
    items: list[CompanyListItem]


class CompanyDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_db: str
    source_act_id: str
    name: str
    description: str | None = None
    industry: str | None = None
    category: str | None = None
    territory: str | None = None
    region: str | None = None
    website: str | None = None
    num_employees: int | None = None
    custom_fields: dict
    addresses: list[AddressOut] = []
    phones: list[PhoneOut] = []
    emails: list[EmailOut] = []
    contacts: list[ContactListItem] = []
    notes: list[NoteOut] = []


# ---- Write schemas (CRUD) --------------------------------------------------
# Separate Create/Update shapes rather than reusing the *Detail models:
# creation never accepts source_db/source_act_id/custom_fields (those are
# provenance, not something a user types in), and update makes every field
# optional so a PATCH can touch just one.


class ContactCreate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    job_title: str | None = None
    department: str | None = None
    company_id: uuid.UUID | None = None
    email: str | None = None
    phone: str | None = None


class ContactUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    job_title: str | None = None
    department: str | None = None
    company_id: uuid.UUID | None = None


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1)
    industry: str | None = None
    category: str | None = None
    website: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    industry: str | None = None
    category: str | None = None
    website: str | None = None


class GroupCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    parent_group_id: uuid.UUID | None = None


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    parent_group_id: uuid.UUID | None = None


class GroupListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str | None = None
    member_count: int = 0


class GroupDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str | None = None
    parent_group_id: uuid.UUID | None = None
    members: list[ContactListItem] = []


class GroupsPage(Page):
    items: list[GroupListItem]
