/** Filtering, sorting and facet counts for tables whose rows are already
 * in the browser (editions, commissions, renewals - hundreds of rows, not
 * thousands). Same FilterDefs and URL state as server-filtered tables, so
 * both kinds look and behave identically. */
import { type FilterDef, type FilterValues, type SortState, paramKeys } from "@/lib/data-view/schema";

/** How to read each filter's value off a row. Keyed by FilterDef.key:
 * search -> the texts to match, multi/single -> value(s), tristate ->
 * boolean, range -> number, dates -> ISO date. */
export type Accessors<Row> = Record<string, (row: Row) => unknown>;

function matches<Row>(row: Row, def: FilterDef, values: FilterValues, get: (row: Row) => unknown): boolean {
  const keys = paramKeys(def);
  switch (def.kind) {
    case "search": {
      const needle = (values[def.key] as string | undefined)?.trim().toLowerCase();
      if (!needle) return true;
      const hay = get(row);
      const texts = (Array.isArray(hay) ? hay : [hay]).filter(Boolean).map((t) => String(t).toLowerCase());
      // Every word must appear somewhere - "air canada 2025" narrows, not widens.
      return needle.split(/\s+/).every((w) => texts.some((t) => t.includes(w)));
    }
    case "multi": {
      const want = values[def.key] as string[] | undefined;
      if (!want?.length) return true;
      const v = get(row);
      const have = (Array.isArray(v) ? v : [v]).map(String);
      return want.some((w) => have.includes(w));
    }
    case "single": {
      const want = values[def.key] as string | undefined;
      return !want || def.required || String(get(row)) === want;
    }
    case "tristate": {
      const want = values[def.key];
      return !want || !!get(row) === (want === "true");
    }
    case "range": {
      const [lo, hi] = keys.map((k) => values[k] as string | undefined);
      if (!lo && !hi) return true;
      const n = get(row) as number | null;
      if (n === null || n === undefined) return false;
      return (!lo || n >= Number(lo)) && (!hi || n <= Number(hi));
    }
    case "dates": {
      const [from, to] = keys.map((k) => values[k] as string | undefined);
      if (!from && !to) return true;
      const d = get(row) as string | null;
      if (!d) return false;
      const day = d.slice(0, 10);
      return (!from || day >= from) && (!to || day <= to);
    }
  }
}

export function applyFilters<Row>(rows: Row[], defs: FilterDef[], values: FilterValues, acc: Accessors<Row>, skip?: string): Row[] {
  const active = defs.filter((d) => d.key !== skip && acc[d.key]);
  return rows.filter((row) => active.every((d) => matches(row, d, values, acc[d.key])));
}

/** {filterKey: {option: count}} for multi and tristate filters - each
 * counted under every *other* active filter, like a shop's sidebar. */
export function facetCounts<Row>(rows: Row[], defs: FilterDef[], values: FilterValues, acc: Accessors<Row>) {
  const out: Record<string, Record<string, number>> = {};
  for (const def of defs) {
    if ((def.kind !== "multi" && def.kind !== "tristate") || !acc[def.key]) continue;
    const pool = applyFilters(rows, defs, values, acc, def.key);
    const counts: Record<string, number> = def.kind === "tristate" ? { true: 0, false: 0 } : {};
    for (const row of pool) {
      const v = acc[def.key](row);
      const keys = def.kind === "tristate" ? [String(!!v)] : (Array.isArray(v) ? v : [v]).map(String);
      for (const k of new Set(keys)) counts[k] = (counts[k] ?? 0) + 1;
    }
    out[def.key] = counts;
  }
  return out;
}

export type SortAccessors<Row> = Record<string, (row: Row) => string | number | null | undefined>;

const collator = new Intl.Collator("en-GB", { numeric: true, sensitivity: "base" });

/** Stable sort; empty values always last, whichever direction. */
export function sortRows<Row>(rows: Row[], sort: SortState, acc: SortAccessors<Row>): Row[] {
  const get = acc[sort.key];
  if (!get) return rows;
  const sign = sort.dir === "asc" ? 1 : -1;
  return rows
    .map((row, i) => ({ row, i, v: get(row) }))
    .sort((a, b) => {
      const ae = a.v === null || a.v === undefined || a.v === "";
      const be = b.v === null || b.v === undefined || b.v === "";
      if (ae || be) return ae === be ? a.i - b.i : ae ? 1 : -1;
      const c = typeof a.v === "number" && typeof b.v === "number" ? a.v - b.v : collator.compare(String(a.v), String(b.v));
      return c === 0 ? a.i - b.i : sign * c;
    })
    .map((x) => x.row);
}
