export type Milestone = { label: string; date: string };
export type IssueKind = "issue" | "event" | "awards" | "guide";
export type IssueFormat = "print_digital" | "print" | "digital" | "event" | "awards";

export type Issue = {
  id: string; brand: string; brand_name: string; title_id: string; title_name: string; year: number; name: string; kind: IssueKind;
  format: IssueFormat | null; period_label: string | null; edition_date: string | null; editorial_deadline: string | null;
  ad_deadline: string | null; copy_deadline: string | null; milestones: Milestone[]; theme: string | null; distribution: string | null;
  features: number; needs_check: boolean; booked_gbp: number; orders: number; status: string;
};
export type Feature = { id: string; title: string; description: string | null; status: "planned" | "confirmed" | "dropped"; sponsorable: boolean; sort_order: number };
export type DeadlineRule = { key: string; label: string; kind: "days_before" | "day_prev_month"; value: number };
export type RegularSection = { name: string; description: string | null };
export type EditorialSettings = { brand: string; deadline_rules: DeadlineRule[]; regular_sections: RegularSection[]; about: string | null; rules_described: string[] };
export type IssueRef = { id: string; name: string; year: number };
export type IssueDetail = Issue & {
  feature_list: Feature[]; notes: string | null; can_edit: boolean; settings: EditorialSettings;
  last_year: (IssueRef & { booked_gbp: number; orders: number }) | null; prev_issue: IssueRef | null; next_issue: IssueRef | null; can_delete: boolean;
};
export type PlannerRow = { title_id: string; title_name: string; issues: Issue[] };
export type PlannerBrand = { key: string; name: string; short: string; can_edit: boolean; titles: { id: string; name: string; slug: string }[]; seed_available: number; rows: PlannerRow[]; undated: Issue[]; about: string | null };
export type Planner = { year: number; years: number[]; today: string; brands: PlannerBrand[] };
export type Deadline = { date: string; days: number; what: string; type: "editorial" | "advertising" | "copy" | "publication" | "event" | "milestone"; issue: Issue };
export type NextYearRow = { id: string; title_name: string; kind: IssueKind; old_name: string; new_name: string; old_date: string; new_date: string; features: number };

export const KIND_LABELS: Record<IssueKind, string> = { issue: "Issue", guide: "Guide / special", event: "Event", awards: "Awards" };
export const FORMAT_LABELS: Record<IssueFormat, string> = { print_digital: "Print and digital", print: "Print only", digital: "Digital only", event: "Event", awards: "Awards" };

/** "Issue 105" for numbered issues, the name otherwise. */
export const issueLabel = (i: { name: string; kind: string }) => (/^\d+$/.test(i.name.trim()) ? `Issue ${i.name}` : i.name);
