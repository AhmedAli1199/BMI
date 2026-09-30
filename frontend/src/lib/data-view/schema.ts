/** Declarative filters for any table ("data view").
 *
 * A page describes its filters once as a list of FilterDefs; the same list
 * drives the sidebar UI, the active-filter chips, URL parsing (on the
 * server, to query the backend) and - for small tables held in the
 * browser - the filtering itself (see client-engine.ts).
 *
 * All state lives in the URL, so every filtered/sorted view is
 * bookmarkable, shareable, survives a refresh and works with Back.
 * Pure module: safe to import from server and client components alike.
 */

export type FilterOption = { value: string; label: string; hint?: string };

type Base = {
  key: string;
  label: string;
  /** Sidebar group heading - consecutive defs with the same section share one. */
  section?: string;
  hint?: string;
};

export type FilterDef = Base &
  (
    | { kind: "search"; placeholder?: string }
    /** Tick any number - matches rows with any of the ticked values. */
    | { kind: "multi"; options: FilterOption[]; /** show a search box above long lists */ searchable?: boolean; /** options shown before "Show all" */ visible?: number }
    /** Pick one (or none). `required` = always has a value (e.g. the year a page is about). */
    | { kind: "single"; options: FilterOption[]; required?: boolean; defaultValue?: string }
    /** Any / Yes / No. */
    | { kind: "tristate"; yes: string; no: string }
    /** Number from-to, e.g. value in £. Uses `${key}_min` / `${key}_max`. */
    | { kind: "range"; prefix?: string; step?: number }
    /** Date from-to. Uses `${key}_from` / `${key}_to`. */
    | { kind: "dates" }
  );

export type FilterValue = string | string[] | undefined;
export type FilterValues = Record<string, FilterValue>;

/** Every URL parameter a def reads/writes. */
export function paramKeys(def: FilterDef): string[] {
  if (def.kind === "range") return [`${def.key}_min`, `${def.key}_max`];
  if (def.kind === "dates") return [`${def.key}_from`, `${def.key}_to`];
  return [def.key];
}

type ParamSource = URLSearchParams | Record<string, string | string[] | undefined>;

function read(src: ParamSource, key: string): string | undefined {
  const v = src instanceof URLSearchParams ? src.get(key) ?? undefined : src[key];
  const s = Array.isArray(v) ? v[0] : v;
  return s && s.trim() ? s : undefined;
}

/** URL -> values. Multi-value filters are comma-separated in one param
 * (`?status=booked,moved`) to keep URLs short and readable. */
export function parseFilters(defs: FilterDef[], src: ParamSource): FilterValues {
  const out: FilterValues = {};
  for (const def of defs) {
    for (const k of paramKeys(def)) {
      const raw = read(src, k);
      if (def.kind === "multi") out[k] = raw ? raw.split(",").filter(Boolean) : undefined;
      else if (def.kind === "single") out[k] = raw ?? def.defaultValue;
      else out[k] = raw;
    }
  }
  return out;
}

export function isActive(def: FilterDef, values: FilterValues): boolean {
  if (def.kind === "single" && def.required) return false;
  return paramKeys(def).some((k) => {
    const v = values[k];
    if (def.kind === "single" && v === def.defaultValue) return false;
    return Array.isArray(v) ? v.length > 0 : !!v;
  });
}

export function activeCount(defs: FilterDef[], values: FilterValues): number {
  return defs.filter((d) => d.kind !== "search" && isActive(d, values)).length;
}

export type Chip = { id: string; label: string; clear: Record<string, FilterValue> };

const fmtDay = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });

/** One removable chip per active filter value, for the strip above a table. */
export function chips(defs: FilterDef[], values: FilterValues): Chip[] {
  const out: Chip[] = [];
  for (const def of defs) {
    if (!isActive(def, values)) continue;
    if (def.kind === "search") {
      out.push({ id: def.key, label: `“${values[def.key]}”`, clear: { [def.key]: undefined } });
    } else if (def.kind === "multi") {
      const vals = (values[def.key] as string[]) ?? [];
      for (const v of vals) {
        const opt = def.options.find((o) => o.value === v);
        out.push({
          id: `${def.key}:${v}`,
          label: `${def.label}: ${opt?.label ?? v}`,
          clear: { [def.key]: vals.filter((x) => x !== v) },
        });
      }
    } else if (def.kind === "single") {
      const opt = def.options.find((o) => o.value === values[def.key]);
      out.push({ id: def.key, label: `${def.label}: ${opt?.label ?? values[def.key]}`, clear: { [def.key]: undefined } });
    } else if (def.kind === "tristate") {
      out.push({ id: def.key, label: values[def.key] === "true" ? def.yes : def.no, clear: { [def.key]: undefined } });
    } else if (def.kind === "range") {
      const [lo, hi] = paramKeys(def).map((k) => values[k] as string | undefined);
      const p = def.prefix ?? "";
      const n = (s: string) => `${p}${Number(s).toLocaleString("en-GB")}`;
      const label = lo && hi ? `${n(lo)} – ${n(hi)}` : lo ? `≥ ${n(lo)}` : `≤ ${n(hi!)}`;
      out.push({ id: def.key, label: `${def.label}: ${label}`, clear: Object.fromEntries(paramKeys(def).map((k) => [k, undefined])) });
    } else if (def.kind === "dates") {
      const [from, to] = paramKeys(def).map((k) => values[k] as string | undefined);
      const label = from && to ? `${fmtDay(from)} – ${fmtDay(to)}` : from ? `from ${fmtDay(from)}` : `until ${fmtDay(to!)}`;
      out.push({ id: def.key, label: `${def.label}: ${label}`, clear: Object.fromEntries(paramKeys(def).map((k) => [k, undefined])) });
    }
  }
  return out;
}

/** Sort state - `?sort=value&dir=asc`. */
export type SortState = { key: string; dir: "asc" | "desc" };

export function parseSort(src: ParamSource, fallback: SortState): SortState {
  const key = read(src, "sort") ?? fallback.key;
  const dir = read(src, "dir");
  return { key, dir: dir === "asc" || dir === "desc" ? dir : key === fallback.key ? fallback.dir : "asc" };
}

/** Writes changes onto a copy of the current params; any change resets paging. */
export function withChanges(current: URLSearchParams, changes: Record<string, FilterValue>): URLSearchParams {
  const next = new URLSearchParams(current);
  for (const [k, v] of Object.entries(changes)) {
    const s = Array.isArray(v) ? v.join(",") : v;
    if (s) next.set(k, s);
    else next.delete(k);
  }
  if (!("page" in changes)) next.delete("page");
  return next;
}
