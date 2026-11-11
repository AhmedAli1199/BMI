"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Plus, Search, SlidersHorizontal, Trash2, X } from "lucide-react";
import type { ContactField, SearchCondition } from "@/lib/contact-tools-types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { InfoHint } from "@/components/sales/info-hint";

/** The Contacts search (Craig, feedback #14): one search, rule lines for any field.
 * A new rule starts on Email (any) contains (or the last field used).
 * Plain-word searches (the top bar, links) arrive as q/company/city... and are turned into rules on arrival.
 * Whatever is filtering the list shows as tags with an X, so nothing is ever hidden. */

type Quick = { q: string; company: string; city: string; country: string; title: string };

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

  // One search (Craig, feedback #14): rule lines for any field. Searches that arrive as plain words (the search box
  // at the top of the app, "contacts at this company" links) are turned into rules straight away.
  const blankRule = (): SearchCondition => {
    const last = readLS(LAST_FIELD_KEY);
    const f = (last && byKey(last)) || byKey("email") || fields[0];
    return { field: f.key, op: f.ops[0].op, value: "" };
  };
  const [rows, setRows] = useState<SearchCondition[]>(conds);
  const [match, setMatch] = useState(initialMatch === "any" ? "any" : "all");
  useEffect(() => {
    setRows(conds.length ? conds : fields.length ? [blankRule()] : []); // eslint-disable-line react-hooks/set-state-in-effect -- following the URL
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

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

  useEffect(() => {
    if (!quickUsed) return;
    const p = new URLSearchParams(params.toString());
    for (const k of ["q", "company", "city", "country", "title"]) p.delete(k);
    p.set("conds", JSON.stringify([...conds, ...quickAsRules()]));
    p.delete("page");
    router.replace(`${pathname}?${p}`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quickUsed, params]);

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


  return (
    <form action="/contacts" className="flex flex-col gap-3 rounded-lg border border-border bg-card p-3 shadow-2xs">
      <input type="hidden" name="sort" value={sort} />
      {desc && <input type="hidden" name="desc" value="1" />}

      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 text-sm font-bold"><SlidersHorizontal className="size-3.5 text-muted-foreground" /> Search</span>
        <InfoHint>
          Pick a field, how to compare and a value, e.g. Email (any) contains onboard. <strong>Anything</strong> looks in names, job
          titles, companies, emails, phone numbers, addresses and the extra fields. Add more rules to narrow it down. Everything
          that&apos;s filtering the list shows as a tag below - its X removes it.
        </InfoHint>
      </div>

      {(
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
