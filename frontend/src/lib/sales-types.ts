/** Types for the Sales Order Register - mirrors backend/app/api/routes/sales.py. */

export type OrderStatus = "booked" | "cancelled" | "contra" | "moved";
export type ProductLine = "print" | "digital" | "events" | "awards";

export type SalesTitle = {
  id: string;
  slug: string;
  name: string;
  product_line: ProductLine;
  crm_source_db: string;
  /** Online-edition link templates - {edition}, {year}, {page} placeholders. */
  digital_page_url?: string | null;
  digital_issue_url?: string | null;
};

export type SalesRate = {
  id: string;
  title_id: string;
  year: number;
  product: string;
  price_gbp: number;
  notes: string | null;
};

export type RenewalPassResult = {
  previous_edition: string;
  advertisers: number;
  queued: number;
  already_booked: number;
  already_queued: number;
};

export type SalesRep = {
  id: string;
  code: string;
  name: string;
  active: boolean;
  has_login: boolean;
  commission_rate: number;
};

export type SalesMeta = {
  titles: SalesTitle[];
  reps: SalesRep[];
  years: number[];
  my_rep_id: string | null;
  can_see_all_commission: boolean;
};

export type Ref = { id: string; label: string };

export type Credit = { rep_id: string; code: string; name: string; amount_gbp: number };

export type SalesOrder = {
  id: string;
  edition_id: string;
  edition_label: string;
  title_id: string;
  client_name: string;
  company: Ref | null;
  match_dismissed: boolean;
  rep: SalesRep | null;
  credits: Credit[];
  booked_on: string | null;
  size: string | null;
  pages: number | null;
  series: string | null;
  position: string | null;
  rate_usd: number | null;
  value_gbp: number;
  agency_commission_gbp: number | null;
  commission_rate: number | null;
  invoice_number: string | null;
  invoice_value_gbp: number | null;
  invoiced_on: string | null;
  invoice_note: string | null;
  order_ref: string | null;
  status: OrderStatus;
  status_reason: string | null;
  extra: Record<string, string>;
  moved_to: Ref | null;
  notes: string | null;
  import_warning: string | null;
  source: string | null;
  edition_date: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type EditionSummary = {
  id: string;
  title: SalesTitle;
  year: number;
  name: string;
  label: string;
  period_label: string | null;
  edition_date: string | null;
  kind: "issue" | "month" | "event" | "awards" | "guide";
  status: "open" | "closed";
  exchange_rate: number | null;
  target_gbp: number | null;
  booked_gbp: number;
  orders: number;
  invoiced_gbp: number;
  uninvoiced: number;
  paid_orders: number;
  invoiced_orders: number;
  pages: number;
  warnings: number;
  sheet_total_gbp: number | null;
  previous: Ref | null;
  previous_booked_gbp: number | null;
  previous_same_point_gbp: number | null;
};

export type EditionDetail = EditionSummary & {
  notes: string | null;
  source: string | null;
  orders_list: SalesOrder[];
  by_rep: Credit[];
  cancelled_or_moved: number;
  next_edition: Ref | null;
  prev_in_year: Ref | null;
  next_in_year: Ref | null;
  digital_url: string | null;
  renews_from: Ref | null;
};

export type OrdersPage = { items: SalesOrder[]; total: number; total_value_gbp: number };

export type SalesOverview = {
  year: number;
  as_of: string;
  is_current_year: boolean;
  booked_gbp: number;
  last_year_same_point_gbp: number;
  last_year_total_gbp: number;
  invoiced_gbp: number;
  uninvoiced_count: number;
  uninvoiced_gbp: number;
  orders: number;
  advertisers: number;
  new_advertisers: number;
  renewal_candidates: number;
  monthly: { month: number; this_year: number; last_year: number }[];
  by_title: {
    title: SalesTitle;
    booked_gbp: number;
    orders: number;
    last_year_same_point_gbp: number;
    last_year_total_gbp: number;
    advertisers: number;
  }[];
  by_rep: { rep: SalesRep; credit_gbp: number; orders: number }[];
  upcoming: EditionSummary[];
};

export type Commissions = {
  year: number;
  scoped_to_me: boolean;
  reps: {
    rep: SalesRep;
    credit_gbp: number;
    commission_gbp: number;
    orders: number;
    editions: { edition: Ref; title: string; edition_date: string | null; credit_gbp: number; commission_gbp: number; orders: number }[];
  }[];
};

export type Renewals = {
  title: SalesTitle;
  year: number;
  previous_advertisers: number;
  rebooked: number;
  retention_rate: number | null;
  not_rebooked_value_gbp: number;
  items: {
    client_name: string;
    company: Ref | null;
    rep: SalesRep | null;
    last_edition: Ref;
    last_booked_on: string | null;
    last_value_gbp: number;
    last_year_value_gbp: number;
    last_year_orders: number;
    size: string | null;
  }[];
};

export type CompanyBookings = {
  lifetime_gbp: number;
  orders: number;
  first_booked: string | null;
  last_booked: string | null;
  titles: string[];
  by_year: Record<string, number>;
  items: SalesOrder[];
};

export type ClientSuggestion = { client_name: string; company: Ref | null; orders: number };

export type OrderInput = {
  client_name?: string;
  company_id?: string | null;
  clear_company?: boolean;
  rep_id?: string | null;
  booked_on?: string | null;
  size?: string | null;
  series?: string | null;
  position?: string | null;
  rate_usd?: number | null;
  value_gbp?: number;
  agency_commission_gbp?: number | null;
  commission_rate?: number | null;
  invoice_number?: string | null;
  invoice_value_gbp?: number | null;
  invoiced_on?: string | null;
  invoice_note?: string | null;
  status?: OrderStatus;
  moved_to_edition_id?: string | null;
  notes?: string | null;
  credits?: { rep_id: string; amount_gbp: number }[];
  clear_warning?: boolean;
};

export type PaceState = "behind" | "on_pace" | "ahead" | "not_comparable";

export type PaceRow = {
  edition: Ref;
  title: SalesTitle;
  edition_date: string | null;
  kind: string;
  booked_gbp: number;
  orders: number;
  previous: Ref | null;
  previous_point_gbp: number | null;
  previous_point_orders: number | null;
  previous_total_gbp: number | null;
  gap_gbp: number | null;
  gap_pct: number | null;
  state: PaceState;
  reason: string | null;
};

export type SalesDashboard = {
  as_of: string;
  threshold_pct: number;
  min_prior_gbp: number;
  min_prior_orders: number;
  pace: PaceRow[];
  weekly: { week_start: string; orders: number; value_gbp: number; last_year_value_gbp: number }[];
  activity_days: number;
  activity: {
    rep: SalesRep;
    bookings: number;
    booked_gbp: number;
    followups_actioned: number | null;
    followups_outstanding: number | null;
  }[];
  unattributed: { orders: number; value_gbp: number };
  unattributed_year: number;
};

export type SummarySection = {
  key: string;
  title: string;
  paragraphs: string[];
  bullets: { text: string; href: string | null }[];
};

export type WeeklySummaryListItem = { id: string; week_of: string; source: "ai" | "template"; generated_at: string; headline: string };
export type WeeklySummary = WeeklySummaryListItem & { brief_markdown: string; sections: SummarySection[]; metrics_snapshot: Record<string, unknown> };

export type ManagementAlert = {
  id: string;
  subject_type: string;
  subject_id: string;
  subject_label: string;
  comparison_label: string | null;
  prior_value: number;
  current_value: number;
  gap: number;
  gap_pct: number;
  message: string;
  records_ref: { type: string; id: string; label: string }[];
  fired_at: string;
};
