"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Plus, Search, SlidersHorizontal, Trash2, X } from "lucide-react";
import type { ContactField, SearchCondition } from "@/lib/contact-tools-types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { InfoHint } from "@/components/sales/info-hint";

/** The Contacts lookup (Craig, feedback #14): two ways to search, one at a time.
 * - Quick search: the boxes (anything, company, town, country, job title).
 * - Advanced search: rule lines (field / how / value), starting on Email (any) contains.
 * Switching from Quick to Advanced turns what was typed into rules, so everything lives in one place.
 * Whatever is filtering the list - from either mode - shows as tags with an X, so nothing is ever hidden. */

type Quick = { q: string; company: string; city: string; country: string; title: string };

const MODE_KEY = "bmi.contacts.search-mode";
const LAST_FIELD_KEY = "bmi.contacts.advanced-search.last-field";
const NO_VALUE = new Set(["is_empty", "is_not_empty", "is_yes", "is_no"]);
const QUICK_FIELDS: { key: keyof Quick; rule: string; label: string; placeholder: string; aria: string }[] = [
  { key: "company", rule: "company", label: "Company", placeholder: "Company", aria: "Company" },
  { key: "city", rule: "city", label: "City / town", placeholder: "City / town", aria: "City or town" },
  { key: "country", rule: "country", label: "Country", placeholder: "Country", aria: "Country" },
  { key: "title", rule: "job_title", label: "Job title", placeholder: "Job title", aria: "Job title" },
];
const selectCls =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2 text-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";

function readLS(key: string): string | null {
  try { return window.localStorage.getItem(key); } catch { return null; }
}
function writeLS(key: string, value: string) {
  try { window.localStorage.setItem(key, value); } catch { /* private window */ }
}

export function ContactSearch({
  fields,
  quick,
  conds,
  match: initialMatch,
  sort,
  desc,
}: {
  fields: ContactField[];
  quick: Quick;
  conds: SearchCondition[];
  match: string;
  sort: string;
  desc: boolean;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const byKey = (k: string) => fields.find((f) => f.key === k);
  const quickUsed = Object.values(quick).some(Boolean);

  // Mode: what the URL is using, else what this person picked last time.
  const [mode, setMode] = useState<"quick" | "advanced">(conds.length && !quickUsed ? "advanced" : "quick");
  useEffect(() => {
    if (conds.length || quickUsed) return;
    if (readLS(MODE_KEY) === "advanced") setMode("advanced"); // eslint-disable-line react-hooks/set-state-in-effect -- restoring a saved choice
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const blankRule = (): SearchCondition => {
    const last = readLS(LAST_FIELD_KEY);
    const f = (last && byKey(last)) || byKey("email") || fields[0];
    return { field: f.key, op: f.ops[0].op, value: "" };
  };
  const [rows, setRows] = useState<SearchCondition[]>(conds);
  const [match, setMatch] = useState(initialMatch === "any" ? "any" : "all");
  useEffect(() => {
    setRows(conds.length ? conds : mode === "advanced" && fields.length ? [blankRule()] : []); // eslint-disable-line react-hooks/set-state-in-effect -- following the URL
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params, mode]);

  const groups = useMemo(() => {
    const m = new Map<string, ContactField[]>();
    for (const f of fields) m.set(f.group, [...(m.get(f.group) ?? []), f]);
    return [...m.entries()];
  }, [fields]);
  const complete = rows.filter((r) => r.field && r.op && (NO_VALUE.has(r.op) || r.value.trim()));

  function go(next: URLSearchParams) {
    next.delete("page");
    router.push(next.size ? `${pathname}?${next}` : `${pathname}?fresh=1`);
  }

  function quickAsRules(): SearchCondition[] {
    const out: SearchCondition[] = [];
    if (quick.q) out.push({ field: "anything", op: "contains", value: quick.q });
    for (const f of QUICK_FIELDS) if (quick[f.key]) out.push({ field: f.rule, op: "contains", value: quick[f.key] });
    return out;
  }

  function switchTo(next: "quick" | "advanced") {
    if (next === mode) return;
    writeLS(MODE_KEY, next);
    if (next === "advanced" && quickUsed) {
      // What was typed in Quick search carries over as rules.
      const p = new URLSearchParams(params.toString());
      for (const k of ["q", "company", "city", "country", "title"]) p.delete(k);
      p.set("conds", JSON.stringify([...conds, ...quickAsRules()]));
      setMode("advanced");
      go(p);
      return;
    }
    setMode(next);
  }

  function change(i: number, patch: Partial<SearchCondition>) {
    setRows(rows.map((r, j) => {
      if (j !== i) return r;
      const next = { ...r, ...patch };
      if (patch.field && patch.field !== r.field) {
        writeLS(LAST_FIELD_KEY, patch.field);
        const f = byKey(patch.field);
        if (f && !f.ops.some((o) => o.op === next.op)) next.op = f.ops[0].op;
        next.value = "";
      }
      return next;
    }));
  }

  // ---- the tags row: everything filtering the list, from either mode ----
  const describe = (c: SearchCondition) => {
    const f = byKey(c.field);
    const op = f?.ops.find((o) => o.op === c.op)?.label ?? c.op;
    const label = c.field === "anything" ? "Anything" : f?.label ?? c.field;
    return `${label} ${op}${NO_VALUE.has(c.op) ? "" : ` “${c.value}”`}`;
  };
  const tags: { label: string; remove: () => void }[] = [];
  if (quick.q) tags.push({ label: `Search “${quick.q}”`, remove: () => drop("q") });
  for (const f of QUICK_FIELDS) if (quick[f.key]) tags.push({ label: `${f.label} contains “${quick[f.key]}”`, remove: () => drop(f.key) });
  conds.forEach((c, i) => tags.push({ label: describe(c), remove: () => dropRule(i) }));

  function drop(key: string) {
    const p = new URLSearchParams(params.toString());
    p.delete(key);
    go(p);
  }
  function dropRule(i: number) {
    const p = new URLSearchParams(params.toString());
    const next = conds.filter((_, j) => j !== i);
    if (next.length) p.set("conds", JSON.stringify(next));
    else { p.delete("conds"); p.delete("match"); }
    go(p);
  }

  const tabCls = (on: boolean) =>
    `inline-flex h-7 items-center gap-1.5 rounded-md px-2.5 text-xs font-semibold transition-colors ${on ? "bg-card text-foreground shadow-2xs ring-1 ring-border" : "text-muted-foreground hover:text-foreground"}`;
  const inputCls = "h-8 text-xs";

  return (
    <form action="/contacts" className="flex flex-col gap-3 rounded-lg border border-border bg-card p-3 shadow-2xs">
      <input type="hidden" name="sort" value={sort} />
      {desc && <input type="hidden" name="desc" value="1" />}

      <div className="flex flex-wrap items-center gap-2">
        <div role="tablist" aria-label="How to search" className="inline-flex gap-1 rounded-lg bg-muted p-0.5">
          <button type="button" role="tab" aria-selected={mode === "quick"} className={tabCls(mode === "quick")} onClick={() => switchTo("quick")}>
            <Search className="size-3.5" /> Quick search
          </button>
          <button type="button" role="tab" aria-selected={mode === "advanced"} className={tabCls(mode === "advanced")} onClick={() => switchTo("advanced")}>
            <SlidersHorizontal className="size-3.5" /> Advanced search
          </button>
        </div>
        <InfoHint>
          <strong>Quick search</strong>: type in any of the boxes - the first one looks in names, job titles, companies, emails, phone
          numbers, addresses and the extra fields. <strong>Advanced search</strong>: rules for any field, e.g. Email (any) contains
          onboard. Switching to Advanced turns what you typed into rules. Everything that&apos;s filtering the list shows as a tag below -
          its X removes it.
        </InfoHint>
      </div>

      {mode === "quick" ? (
        <>
          {/* Rules from Advanced search keep applying while you use the boxes. */}
          {conds.length > 0 && <input type="hidden" name="conds" value={JSON.stringify(conds)} />}
          {conds.length > 0 && initialMatch === "any" && <input type="hidden" name="match" value="any" />}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-[2fr_1.3fr_1fr_1fr_1.3fr_auto]">
            <div className="relative col-span-2 sm:col-span-3 lg:col-span-1">
              <Search className="absolute left-2.5 top-2 size-3.5 text-muted-foreground" />
              <Input name="q" aria-label="Search" placeholder="Name, email, phone, address, company…" defaultValue={quick.q} className={`pl-8 ${inputCls}`} />
            </div>
            {QUICK_FIELDS.map((f) => (
              <Input key={f.key} name={f.key} aria-label={f.aria} placeholder={f.placeholder} defaultValue={quick[f.key]} className={inputCls} />
            ))}
            <Button type="submit" size="sm" className="col-span-2 h-8 gap-1.5 sm:col-span-1">
              <Search className="size-3.5" /> Look up
            </Button>
          </div>
        </>
      ) : (
        <div className="flex flex-col gap-2">
          <input type="hidden" name="conds" value={complete.length ? JSON.stringify(complete) : ""} />
          <input type="hidden" name="match" value={complete.length > 1 && match === "any" ? "any" : ""} />
          {rows.length > 1 && (
            <div className="flex items-center gap-2 text-xs">
              Match
              <select aria-label="Match all or any rule" className={`${selectCls} !w-auto`} value={match} onChange={(e) => setMatch(e.target.value)}>
                <option value="all">all of these rules</option>
                <option value="any">any one of these rules</option>
              </select>
            </div>
          )}
          {rows.map((r, i) => {
            const f = byKey(r.field);
            return (
              <div key={i} className="grid grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1.4fr)_auto] items-center gap-2">
                <select aria-label="Field" className={selectCls} value={r.field} onChange={(e) => change(i, { field: e.target.value })}>
                  {groups.map(([g, fs]) => (
                    <optgroup key={g} label={g}>{fs.map((x) => <option key={x.key} value={x.key}>{x.label}</option>)}</optgroup>
                  ))}
                </select>
                <select aria-label="How to compare" className={selectCls} value={r.op} onChange={(e) => change(i, { op: e.target.value })}>
                  {(f?.ops ?? []).map((o) => <option key={o.op} value={o.op}>{o.label}</option>)}
                </select>
                {NO_VALUE.has(r.op) ? <span className="text-xs text-muted-foreground">-</span> : (
                  <Input aria-label="Value" type={f?.kind === "date" ? "date" : "text"} value={r.value} onChange={(e) => change(i, { value: e.target.value })}
                    placeholder={f?.kind === "date" ? "" : "Type a value"} className="h-8 text-xs" />
                )}
                <Button type="button" size="icon-sm" variant="ghost" aria-label="Remove this rule" onClick={() => setRows(rows.filter((_, j) => j !== i))}>
                  <Trash2 className="size-3.5" />
                </Button>
              </div>
            );
          })}
          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" size="sm" variant="ghost" className="h-7 gap-1.5 text-xs" onClick={() => setRows([...rows, blankRule()])}>
              <Plus className="size-3.5" /> Add a rule
            </Button>
            <Button type="submit" size="sm" className="ml-auto h-8 gap-1.5">
              <Search className="size-3.5" /> Look up
            </Button>
          </div>
        </div>
      )}

      {tags.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 border-t border-border/60 pt-2.5">
          <span className="text-[11px] font-semibold text-muted-foreground">Searching for:</span>
          {tags.map((t, i) => (
            <span key={i} className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/5 py-0.5 pl-2.5 pr-1 text-[11px] font-medium">
              {t.label}
              <button type="button" onClick={t.remove} aria-label={`Remove: ${t.label}`} className="rounded-full p-0.5 hover:bg-primary/15">
                <X className="size-3" />
              </button>
            </span>
          ))}
          {conds.length > 1 && <span className="text-[11px] text-muted-foreground">({initialMatch === "any" ? "any one of the rules" : "all of the rules"})</span>}
          <Button variant="ghost" size="sm" className="h-6 px-2 text-[11px]" nativeButton={false} render={<Link href="/contacts?fresh=1" aria-label="Clear lookup" />}>
            Clear all
          </Button>
        </div>
      )}
    </form>
  );
}
