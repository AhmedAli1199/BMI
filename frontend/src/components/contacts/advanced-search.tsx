"use client";

import { useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Plus, SlidersHorizontal, Trash2, X } from "lucide-react";
import type { ContactField, SearchCondition } from "@/lib/contact-tools-types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { InfoHint } from "@/components/sales/info-hint";

const selectCls = "h-8 w-full rounded-lg border border-input bg-transparent px-2 text-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";
const NO_VALUE = new Set(["is_empty", "is_not_empty", "is_yes", "is_no"]);

function describe(c: SearchCondition, fields: ContactField[]) {
  const f = fields.find((x) => x.key === c.field);
  const op = f?.ops.find((o) => o.op === c.op)?.label ?? c.op;
  return `${f?.label ?? c.field} ${op}${NO_VALUE.has(c.op) ? "" : ` “${c.value}”`}`;
}

/** The "Advanced search" part of the contacts lookup: any number of "field / how / value" rules, all
 * of which (or any one of which) must match. Lives inside the lookup <form>; its rules travel in the
 * hidden `conds` / `match` fields so the whole search stays one shareable URL. */
export function AdvancedSearch({ fields, initial, match: initialMatch }: { fields: ContactField[]; initial: SearchCondition[]; match: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [open, setOpen] = useState(initial.length > 0);
  const [rows, setRows] = useState<SearchCondition[]>(initial.length ? initial : []);
  const [match, setMatch] = useState(initialMatch === "any" ? "any" : "all");
  const groups = useMemo(() => {
    const m = new Map<string, ContactField[]>();
    for (const f of fields) m.set(f.group, [...(m.get(f.group) ?? []), f]);
    return [...m.entries()];
  }, [fields]);
  const byKey = (k: string) => fields.find((f) => f.key === k);
  const complete = rows.filter((r) => r.field && r.op && (NO_VALUE.has(r.op) || r.value.trim()));

  function add() {
    const f = fields.find((x) => x.key === "job_title") ?? fields[0];
    setRows([...rows, { field: f.key, op: f.ops[0].op, value: "" }]);
    setOpen(true);
  }
  function change(i: number, patch: Partial<SearchCondition>) {
    setRows(rows.map((r, j) => {
      if (j !== i) return r;
      const next = { ...r, ...patch };
      if (patch.field && patch.field !== r.field) {
        const f = byKey(patch.field);
        if (f && !f.ops.some((o) => o.op === next.op)) next.op = f.ops[0].op;
        next.value = "";
      }
      return next;
    }));
  }
  function removeChip(i: number) {
    const next = initial.filter((_, j) => j !== i);
    const p = new URLSearchParams(params.toString());
    if (next.length) p.set("conds", JSON.stringify(next));
    else { p.delete("conds"); p.delete("match"); }
    p.delete("page");
    router.push(`${pathname}?${p}`);
  }

  return (
    <div className="col-span-full">
      <input type="hidden" name="conds" value={complete.length ? JSON.stringify(complete) : ""} />
      <input type="hidden" name="match" value={complete.length && match === "any" ? "any" : ""} />
      <div className="flex flex-wrap items-center gap-2">
        <Button type="button" variant="ghost" size="sm" className="h-7 gap-1.5 px-2 text-xs" aria-expanded={open} onClick={() => (open ? setOpen(false) : rows.length ? setOpen(true) : add())}>
          <SlidersHorizontal className="size-3.5" /> Advanced search{initial.length ? ` (${initial.length})` : ""}
        </Button>
        <InfoHint>Search any field - including phone, address, notes and the Act! custom fields - with several rules at once, e.g. Postcode <em>starts with</em> SW1 and Job title <em>contains</em> counsellor.</InfoHint>
        {initial.map((c, i) => (
          <span key={i} className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/5 py-0.5 pl-2.5 pr-1 text-[11px] font-medium">
            {describe(c, fields)}
            <button type="button" onClick={() => removeChip(i)} aria-label={`Remove rule: ${describe(c, fields)}`} className="rounded-full p-0.5 hover:bg-primary/15"><X className="size-3" /></button>
          </span>
        ))}
      </div>
      {open && (
        <div className="mt-2 flex flex-col gap-2 rounded-lg border border-border/80 bg-muted/30 p-3">
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
                  <Input aria-label="Value" type={f?.kind === "date" ? "date" : "text"} value={r.value} onChange={(e) => change(i, { value: e.target.value })} placeholder={f?.kind === "date" ? "" : "Type a value"} className="h-8 text-xs" />
                )}
                <Button type="button" size="icon-sm" variant="ghost" aria-label="Remove this rule" onClick={() => setRows(rows.filter((_, j) => j !== i))}><Trash2 className="size-3.5" /></Button>
              </div>
            );
          })}
          <div className="flex items-center gap-2">
            <Button type="button" size="sm" variant="ghost" className="h-7 gap-1.5 text-xs" onClick={add}><Plus className="size-3.5" /> Add a rule</Button>
            <span className="text-[11px] text-muted-foreground">Press “Look up” to search.</span>
          </div>
        </div>
      )}
    </div>
  );
}
