"use client";

import { useId, useMemo, useState } from "react";
import { ChevronDown, RotateCcw, Search, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { InfoHint } from "@/components/sales/info-hint";
import { useDataView } from "@/components/data-view/data-view";
import { type FilterDef, activeCount, isActive, paramKeys } from "@/lib/data-view/schema";

/** The filter panel: a sticky sidebar on wide screens, a drawer behind a
 * "Filters (n)" button on narrow ones. Rendered entirely from the page's
 * FilterDefs - a new filter is one line in a page's filter list. */
export function FilterSidebar({ title = "Filters", description }: { title?: string; description?: string }) {
  const { defs, values } = useDataView();
  const [open, setOpen] = useState(false);
  const count = activeCount(defs, values);

  return (
    <>
      <div className="lg:hidden">
        <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setOpen(true)}>
          <SlidersHorizontal className="size-3.5" aria-hidden="true" />
          {title}
          {count > 0 && <span className="rounded-full bg-primary px-1.5 text-[10px] font-bold text-primary-foreground tabular-nums">{count}</span>}
        </Button>
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetContent side="left" className="w-[88vw] gap-0 overflow-y-auto p-0 sm:max-w-sm">
            <SheetHeader className="border-b border-border px-4 py-3">
              <SheetTitle>{title}</SheetTitle>
              {description && <SheetDescription className="text-xs">{description}</SheetDescription>}
            </SheetHeader>
            <FilterPanel />
          </SheetContent>
        </Sheet>
      </div>
      <aside
        aria-label={title}
        className="sticky top-4 hidden max-h-[calc(100vh-6rem)] overflow-y-auto rounded-xl border border-border/80 bg-card shadow-2xs lg:block"
      >
        <div className="flex items-center justify-between border-b border-border/70 px-4 py-3">
          <h2 className="flex items-center gap-1.5 text-sm font-bold">
            <SlidersHorizontal className="size-3.5 text-muted-foreground" aria-hidden="true" />
            {title}
          </h2>
          <ClearAll />
        </div>
        <FilterPanel />
      </aside>
    </>
  );
}

function ClearAll() {
  const { defs, values, update } = useDataView();
  const count = activeCount(defs, values);
  if (!count) return <span className="text-[11px] text-muted-foreground">None applied</span>;
  const clear = Object.fromEntries(
    defs.filter((d) => d.kind !== "search" && !(d.kind === "single" && d.required)).flatMap((d) => paramKeys(d).map((k) => [k, undefined]))
  );
  return (
    <button type="button" onClick={() => update(clear)} className="flex items-center gap-1 text-xs font-semibold text-primary hover:underline">
      <RotateCcw className="size-3" aria-hidden="true" />
      Clear {count}
    </button>
  );
}

function FilterPanel() {
  const { defs } = useDataView();
  // Consecutive defs sharing a `section` render under one heading.
  const groups: { section?: string; defs: FilterDef[] }[] = [];
  for (const d of defs.filter((x) => x.kind !== "search")) {
    const last = groups[groups.length - 1];
    if (last && last.section === d.section && d.section) last.defs.push(d);
    else groups.push({ section: d.section, defs: [d] });
  }
  return (
    <div className="flex flex-col divide-y divide-border/70">
      {groups.map((g, i) => (
        <div key={i} className="flex flex-col gap-4 px-4 py-4">
          {g.section && <div className="-mb-1 text-[10.5px] font-bold uppercase tracking-wider text-muted-foreground">{g.section}</div>}
          {g.defs.map((d) => (
            <FilterField key={d.key} def={d} />
          ))}
        </div>
      ))}
    </div>
  );
}

function FieldLabel({ def, id, children }: { def: FilterDef; id?: string; children?: React.ReactNode }) {
  const { values, update } = useDataView();
  const active = isActive(def, values);
  return (
    <div className="mb-1.5 flex items-center justify-between gap-2">
      <span id={id} className="flex items-center gap-1 text-xs font-semibold text-foreground">
        {def.label}
        {def.hint && <InfoHint>{def.hint}</InfoHint>}
      </span>
      {children}
      {active && !(def.kind === "single" && def.required) && (
        <button
          type="button"
          onClick={() => update(Object.fromEntries(paramKeys(def).map((k) => [k, undefined])))}
          className="text-[11px] font-medium text-muted-foreground hover:text-foreground"
          aria-label={`Reset ${def.label}`}
        >
          Reset
        </button>
      )}
    </div>
  );
}

function FilterField({ def }: { def: FilterDef }) {
  switch (def.kind) {
    case "multi":
      return <MultiField def={def} />;
    case "single":
      return <SingleField def={def} />;
    case "tristate":
      return <TristateField def={def} />;
    case "range":
      return <RangeField def={def} />;
    case "dates":
      return <DatesField def={def} />;
    default:
      return null;
  }
}

const countCls = "ml-auto shrink-0 text-[11px] tabular-nums text-muted-foreground";

function MultiField({ def }: { def: Extract<FilterDef, { kind: "multi" }> }) {
  const { values, facets, update } = useDataView();
  const labelId = useId();
  const [q, setQ] = useState("");
  const [expanded, setExpanded] = useState(false);
  const selected = useMemo(() => (values[def.key] as string[] | undefined) ?? [], [values, def.key]);
  const counts = facets[def.key];
  const limit = def.visible ?? 6;

  // Selected first, then by count (when known), keeping the defined order otherwise.
  const options = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const list = def.options.filter((o) => !needle || o.label.toLowerCase().includes(needle));
    return [...list].sort((a, b) => {
      const sa = selected.includes(a.value) ? 1 : 0;
      const sb = selected.includes(b.value) ? 1 : 0;
      if (sa !== sb) return sb - sa;
      // Options with nothing to show sink to the bottom.
      if (counts) return (counts[b.value] ? 1 : 0) - (counts[a.value] ? 1 : 0);
      return 0;
    });
  }, [def.options, q, selected, counts]);
  const shown = expanded || q ? options : options.slice(0, Math.max(limit, selected.length));

  function toggle(v: string) {
    update({ [def.key]: selected.includes(v) ? selected.filter((x) => x !== v) : [...selected, v] });
  }

  return (
    <div role="group" aria-labelledby={labelId}>
      <FieldLabel def={def} id={labelId} />
      {def.searchable && def.options.length > limit && (
        <div className="relative mb-1.5">
          <Search className="pointer-events-none absolute top-1/2 left-2 size-3 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={`Find ${def.label.toLowerCase()}…`} aria-label={`Find ${def.label}`} className="h-7 pl-6 text-xs" />
        </div>
      )}
      <ul className="flex flex-col gap-0.5">
        {shown.map((o) => {
          const n = counts?.[o.value];
          const checked = selected.includes(o.value);
          const empty = counts !== undefined && !n && !checked;
          return (
            <li key={o.value} className="group/opt flex items-center">
              <label
                className={`flex min-w-0 flex-1 cursor-pointer items-center gap-2 rounded-md px-1.5 py-1 text-xs transition-colors hover:bg-muted ${empty ? "opacity-45" : ""}`}
                title={o.hint}
              >
                <input type="checkbox" className="size-3.5 shrink-0 accent-primary" checked={checked} onChange={() => toggle(o.value)} />
                <span className={`truncate ${checked ? "font-semibold text-foreground" : ""}`}>{o.label}</span>
                {n !== undefined && <span className={countCls}>{n.toLocaleString("en-GB")}</span>}
              </label>
              {/* "Only" = untick everything else in one click */}
              <button
                type="button"
                onClick={() => update({ [def.key]: [o.value] })}
                className="ml-0.5 hidden rounded px-1 text-[10.5px] font-semibold text-primary group-hover/opt:block hover:bg-primary/10 focus-visible:block"
                aria-label={`Only ${o.label}`}
              >
                only
              </button>
            </li>
          );
        })}
        {shown.length === 0 && <li className="px-1.5 py-1 text-xs text-muted-foreground">No match</li>}
      </ul>
      {!q && options.length > shown.length && (
        <button type="button" onClick={() => setExpanded(true)} className="mt-1 flex items-center gap-0.5 px-1.5 text-xs font-semibold text-primary hover:underline">
          <ChevronDown className="size-3" aria-hidden="true" /> Show all {options.length}
        </button>
      )}
      {expanded && !q && options.length > limit && (
        <button type="button" onClick={() => setExpanded(false)} className="mt-1 px-1.5 text-xs font-semibold text-muted-foreground hover:underline">
          Show fewer
        </button>
      )}
    </div>
  );
}

function SingleField({ def }: { def: Extract<FilterDef, { kind: "single" }> }) {
  const { values, facets, update } = useDataView();
  const id = useId();
  const current = (values[def.key] as string | undefined) ?? "";
  const counts = facets[def.key];
  return (
    <div>
      <FieldLabel def={def} id={`${id}-l`} />
      <select
        id={id}
        aria-labelledby={`${id}-l`}
        value={current}
        onChange={(e) => update({ [def.key]: e.target.value || undefined })}
        className="h-8 w-full rounded-md border border-input bg-background px-2 text-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        {!def.required && <option value="">Any</option>}
        {def.options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
            {counts?.[o.value] !== undefined ? ` (${counts[o.value].toLocaleString("en-GB")})` : ""}
          </option>
        ))}
      </select>
    </div>
  );
}

function TristateField({ def }: { def: Extract<FilterDef, { kind: "tristate" }> }) {
  const { values, facets, update } = useDataView();
  const id = useId();
  const current = (values[def.key] as string | undefined) ?? "";
  const counts = facets[def.key];
  const opts = [
    { v: "", label: "Any" },
    { v: "true", label: def.yes },
    { v: "false", label: def.no },
  ];
  return (
    <div role="radiogroup" aria-labelledby={id}>
      <FieldLabel def={def} id={id} />
      <div className="flex flex-col gap-0.5">
        {opts.map((o) => (
          <label key={o.v} className="flex cursor-pointer items-center gap-2 rounded-md px-1.5 py-1 text-xs hover:bg-muted">
            <input type="radio" name={id} className="size-3.5 accent-primary" checked={current === o.v} onChange={() => update({ [def.key]: o.v || undefined })} />
            <span className={current === o.v ? "font-semibold" : ""}>{o.label}</span>
            {o.v && counts?.[o.v] !== undefined && <span className={countCls}>{counts[o.v].toLocaleString("en-GB")}</span>}
          </label>
        ))}
      </div>
    </div>
  );
}

/** Typed values apply on Enter or when the field loses focus - never on
 * every keystroke, which would reload the table mid-number. */
function useCommittedInput(value: string | undefined, commit: (v: string) => void) {
  const [draft, setDraft] = useState(value ?? "");
  const [seen, setSeen] = useState(value);
  if (value !== seen) {
    setSeen(value);
    setDraft(value ?? "");
  }
  return {
    value: draft,
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => setDraft(e.target.value),
    onBlur: () => draft !== (value ?? "") && commit(draft),
    onKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => e.key === "Enter" && commit(draft),
  };
}

function RangeField({ def }: { def: Extract<FilterDef, { kind: "range" }> }) {
  const { values, update } = useDataView();
  const [kMin, kMax] = paramKeys(def);
  const set = (k: string) => (v: string) => update({ [k]: v.trim() ? String(Number(v) || 0) : undefined });
  const lo = useCommittedInput(values[kMin] as string | undefined, set(kMin));
  const hi = useCommittedInput(values[kMax] as string | undefined, set(kMax));
  const cls = "h-8 text-xs tabular-nums";
  return (
    <div>
      <FieldLabel def={def} />
      <div className="flex items-center gap-1.5">
        <Input type="number" inputMode="decimal" min={0} step={def.step ?? 1} placeholder={`${def.prefix ?? ""}Min`} aria-label={`${def.label} from`} className={cls} {...lo} />
        <span className="text-xs text-muted-foreground">–</span>
        <Input type="number" inputMode="decimal" min={0} step={def.step ?? 1} placeholder={`${def.prefix ?? ""}Max`} aria-label={`${def.label} to`} className={cls} {...hi} />
      </div>
    </div>
  );
}

const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

function datePresets(): { label: string; from: string; to?: string }[] {
  const now = new Date();
  const y = now.getFullYear();
  const back = (days: number) => iso(new Date(now.getTime() - days * 86400000));
  return [
    { label: "Last 30 days", from: back(30), to: iso(now) },
    { label: "This month", from: iso(new Date(y, now.getMonth(), 1)), to: iso(new Date(y, now.getMonth() + 1, 0)) },
    { label: "This quarter", from: iso(new Date(y, Math.floor(now.getMonth() / 3) * 3, 1)), to: iso(new Date(y, Math.floor(now.getMonth() / 3) * 3 + 3, 0)) },
    { label: "This year", from: `${y}-01-01`, to: `${y}-12-31` },
    { label: "Last year", from: `${y - 1}-01-01`, to: `${y - 1}-12-31` },
  ];
}

function DatesField({ def }: { def: Extract<FilterDef, { kind: "dates" }> }) {
  const { values, update } = useDataView();
  const [kFrom, kTo] = paramKeys(def);
  const [presets] = useState(datePresets);
  const from = (values[kFrom] as string | undefined) ?? "";
  const to = (values[kTo] as string | undefined) ?? "";
  const cls = "h-8 text-xs";
  return (
    <div>
      <FieldLabel def={def} />
      <div className="grid grid-cols-2 gap-1.5">
        <Input type="date" value={from} max={to || undefined} aria-label={`${def.label} from`} className={cls} onChange={(e) => update({ [kFrom]: e.target.value || undefined })} />
        <Input type="date" value={to} min={from || undefined} aria-label={`${def.label} to`} className={cls} onChange={(e) => update({ [kTo]: e.target.value || undefined })} />
      </div>
      <div className="mt-1.5 flex flex-wrap gap-1">
        {presets.map((p) => {
          const on = from === p.from && to === (p.to ?? "");
          return (
            <button
              key={p.label}
              type="button"
              onClick={() => update(on ? { [kFrom]: undefined, [kTo]: undefined } : { [kFrom]: p.from, [kTo]: p.to })}
              aria-pressed={on}
              className={`rounded-full border px-2 py-0.5 text-[10.5px] font-medium transition-colors ${on ? "border-primary bg-primary text-primary-foreground" : "border-border text-muted-foreground hover:bg-muted hover:text-foreground"}`}
            >
              {p.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

