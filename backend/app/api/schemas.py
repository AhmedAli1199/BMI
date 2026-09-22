"""Pydantic response shapes for the read endpoints. Kept separate from the
SQLAlchemy models (app/models/) on purpose - these are what the frontend
sees, the models are what the database looks like, and they're allowed to
diverge (e.g. we never expose custom_fields' internal shape directly
without deciding it's stable API surface).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

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


class ContactPosition(BaseModel):
    """Powers the record-stepper (VCR arrows) on the contact detail page -
    where this record sits within whatever filtered/sorted list the user
    navigated in from, and the neighbouring ids to step to."""
    position: int | None = None
    total: int
    prev_id: uuid.UUID | None = None
    next_id: uuid.UUID | None = None
    first_id: uuid.UUID | None = None
    last_id: uuid.UUID | None = None


class AddressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type_label: str | None = None
    line1: str | None = None
    line2: str | None = None
    line3: str | None = None
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


class AddressWrite(BaseModel):
    type_label: str | None = "Business"
    line1: str | None = None
    line2: str | None = None
    line3: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None


class PhoneWrite(BaseModel):
    type_label: str | None = "Business"
    number: str | None = None


class EmailWrite(BaseModel):
    type_label: str | None = "Business"
    address: str | None = None


class UserSummary(BaseModel):
    """Just enough to show "who logged this" - never the full UserOut
    (email, role, access) on a Note/History/Activity payload."""
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    note_type: str | None = None
    body: str | None = None
    is_private: bool = False
    act_created_at: datetime | None = None
    created_by: UserSummary | None = None
    # Where this note actually came from - one of app.models.base.SOURCE_DBS
    # for a real Act!-migrated note, or MANUAL_SOURCE_DB ("manual") for
    # anything written directly in this CRM. A "manual" note with no
    # created_by is always automation-authored (every UI-driven note-add
    # sets created_by_user_id from the logged-in session; no automation
    # ever does) - the frontend uses that combination to label a note
    # "AI / Automation" instead of the misleading blanket "Act! Manual" it
    # used to show for every single note regardless of real origin.
    source_db: str


class NoteCreate(BaseModel):
    body: str = Field(min_length=1)
    note_type: str = "Note"
    is_private: bool = False
    created_by_user_id: uuid.UUID | None = None


class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    history_type: str
    subject: str | None = None
    details: str | None = None
    duration_minutes: int | None = None
    is_private: bool = False
    occurred_at: datetime
    created_by: UserSummary | None = None


class HistoryCreate(BaseModel):
    # Act!'s dialog splits "History type" (Call/Meeting/...) from a
    # "Result" dropdown (Call Attempted/Call Completed/...) but stores one
    # combined string - see app/models/history.py's HISTORY_TYPES_KEPT for
    # the allowed values, which is exactly Act!'s own Result vocabulary.
    history_type: str = Field(min_length=1, max_length=64)
    subject: str | None = None
    details: str | None = None
    duration_minutes: int | None = None
    is_private: bool = False
    occurred_at: datetime
    created_by_user_id: uuid.UUID | None = None


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    activity_type: str | None = None
    subject: str | None = None
    details: str | None = None
    location: str | None = None
    start_at: datetime
    end_at: datetime | None = None
    is_timeless: bool = False
    is_cleared: bool = False
    is_private: bool = False
    priority: str = "normal"
    duration_minutes: int | None = None
    organized_by_name: str | None = None
    has_attachments: bool = False
    recurrence: str = "never"
    contact_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    contact_name: str | None = None
    company_name: str | None = None
    created_by: UserSummary | None = None


class ActivityCreate(BaseModel):
    activity_type: str = Field(min_length=1, max_length=128)  # "Call" / "Meeting" / "To-do"
    subject: str | None = None
    details: str | None = None
    location: str | None = None
    start_at: datetime
    end_at: datetime | None = None
    is_timeless: bool = False
    is_private: bool = False
    priority: str = "normal"
    duration_minutes: int | None = None
    organized_by_name: str | None = None
    recurrence: str = "never"
    contact_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    source_db: str
    created_by_user_id: uuid.UUID | None = None


class ActivityUpdate(BaseModel):
    activity_type: str | None = None
    subject: str | None = None
    details: str | None = None
    location: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    is_timeless: bool | None = None
    is_cleared: bool | None = None
    is_private: bool | None = None
    priority: str | None = None
    duration_minutes: int | None = None
    organized_by_name: str | None = None
    recurrence: str | None = None


class ActivitiesPage(Page):
    items: list[ActivityOut]



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
    last_meet_date: datetime | None = None
    last_reach_date: datetime | None = None
    last_attempt_date: datetime | None = None
    last_letter_date: datetime | None = None
    is_unsubscribed: bool = False
    custom_fields: dict
    company: CompanySummary | None = None
    addresses: list[AddressOut] = []
    phones: list[PhoneOut] = []
    emails: list[EmailOut] = []
    groups: list[GroupOut] = []
    notes: list[NoteOut] = []
    history: list[HistoryOut] = []
    activities: list[ActivityOut] = []


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


class CompanyPosition(BaseModel):
    """See ContactPosition - same idea, for the company record stepper."""
    position: int | None = None
    total: int
    prev_id: uuid.UUID | None = None
    next_id: uuid.UUID | None = None
    first_id: uuid.UUID | None = None
    last_id: uuid.UUID | None = None


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
    history: list[HistoryOut] = []
    activities: list[ActivityOut] = []


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
    # Which "database" (Publication.slug) this belongs to - omit for the
    # legacy "manual" bucket. See app/api/routes/publications.py.
    source_db: str | None = None


class ContactUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    job_title: str | None = None
    department: str | None = None
    category: str | None = None
    referred_by: str | None = None
    birthdate: date | None = None
    company_id: uuid.UUID | None = None


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1)
    industry: str | None = None
    category: str | None = None
    website: str | None = None
    source_db: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    industry: str | None = None
    category: str | None = None
    territory: str | None = None
    region: str | None = None
    website: str | None = None
    num_employees: int | None = None


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
    source_db: str
    name: str
    description: str | None = None
    member_count: int = 0
    # Act!'s group hierarchy (62 top-level groups + 183 sub-groups in
    # OnBoard alone) - carried through since migration but never surfaced
    # in the list view until now. hier_level 0 = top-level; parent_group_id
    # lets the frontend indent/nest without a second request per row.
    hier_level: int | None = None
    parent_group_id: uuid.UUID | None = None


class SourceBreakdown(BaseModel):
    source_db: str
    count: int


class RecentContact(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    company_id: uuid.UUID | None = None
    company_name: str | None = None
    created_at: datetime


class RecentCompany(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    industry: str | None = None
    created_at: datetime


class TopCompany(BaseModel):
    id: uuid.UUID
    name: str
    industry: str | None = None
    contact_count: int


class DashboardStats(BaseModel):
    total_contacts: int
    total_companies: int
    total_groups: int
    contacts_by_source: list[SourceBreakdown]
    companies_by_source: list[SourceBreakdown]
    recent_contacts: list[RecentContact]
    recent_companies: list[RecentCompany]
    top_companies: list[TopCompany]


class GroupDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_db: str
    name: str
    description: str | None = None
    parent_group_id: uuid.UUID | None = None
    members: list[ContactListItem] = []


class GroupsPage(Page):
    items: list[GroupListItem]


# ---- Automations / review queue --------------------------------------------
# See app/automations/registry.py for what these fields mean and the
# payload convention every automation follows.

class ReviewActionOut(BaseModel):
    id: str
    label: str
    style: str
    outcome: str
    requires_note: bool
    requires_contact_picker: bool
    extra_fields: list[dict]
    confirm_message: str | None = None
    requires_related_entity_choice: bool = False


class ReviewKindOut(BaseModel):
    kind: str
    label: str
    description: str
    actions: list[ReviewActionOut]


class ReviewQueueItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    kind: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    payload: dict
    status: str
    resolved_action: str | None = None
    review_note: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class ScheduledJobOut(BaseModel):
    id: str
    label: str
    description: str
    cron: str
    enabled: bool
    has_cursor: bool = False


class AutomationSettingOut(BaseModel):
    key: str
    label: str
    description: str
    group: str
    type: str  # "bool" | "int" | "float" | "csv"
    value: object  # the effective value right now - a stored override if one exists, else the env default
    default: object  # what it would be with no override - lets the UI show "(default)" or offer a reset
    is_overridden: bool
    min: float | None = None
    max: float | None = None


class AutomationSettingUpdate(BaseModel):
    value: object


class ReviewQueueCounts(BaseModel):
    kind: str
    pending: int
    approved: int = 0
    rejected: int = 0


class ReviewActionRequest(BaseModel):
    note: str | None = None
    contact_id: uuid.UUID | None = None
    fields: dict[str, str] = {}
    # Which of this item's own related_entities the reviewer picked, for an
    # action with requires_related_entity_choice=True (e.g. CS-004's merge -
    # which contact survives) - kept separate from contact_id, which is for
    # picking an unrelated contact via search (e.g. "match this bounce to
    # someone"), a different kind of choice with a different UI.
    chosen_entity_id: uuid.UUID | None = None


class ReviewQueuePage(Page):
    items: list[ReviewQueueItemOut]


class BulkReviewActionRequest(BaseModel):
    note: str | None = None


class BulkReviewActionResult(BaseModel):
    matched: int  # how many pending items matched kind/status before this ran
    succeeded: int
    failed: int
    errors: list[str] = []  # "<item id>: <message>" for whichever items failed, capped


# ---- LLM usage / cost dashboard ----------------------------------------

class LlmUsageBucket(BaseModel):
    """One row of the usage-over-time table - a fixed-width time bucket
    (see the `granularity` query param) with its own call counts and cost."""
    bucket_start: datetime
    call_count: int
    success_count: int
    failure_count: int
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


class LlmUsageByPurpose(BaseModel):
    purpose: str
    provider: str
    call_count: int
    failure_count: int
    cost_usd: float


class LlmUsageSummary(BaseModel):
    range_start: datetime
    range_end: datetime
    total_calls: int
    total_failures: int
    total_cost_usd: float
    total_prompt_tokens: int
    total_completion_tokens: int
    buckets: list[LlmUsageBucket]
    by_purpose: list[LlmUsageByPurpose]


# ---- Preferences / settings -------------------------------------------
# See app/preferences.py for the registry these render.

class PreferenceOptionOut(BaseModel):
    value: str
    label: str
    description: str


class PreferenceDefOut(BaseModel):
    key: str
    label: str
    description: str
    group: str
    options: list[PreferenceOptionOut]
    default: str


class UserPreferencesOut(BaseModel):
    values: dict[str, str]


class UserPreferencesUpdate(BaseModel):
    values: dict[str, str]


# ---- Publications ("add a new database") -------------------------------
# See app/models/publication.py - `slug` is exactly what's stored in every
# other table's source_db column, not a new Postgres database.

PUBLICATION_SLUG_PATTERN = r"^[a-z][a-z0-9-]{1,62}[a-z0-9]$"


class PublicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    slug: str
    name: str
    description: str | None = None
    color: str
    icon: str


class PublicationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    # Optional - the route slugifies `name` when omitted. Validated against
    # PUBLICATION_SLUG_PATTERN when given explicitly (lowercase, digits,
    # single hyphens, 3-64 chars) since it becomes a permanent source_db
    # value stamped onto every contact/company created under it.
    slug: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=256)
    color: str = "slate"
    icon: str = "newspaper"


# ---- Users / role-based access ------------------------------------------
# See app/roles.py (what a role grants) and app/models/user_access.py
# (per-user database/group scoping).

class RoleDefOut(BaseModel):
    value: str
    label: str
    description: str


class UserAccessIn(BaseModel):
    source_db: str
    group_id: uuid.UUID | None = None


class UserAccessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    source_db: str
    group_id: uuid.UUID | None = None
    group_name: str | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    role: str
    is_active: bool
    access: list[UserAccessOut] = []


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8)
    role: str
    access: list[UserAccessIn] = []


class UserUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)
    # When provided, replaces the user's entire access list (not a merge) -
    # the admin UI always submits the full desired set, same as how a
    # <select multiple> would.
    access: list[UserAccessIn] | None = None
