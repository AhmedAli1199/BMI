export type RepRef = { id: string; code: string; name: string; active: boolean; has_login: boolean };

export type NewBusinessStatus = "new" | "returning" | "check";

export type CommissionLine = {
  order_id: string;
  edition_id: string;
  edition: string;
  title: string;
  title_slug: string;
  group: string;
  publication: string | null;
  earned_on: string;
  booked_on: string | null;
  client: string;
  company_id: string | null;
  size: string | null;
  value_gbp: number;
  share_gbp: number;
  split: boolean;
  agency_cut: boolean;
  base_rate: number;
  base_source: string;
  base_gbp: number;
  new_business: NewBusinessStatus;
  new_business_reason: string;
  new_business_decided_by: "history" | "manager";
  new_business_rate: number;
  new_business_gbp: number;
  commission_gbp: number;
  flags: string[];
};

export type CommissionBonus = { kind: "new_client" | "new_guide" | "threshold"; label: string; group: string; amount_gbp: number; reason: string; order_id?: string; edition_id?: string };
export type CommissionEvent = {
  edition_id: string; edition: string; event_date: string | null; income_gbp: number; costs_gbp: number; profit_gbp: number;
  rate: number; amount_gbp: number; group: string; basis: string; loss: boolean;
};
export type CommissionAdjustment = { period: string; amount_gbp: number; label: string };

export type CommissionRule = {
  id: string;
  rep_id: string;
  name: string;
  title_slugs: string[];
  base_rate: number;
  new_business_rate: number;
  new_business_rate_change_on: string | null;
  new_business_rate_after: number | null;
  new_guide_bonus_gbp: number | null;
  threshold_bonus_gbp: number | null;
  threshold_gbp: number | null;
  new_client_bonus_gbp: number | null;
  event_profit_rate: number | null;
  valid_from: string | null;
  valid_until: string | null;
  notes: string | null;
};
export type CommissionRuleInput = Omit<CommissionRule, "id">;

export type CommissionSettings = { earned_on: "publication" | "booked"; lookback_months: number; first_deal_days: number; event_profit_basis: "all" | "own" };

export type CommissionStatement = {
  period: string;
  rep: RepRef;
  lines: CommissionLine[];
  bonuses: CommissionBonus[];
  events: CommissionEvent[];
  adjustments: CommissionAdjustment[];
  groups: { name: string; share_gbp: number; base_gbp: number; new_business_gbp: number; commission_gbp: number; bookings: number }[];
  totals: { share_gbp: number; base_gbp: number; new_business_gbp: number; bonuses_gbp: number; event_profit_gbp: number; core_gbp: number; adjustments_gbp: number; total_gbp: number };
  checks: number;
  flags: string[];
  approved: { at: string | null; by: string | null; by_name?: string | null; changed_since_gbp: number } | null;
  can_approve: boolean;
  can_decide: boolean;
  plan: CommissionRule[];
  settings: CommissionSettings;
};

export type CommissionOverview = {
  year: number;
  reps: { rep: RepRef; months: { period: string; total_gbp: number; approved: boolean; checks: number; bookings: number }[]; year_total_gbp: number; checks: number; has_plan: boolean }[];
  scoped_to_me: boolean;
  can_manage: boolean;
  has_plans: boolean;
};

export type CommissionPlans = {
  reps: (RepRef & { default_rate: number; rules: CommissionRule[] })[];
  titles: { slug: string; name: string }[];
  settings: CommissionSettings;
  can_edit: boolean;
  seed_available: boolean;
};

export type BookingNewBusiness = { status: NewBusinessStatus; reason: string; decided_by: "history" | "manager"; last: { label: string; day: string; value: number; order_id: string | null } | null; similar: string | null; can_decide: boolean };

export type EditionCommission = {
  new_contract_guide: boolean;
  new_contract_rep: RepRef | null;
  guide_title: boolean;
  profit_share: boolean;
  profit_share_reps: RepRef[];
  costs_final_at: string | null;
  costs_final_by: string | null;
  costs_signed_off_at: string | null;
  costs_signed_off_by: string | null;
  can_mark_guide: boolean;
  can_mark_final: boolean;
  can_sign_off: boolean;
};

export const NB_LABEL: Record<NewBusinessStatus, string> = { new: "New business", returning: "Returning", check: "Needs a decision" };
