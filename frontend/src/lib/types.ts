export type ContactListItem = {
  id: string;
  source_db: string;
  full_name: string | null;
  first_name: string | null;
  last_name: string | null;
  job_title: string | null;
  company_id: string | null;
  company_name: string | null;
  primary_email: string | null;
};

export type Page<T> = { items: T[]; total: number; page: number; page_size: number };

export type RecordPosition = {
  position: number | null;
  total: number;
  prev_id: string | null;
  next_id: string | null;
  first_id: string | null;
  last_id: string | null;
};

export type AddressOut = {
  id: string; type_label: string | null;
  line1: string | null; line2: string | null; line3: string | null;
  city: string | null; state: string | null; postal_code: string | null; country: string | null;
};
export type PhoneOut = { id: string; type_label: string | null; number: string | null };
export type EmailOut = { id: string; type_label: string | null; address: string | null };
export type UserSummary = { id: string; name: string };
export type NoteOut = {
  id: string;
  note_type: string | null;
  body: string | null;
  is_private: boolean;
  act_created_at: string | null;
  created_by: UserSummary | null;
  // One of the real Act! source databases, or "manual" for anything
  // written directly in this CRM (by a person via the UI, or by an
  // automation) - see noteSourceLabel() in act-tab-workstation.tsx for
  // how "manual" is split into a real name vs. "AI / Automation".
  source_db: string;
};
export type HistoryOut = {
  id: string;
  history_type: string;
  subject: string | null;
  details: string | null;
  duration_minutes: number | null;
  is_private: boolean;
  occurred_at: string;
  created_by: UserSummary | null;
};
/** "never" is the only value the UI offers today - see backend's
 * app/models/activity.py RECURRENCE_VALUES for the other three. */
export type ActivityRecurrence = "never" | "daily" | "weekly" | "monthly";
export type ActivityPriority = "high" | "normal" | "low";

export type ActivityOut = {
  id: string;
  activity_type: string | null;
  subject: string | null;
  details: string | null;
  location: string | null;
  start_at: string;
  end_at: string | null;
  is_timeless: boolean;
  is_cleared: boolean;
  is_private: boolean;
  priority?: ActivityPriority | string;
  duration_minutes?: number | null;
  organized_by_name?: string | null;
  has_attachments?: boolean;
  recurrence: ActivityRecurrence;
  contact_id: string | null;
  company_id: string | null;
  contact_name: string | null;
  company_name: string | null;
  created_by: UserSummary | null;
};

export type GroupOut = { id: string; name: string };

export type FieldChange = {
  id: string;
  field: string;
  old_value: string | null;
  new_value: string | null;
  changed_at: string;
  changed_by: UserSummary | null;
};
export type CompanySummary = { id: string; name: string; source_db: string; industry: string | null; category: string | null };

export type ContactDetail = {
  id: string;
  source_db: string;
  source_act_id: string;
  first_name: string | null;
  middle_name: string | null;
  last_name: string | null;
  full_name: string | null;
  job_title: string | null;
  department: string | null;
  category: string | null;
  referred_by: string | null;
  birthdate: string | null;
  last_meet_date: string | null;
  last_reach_date: string | null;
  last_attempt_date: string | null;
  last_letter_date: string | null;
  is_unsubscribed: boolean;
  custom_fields: Record<string, unknown>;
  company: CompanySummary | null;
  addresses: AddressOut[];
  phones: PhoneOut[];
  emails: EmailOut[];
  groups: GroupOut[];
  notes: NoteOut[];
  history: HistoryOut[];
  activities: ActivityOut[];
};

export type CompanyListItem = {
  id: string;
  source_db: string;
  name: string;
  industry: string | null;
  category: string | null;
  contact_count: number;
};

export type CompanyDetail = {
  id: string;
  source_db: string;
  source_act_id: string;
  name: string;
  description: string | null;
  industry: string | null;
  category: string | null;
  territory: string | null;
  region: string | null;
  website: string | null;
  num_employees: number | null;
  custom_fields: Record<string, unknown>;
  addresses: AddressOut[];
  phones: PhoneOut[];
  emails: EmailOut[];
  contacts: ContactListItem[];
  notes: NoteOut[];
  history: HistoryOut[];
  activities: ActivityOut[];
};

export type GroupListItem = {
  id: string;
  name: string;
  description: string | null;
  member_count: number;
  hier_level: number | null;
  parent_group_id: string | null;
};

export type GroupDetail = {
  id: string;
  source_db: string;
  name: string;
  description: string | null;
  parent_group_id: string | null;
  members: ContactListItem[];
};

export type ActivitiesPage = Page<ActivityOut>;

export type SourceBreakdown = { source_db: string; count: number };

export type RecentContact = {
  id: string;
  full_name: string | null;
  first_name: string | null;
  last_name: string | null;
  job_title: string | null;
  company_id: string | null;
  company_name: string | null;
  created_at: string;
};

export type RecentCompany = {
  id: string;
  name: string;
  industry: string | null;
  created_at: string;
};

export type TopCompany = {
  id: string;
  name: string;
  industry: string | null;
  contact_count: number;
};

export type DashboardStats = {
  total_contacts: number;
  total_companies: number;
  total_groups: number;
  contacts_by_source: SourceBreakdown[];
  companies_by_source: SourceBreakdown[];
  recent_contacts: RecentContact[];
  recent_companies: RecentCompany[];
  top_companies: TopCompany[];
};

// ---- Automations / review queue --------------------------------------------
// Mirrors backend/app/automations/registry.py - see its docstring for the
// full contract. The frontend renders entirely from this data, so a new
// automation kind shows up here with zero frontend code changes.

export type ReviewExtraField = {
  key: string;
  label: string;
  placeholder: string;
  required: boolean;
  field_type: "text" | "bool";
};

export type ReviewAction = {
  id: string;
  label: string;
  style: "primary" | "secondary" | "destructive";
  outcome: "approved" | "rejected";
  requires_note: boolean;
  requires_contact_picker: boolean;
  extra_fields: ReviewExtraField[];
  confirm_message: string | null;
  requires_related_entity_choice: boolean;
};

export type ReviewKind = {
  kind: string;
  label: string;
  description: string;
  actions: ReviewAction[];
  /** Phase 1 labeling only (see backend registry.py's ReviewKind.audience)
   * - not yet enforced; "sales" vs "admin" who a kind is meant for. */
  audience: "sales" | "admin";
};

export type ReviewDetail = { key?: string; label: string; value: string; editable?: boolean };
export type ReviewRelatedEntity = { type: "contact" | "company"; id: string; label: string };
export type ReviewCandidate = { contact_id?: string; label?: string; source?: string };

export type ReviewPayload = {
  summary?: string;
  details?: ReviewDetail[];
  original_text?: string;
  source_context?: string | null;
  related_entities?: ReviewRelatedEntity[];
  suggested_contact?: { id: string; label: string } | null;
  candidate?: ReviewCandidate | null;
  confidence?: number | null;
  /** Keyed to match ReviewAction.extra_fields[].key exactly - whatever an
   * automation could confidently identify (a signature parse, a domain
   * match) pre-filled into that action's form, never a guess it can't
   * back up. Generic across every kind: any automation can set this and
   * the form seeds itself from it, no per-kind frontend wiring needed. */
  prefill?: Record<string, string>;
  source_db?: string;
  signature?: {
    full_name?: string | null;
    job_title?: string | null;
    company_name?: string | null;
    phone?: string | null;
    mobile?: string | null;
  } | null;
  replacements?: Array<{
    name?: string | null;
    email?: string | null;
    phone?: string | null;
    role?: string | null;
  }> | null;
  card?: {
    full_name?: string | null;
    job_title?: string | null;
    company_name?: string | null;
    email?: string | null;
    phone?: string | null;
    mobile?: string | null;
  } | null;
  suggested_groups?: string[] | null;
  [key: string]: unknown;
};

export type ReviewQueueItem = {
  id: string;
  kind: string;
  source_db: string | null;
  entity_type: string | null;
  entity_id: string | null;
  payload: ReviewPayload;
  status: string;
  resolved_action: string | null;
  review_note: string | null;
  reviewed_at: string | null;
  created_at: string;
};

export type ReviewQueueCounts = { kind: string; pending: number; approved: number; rejected: number };

export type ReviewQueueInsightBucket = { key: string; label: string; count: number };
export type ReviewQueueInsights = { kind: string; buckets: ReviewQueueInsightBucket[] };

export type DataHealthMetric = {
  key: string;
  label: string;
  description: string;
  count: number;
  total: number;
  entity_type: "contact" | "company" | null;
  review_kind: string | null;
};

export type DataHealthStats = {
  total_contacts: number;
  total_companies: number;
  metrics: DataHealthMetric[];
};

/** SALES-013's read side - a ReviewQueueItem (same shape, so it feeds
 * straight into ReviewItemCard) plus which rep it belongs to. See
 * backend's app/automations/morning_queue.py. */
export type TodayItem = ReviewQueueItem & { owner_user_id: string | null; owner_name: string };

export type ScheduledJob = {
  id: string;
  label: string;
  description: string;
  cron: string;
  enabled: boolean;
  has_cursor: boolean;
};

export type AutomationSettingType = "bool" | "int" | "float" | "csv" | "text";

export type AutomationSetting = {
  key: string;
  label: string;
  description: string;
  group: string;
  type: AutomationSettingType;
  value: boolean | number | string;
  default: boolean | number | string;
  is_overridden: boolean;
  min: number | null;
  max: number | null;
};

// Mirrors backend/app/api/schemas.py's LlmUsage* shapes - see
// GET /api/automations/llm-usage (backend/app/automations/llm.py logs one
// LlmUsageEvent per real Gemini/OpenAI call; this is the aggregated view).
export type LlmUsageBucket = {
  bucket_start: string;
  call_count: number;
  success_count: number;
  failure_count: number;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
};

export type LlmUsageByPurpose = {
  purpose: string;
  provider: string;
  call_count: number;
  failure_count: number;
  cost_usd: number;
};

export type LlmUsageSummary = {
  range_start: string;
  range_end: string;
  total_calls: number;
  total_failures: number;
  total_cost_usd: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  buckets: LlmUsageBucket[];
  by_purpose: LlmUsageByPurpose[];
};

export type PreferenceOption = { value: string; label: string; description: string };

export type PreferenceDef = {
  key: string;
  label: string;
  description: string;
  group: string;
  options: PreferenceOption[];
  default: string;
};

export type UserPreferences = { values: Record<string, string> };

export type Publication = {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  color: string;
  icon: string;
};

export type RoleDef = { value: string; label: string; description: string };

export type UserAccessEntry = { source_db: string; group_id: string | null; group_name: string | null };

export type UserAccount = {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  access: UserAccessEntry[];
};
