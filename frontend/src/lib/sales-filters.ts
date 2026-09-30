/** Filter definitions for the Sales Order Register's tables. One list per
 * table, built from the register's own reference data (titles, reps,
 * years) - pure, so server pages use it to query the backend and client
 * tables use it to filter in the browser. */
import type { FilterDef, FilterValues, SortState } from "@/lib/data-view/schema";
import type { SalesMeta } from "@/lib/sales-types";

export const STATUS_OPTIONS = [
  { value: "booked", label: "Booked" },
  { value: "cancelled", label: "Cancelled" },
  { value: "contra", label: "Contra", hint: "Exchanged for goods/services, not paid in money" },
  { value: "moved", label: "Moved", hint: "Moved to another edition" },
];

export const PRODUCT_LINE_OPTIONS = [
  { value: "print", label: "Print" },
  { value: "digital", label: "Digital" },
  { value: "events", label: "Events" },
  { value: "awards", label: "Awards" },
];

const shortTitle = (name: string) => name.replace(/\s*\(.*\)/, "");

/** Keys of the bookings filters - `hide` drops any that make no sense on a page (e.g. year/title on one edition). */
export type OrderFilterKey = "q" | "year" | "title" | "line" | "rep" | "status" | "invoiced" | "linked" | "check" | "value" | "booked" | "edition";

export function orderFilterDefs(meta: SalesMeta, hide: OrderFilterKey[] = []): FilterDef[] {
  const defs: FilterDef[] = [
    { kind: "search", key: "q", label: "Search bookings", placeholder: "Client, invoice no., company, salesperson, size, notes…" },
    { kind: "multi", key: "year", label: "Year", section: "Where", options: meta.years.map((y) => ({ value: String(y), label: String(y) })) },
    { kind: "multi", key: "line", label: "Type", section: "Where", options: PRODUCT_LINE_OPTIONS },
    {
      kind: "multi", key: "title", label: "Title", section: "Where", searchable: true,
      options: meta.titles.map((t) => ({ value: t.id, label: shortTitle(t.name) })),
    },
    {
      kind: "multi", key: "rep", label: "Salesperson", section: "Who", searchable: true,
      hint: "Includes bookings a person shares a credit on, not only ones where they're the main salesperson.",
      options: meta.reps.map((r) => ({ value: r.id, label: `${r.name}${r.active ? "" : " (former)"}` })),
    },
    { kind: "multi", key: "status", label: "Status", section: "State", options: STATUS_OPTIONS },
    {
      kind: "tristate", key: "invoiced", label: "Invoice", section: "State", yes: "Invoiced", no: "Awaiting invoice",
      hint: "“Awaiting invoice” = live bookings with a value and no invoice number yet.",
    },
    {
      kind: "tristate", key: "linked", label: "CRM company", section: "State", yes: "Linked", no: "Not linked",
      hint: "Whether the client is linked to a company record in the CRM.",
    },
    {
      kind: "tristate", key: "check", label: "Import check", section: "State", yes: "Needs a check", no: "No issues",
      hint: "Rows the spreadsheet import flagged - an unreadable amount, a shifted commission column, an unknown salesperson…",
    },
    { kind: "range", key: "value", label: "Value", section: "Amount & dates", prefix: "£", step: 50 },
    { kind: "dates", key: "booked", label: "Booked on", section: "Amount & dates" },
    { kind: "dates", key: "edition", label: "Edition / event date", section: "Amount & dates" },
  ];
  return defs.filter((d) => !hide.includes(d.key as OrderFilterKey));
}

export const ORDER_DEFAULT_SORT: SortState = { key: "edition", dir: "desc" };

const list = (v: unknown) => (Array.isArray(v) ? (v as string[]) : []);

/** URL filter values -> the backend's /api/sales/orders query (which takes
 * repeated params for multi-value filters). */
export function orderBackendQuery(values: FilterValues, sort: SortState, extra: Record<string, string> = {}): URLSearchParams {
  const qs = new URLSearchParams(extra);
  const one = (k: string, v: unknown) => typeof v === "string" && v && qs.set(k, v);
  list(values.year).forEach((v) => qs.append("year", v));
  list(values.title).forEach((v) => qs.append("title_id", v));
  list(values.line).forEach((v) => qs.append("product_line", v));
  list(values.rep).forEach((v) => qs.append("rep_id", v));
  list(values.status).forEach((v) => qs.append("status", v));
  one("search", values.q);
  one("invoiced", values.invoiced);
  one("linked", values.linked);
  one("has_warning", values.check);
  one("value_min", values.value_min);
  one("value_max", values.value_max);
  one("booked_from", values.booked_from);
  one("booked_to", values.booked_to);
  one("edition_from", values.edition_from);
  one("edition_to", values.edition_to);
  qs.set("sort", sort.key);
  qs.set("desc", String(sort.dir === "desc"));
  return qs;
}

/** Backend facet names -> the sidebar's filter keys. */
export function orderFacetsForSidebar(f: Record<string, Record<string, number>>): Record<string, Record<string, number>> {
  return {
    year: f.year ?? {},
    title: f.title ?? {},
    line: f.product_line ?? {},
    rep: f.rep ?? {},
    status: f.status ?? {},
    invoiced: f.invoiced ?? {},
    linked: f.linked ?? {},
    check: f.has_warning ?? {},
  };
}
