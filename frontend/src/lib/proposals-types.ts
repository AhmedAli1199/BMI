export type ProposalSection = { id: string; kind: string; heading: string; body: string };
export type ProposalLine = {
  id?: string; product: string; qty: number; unit_price: number | null; source: "rate_card" | "manual" | "offer"; rate_id?: string | null;
  /** A line can be for another title than the proposal's (a newsletter, the awards). */
  title_id?: string | null;
  /** The issues it runs in - sets the quantity. */
  issues?: string[];
  issue_labels?: string[];
  discount_pct?: number;
  /** "Option A: one issue" - lines without one are part of every option. */
  option?: string | null;
  list_price?: number | null;
};

export type ProposalKind = "issue" | "multi" | "annual" | "digital" | "sponsorship" | "mixed";
export type ProposalTotal = { option: string | null; subtotal_gbp: number; discount_gbp: number; total_gbp: number; rate_card_gbp: number; lines: number };

export type ProposalHistoryBooking = { title: string; edition: string; year: number; size: string | null; value_gbp: number; booked_on: string | null };
export type ProposalContext = {
  company?: string;
  title?: string | null;
  year?: number;
  history?: { count: number; total_gbp: number; by_year: Record<string, number>; bookings: ProposalHistoryBooking[] };
  rates?: { id: string; product: string; price_gbp: number; notes: string | null }[];
  issue?: ProposalIssue | null;
};

/** The issue a proposal is for, from the editorial plan. */
export type ProposalIssue = {
  id: string;
  label: string;
  name: string;
  kind: string;
  publication: string | null;
  publication_text: string;
  ad_deadline: string | null;
  ad_deadline_text: string;
  theme: string | null;
  distribution: string | null;
  period: string | null;
  features: string[];
  sponsorable: string[];
};

export type UpcomingIssue = { id: string; label: string; kind: string; edition_date: string | null; ad_deadline: string | null; open: boolean; suggested: boolean };

export type Proposal = {
  id: string;
  company_id: string;
  company_name: string;
  contact_id: string | null;
  title_id: string | null;
  title_name: string | null;
  edition_id: string | null;
  issue: ProposalIssue | null;
  template: "obh" | "stm" | "tbtm";
  template_label: string;
  campaign_name: string;
  status: "draft" | "sent";
  sections: ProposalSection[];
  lines: (ProposalLine & { unit_price: number })[];
  total_gbp: number;
  context: ProposalContext;
  flags: string[];
  drafted_by: "ai" | "template";
  created_by: string | null;
  created_at: string;
  sent_at: string | null;
  sent_via: string | null;
  follow_up_due: string | null;
  notes: string | null;
  kind: ProposalKind;
  kind_label: string;
  discount_pct: number;
  totals: ProposalTotal[];
  titles: string[];
  kinds: Record<ProposalKind, string>;
};

export const KIND_OPTIONS: { value: ProposalKind; label: string }[] = [
  { value: "issue", label: "A single issue" },
  { value: "multi", label: "Several issues" },
  { value: "annual", label: "A year's programme" },
  { value: "digital", label: "Digital (website, newsletters, social)" },
  { value: "sponsorship", label: "Awards or event sponsorship" },
  { value: "mixed", label: "A mixed package" },
];

export const TEMPLATE_OPTIONS: { value: Proposal["template"]; label: string }[] = [
  { value: "obh", label: "Onboard Hospitality" },
  { value: "stm", label: "Selling Travel" },
  { value: "tbtm", label: "The Business Travel Magazine" },
];

export type ProposalEmailDraft = {
  to: string[];
  subject: string;
  body: string;
  outlook_connected: boolean;
  outlook_email: string | null;
  contact_name: string | null;
};
