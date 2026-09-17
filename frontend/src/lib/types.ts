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
};

export type ReviewKind = {
  kind: string;
  label: string;
  description: string;
  actions: ReviewAction[];
};

export type ReviewDetail = { key?: string; label: string; value: string; editable?: boolean };
export type ReviewRelatedEntity = { type: "contact" | "company"; id: string; label: string };
export type ReviewCandidate = { contact_id?: string; label?: string; source?: string };

export type ReviewPayload = {
  summary?: string;
  details?: ReviewDetail[];
  original_text?: string;
  related_entities?: ReviewRelatedEntity[];
  suggested_contact?: { id: string; label: string } | null;
  candidate?: ReviewCandidate | null;
  confidence?: number | null;
};

export type ReviewQueueItem = {
  id: string;
  kind: string;
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

export type ScheduledJob = { id: string; label: string; description: string; cron: string; enabled: boolean };

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
