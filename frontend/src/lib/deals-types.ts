export type DealStatus = "pencilled" | "confirmed" | "cancelled";

export type DealPlacement = {
  order_id?: string | null;
  edition_id?: string | null;
  item_date?: string | null;
  copy_due?: string | null;
  note?: string | null;
  booked_on?: string | null;
  value_gbp?: number;
  agency_gbp?: number;
};

export type DealLine = {
  key?: string | null;
  title_id?: string | null;
  rate_id?: string | null;
  description: string;
  detail?: string | null;
  size?: string | null;
  qty: number;
  unit_price?: number | null;
  list_price?: number | null;
  discount_pct: number;
  added_value: boolean;
  share_gbp?: number | null;
  placements: DealPlacement[];
  total_gbp?: number;
};

export type DealInput = {
  company_id: string | null;
  client_name: string;
  contact_id: string | null;
  contact_name: string | null;
  contact_email: string | null;
  confirmation_address: string | null;
  invoice_to: string | null;
  invoice_email: string | null;
  po_number: string | null;
  agency_name: string | null;
  agency_pct: number;
  rep_id: string | null;
  split: { rep_id: string; pct: number }[];
  booked_on: string | null;
  title_id: string | null;
  publication_label: string | null;
  insertions_label: string | null;
  document: "confirmation" | "schedule";
  pricing: "items" | "package";
  package_price_gbp: number | null;
  package_label: string | null;
  package_split: "rate_card" | "even" | "manual";
  discount_pct: number;
  lines: DealLine[];
  invoice_plan: "upfront" | "on_publication" | "custom";
  special_instructions: string | null;
  copy_instructions: string | null;
  production_contact: string | null;
  show_artwork_specs: boolean;
  notes: string | null;
  proposal_id: string | null;
  status?: "pencilled" | "confirmed";
};

export type DealTotals = {
  gross_gbp: number; discount_gbp: number; total_gbp: number; agency_gbp: number; payable_gbp: number;
  rate_card_gbp: number; added_value_gbp: number; off_rate_card_pct: number | null; invoiced_gbp: number; to_invoice_gbp: number;
};

export type DealScheduleRow = {
  order_id: string | null; line: string; description: string; edition_id: string | null; edition: string | null; title: string | null;
  runs_on: string | null; ad_deadline: string | null; copy_due: string | null; value_gbp: number; agency_gbp: number; added_value: boolean;
  status: string | null; invoice_number: string | null; xero_state: string | null; booked_on: string | null; published: boolean; ready_to_invoice: boolean;
};

export type Deal = Omit<DealInput, "status"> & {
  id: string;
  number: number;
  status: DealStatus;
  rep: { id: string; code: string; name: string } | null;
  split_names: { rep_id: string; name: string; pct: number }[];
  totals: DealTotals;
  schedule: DealScheduleRow[];
  warnings: string[];
  insertions: string;
  rebooked_from_id: string | null;
  rebooked_from_number: number | null;
  confirmed_at: string | null;
  sent_at: string | null;
  sent_to: string | null;
  cancelled_reason: string | null;
  created_at: string | null;
  can_edit: boolean;
  notes_after_save?: string[];
};

export type DealListItem = {
  id: string; number: number; status: DealStatus; client_name: string; company_id: string | null; rep: string | null; booked_on: string;
  total_gbp: number; items: number; first: string | null; last: string | null; invoiced_gbp: number; sent_at: string | null;
  po_number: string | null; agency_name: string | null;
};

export type DealPreview = {
  error?: string;
  lines?: { total_gbp: number; placements: number[] }[];
  gross_gbp?: number; discount_gbp?: number; total_gbp?: number; agency_gbp?: number; payable_gbp?: number;
  rate_card_gbp?: number; added_value_gbp?: number; off_rate_card_pct?: number | null; warnings?: string[];
};

export type DealIssue = { id: string; label: string; kind: string; edition_date: string | null; ad_deadline: string | null; copy_deadline: string | null; open: boolean; status: string };

export type DealPrefill = Partial<DealInput> & {
  company?: { id: string; label: string };
  contact?: { id: string; label: string };
  last_order?: { id: string; number: number };
};

export type DealDocument = {
  number: number; status: DealStatus; document: string; heading: string; subheading: string | null; date: string;
  company_block: string; footer: string; terms: string; artwork_specs: string | null;
  confirmation_address: string; invoice_to: string; your_contact: string | null; your_email: string | null; our_contact: string | null; our_email: string | null;
  order_ref: string | null; invoice_email: string | null; intro: string; publication: string | null; insertions: string;
  package: { label: string; price: number } | null;
  rows: { description: string; when: string[]; insertions: number; detail: string | null; added_value: boolean; qty: number; each: number | null; total: number | null; note: string | null }[];
  gross: number; discount_pct: number; discount: number; total: number; agency_pct: number; agency: number; agency_name: string | null; payable: number;
  special_instructions: string | null; copy_instructions: string | null; copy_dates: { date: string; item: string; dates: string }[]; production_contact: string | null;
};

export type DealEmailDraft = { to: string[]; cc: string[]; subject: string; body: string; outlook_connected: boolean; outlook_email: string | null };

export type DealSettings = { next_number: number; company_block: string; footer: string; terms: string; artwork_specs: string; can_edit: boolean };

export const DEAL_STATUS_LABEL: Record<DealStatus, string> = { pencilled: "Pencilled", confirmed: "Confirmed", cancelled: "Cancelled" };
