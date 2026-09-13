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

export type AddressOut = {
  id: string; type_label: string | null;
  line1: string | null; line2: string | null;
  city: string | null; state: string | null; postal_code: string | null; country: string | null;
};
export type PhoneOut = { id: string; type_label: string | null; number: string | null };
export type EmailOut = { id: string; type_label: string | null; address: string | null };
export type NoteOut = { id: string; note_type: string | null; body: string | null; act_created_at: string | null };
export type HistoryOut = { id: string; history_type: string; subject: string | null; occurred_at: string };
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
  custom_fields: Record<string, unknown>;
  company: CompanySummary | null;
  addresses: AddressOut[];
  phones: PhoneOut[];
  emails: EmailOut[];
  groups: GroupOut[];
  notes: NoteOut[];
  history: HistoryOut[];
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
};

export type GroupListItem = {
  id: string;
  name: string;
  description: string | null;
  member_count: number;
};

export type GroupDetail = {
  id: string;
  name: string;
  description: string | null;
  parent_group_id: string | null;
  members: ContactListItem[];
};
