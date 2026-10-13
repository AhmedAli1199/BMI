/** Sections an administrator can hide from other roles (keys match
 * backend/app/ui_sections.py). Hiding only tidies the navigation; what a
 * person may open or change is still decided by their role and access. */
export type SectionKey =
  | "contacts"
  | "companies"
  | "groups"
  | "calendar"
  | "reminders"
  | "calls"
  | "mail_merge"
  | "email_templates"
  | "sales_overview"
  | "sales_dashboard"
  | "editions"
  | "bookings"
  | "renewals"
  | "proposals"
  | "orders"
  | "rate_card"
  | "invoicing"
  | "commissions"
  | "editorial"
  | "today"
  | "review_queue"
  | "automations_hub"
  | "data_health";

export type SectionDef = { key: SectionKey; label: string; group: string; description: string };

export type SectionsInfo = {
  sections: SectionDef[];
  roles: string[];
  hidden: Record<string, SectionKey[]>;
  /** People with their own choice (replaces their role's): user id -> hidden sections. */
  users: Record<string, SectionKey[]>;
  people: { id: string; name: string; role: string }[];
  mine: SectionKey[];
};
