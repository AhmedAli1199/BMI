export type ProposalSection = { id: string; kind: string; heading: string; body: string };
export type ProposalLine = { id?: string; product: string; qty: number; unit_price: number | null; source: "rate_card" | "manual"; rate_id?: string | null };

export type ProposalHistoryBooking = { title: string; edition: string; year: number; size: string | null; value_gbp: number; booked_on: string | null };
export type ProposalContext = {
  company?: string;
  title?: string | null;
  year?: number;
  history?: { count: number; total_gbp: number; by_year: Record<string, number>; bookings: ProposalHistoryBooking[] };
  rates?: { id: string; product: string; price_gbp: number; notes: string | null }[];
};

export type Proposal = {
  id: string;
  company_id: string;
  company_name: string;
  contact_id: string | null;
  title_id: string | null;
  title_name: string | null;
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
};

export const TEMPLATE_OPTIONS: { value: Proposal["template"]; label: string }[] = [
  { value: "obh", label: "Onboard Hospitality" },
  { value: "stm", label: "Selling Travel" },
  { value: "tbtm", label: "The Business Travel Magazine" },
];
