/** Types for reminders, notifications, Outlook connection and mail merge -
 * mirrors backend/app/api/routes/messaging.py. */

export type Reminder = {
  id: string;
  due_at: string;
  note: string | null;
  contact_id: string | null;
  company_id: string | null;
  about: string;
  link: string | null;
  email_me: boolean;
  status: "open" | "done" | "cancelled";
  notified_at: string | null;
  created_at: string | null;
};

export type AppNotification = {
  id: string;
  kind: string;
  title: string;
  body: string | null;
  link: string | null;
  created_at: string | null;
  read_at: string | null;
  email_status: string | null;
};

export type MailStatus = {
  configured: boolean;
  connected: boolean;
  email: string | null;
  display_name: string | null;
  connected_at: string | null;
  needs_reconnect: boolean;
  last_error: string | null;
  automation_mailbox: string | null;
  automation_mailbox_ready: boolean;
  per_minute: number;
};

export type MergeField = { key: string; label: string; example: string; group?: "contact" | "brand" | "issue" };

export type TemplateKind = "pitch" | "follow_up" | "event" | "launch" | "renewal" | "general";
export const TEMPLATE_KIND_LABEL: Record<TemplateKind, string> = {
  pitch: "Pitch a feature or issue", follow_up: "Follow-up", event: "Event invitation", launch: "New title or product", renewal: "Renewal", general: "General",
};
export const BRAND_LABEL: Record<string, string> = { obh: "Onboard Hospitality", tbtm: "The Business Travel Magazine", stm: "Selling Travel" };
export type ComposeResult = {
  to: string[]; subject: string; body: string; html: string; missing: string[]; unknown_fields: string[]; unsubscribed: boolean;
  outlook_connected: boolean; outlook_email: string | null;
};

export type MailTemplate = {
  id: string;
  name: string;
  subject: string | null;
  body: string;
  shared: boolean;
  mine: boolean;
  owner_name: string | null;
  updated_at: string | null;
  brand?: string | null;
  title_id?: string | null;
  title_name?: string | null;
  kind?: TemplateKind;
  kind_label?: string;
  description?: string | null;
  source?: string | null;
  needs_check?: boolean;
  use_count?: number;
  last_used_at?: string | null;
  can_edit?: boolean;
  uses_issue?: boolean;
};

export type RecipientSource =
  | { kind: "group"; group_id: string }
  | { kind: "company"; company_id: string }
  | { kind: "contacts"; contact_ids: string[] }
  | {
      kind: "lookup";
      q?: string;
      source_db?: string;
      company?: string;
      city?: string;
      country?: string;
      title?: string;
      sort?: string;
      desc?: boolean;
      conds?: string;
      match?: string;
    };

export type Recipient = {
  contact_id: string;
  name: string;
  company: string | null;
  email: string | null;
  city: string | null;
  country: string | null;
  has_address: boolean;
  unsubscribed: boolean;
  bounced: boolean;
};

export type RecipientsResult = { label: string; total: number; truncated: boolean; items: Recipient[] };

export type MergeOutput = "email" | "word" | "labels" | "data";

export type MailMergeSummary = {
  id: string;
  output: MergeOutput;
  source_label: string | null;
  subject: string | null;
  status: "queued" | "sending" | "done" | "cancelled" | "failed";
  total: number;
  sent: number;
  failed: number;
  skipped: number;
  error: string | null;
  from_email: string | null;
  created_at: string | null;
  finished_at: string | null;
  created_by: string | null;
  letters_for_no_email?: number;
};

export type Attachment = { id: string; filename: string; size: number; content_type: string };

export type MailMergeDetail = MailMergeSummary & {
  body: string;
  cc: string | null;
  bcc: string | null;
  record_history: string;
  attachments: Attachment[];
  recipients: {
    contact_id: string | null;
    name: string | null;
    email: string | null;
    status: string;
    error: string | null;
    sent_at: string | null;
  }[];
};

export type MergeRequest = {
  output: MergeOutput;
  source_label?: string;
  contact_ids: string[];
  subject?: string;
  body: string;
  cc?: string;
  bcc?: string;
  attachment_ids?: string[];
  record_history: "email_full" | "subject_only" | "none";
  history_regarding?: string;
  no_email: "skip" | "letters";
  include_unsubscribed: boolean;
  data_format: "xlsx" | "csv";
  test_only?: boolean;
  brand?: string | null;
  edition_id?: string | null;
  feature?: string | null;
  template_id?: string | null;
};
