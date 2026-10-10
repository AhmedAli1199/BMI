"use client";

import { useEffect, useMemo, useState } from "react";
import { BadgePercent, CalendarPlus, Plus, Trash2, X } from "lucide-react";
import type { SalesRate, SalesTitle } from "@/lib/sales-types";
import type { DealIssue } from "@/lib/deals-types";
import type { ProposalKind, ProposalLine, ProposalTotal } from "@/lib/proposals-types";
import { KIND_OPTIONS } from "@/lib/proposals-types";
import { getDealIssues } from "@/lib/deals-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { InfoHint } from "@/components/sales/info-hint";
import { fmtDate, fmtGBP } from "@/components/sales/sales-ui";

const selectCls = "h-8 w-full min-w-0 truncate rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-60 dark:bg-input/30";
const labelCls = "flex min-w-0 flex-col gap-1 text-xs font-semibold text-muted-foreground";

export type EditLine = ProposalLine & { id: string };

const pct = (v?: number) => (v ? String(Math.round(v * 10000) / 100) : "");
const fromPct = (s: string) => Math.min(Math.max((Number(s) || 0) / 100, 0), 1);
const lineTotal = (l: ProposalLine) => (l.issues?.length || l.qty || 1) * (l.unit_price ?? 0) * (1 - (l.discount_pct ?? 0));

/** Totals as the server works them out (offers aside, which are added when it's saved). */
export function localTotals(lines: ProposalLine[], discount: number): ProposalTotal[] {
  const opts = [...new Set(lines.map((l) => l.option).filter(Boolean))] as string[];
  return (opts.length ? opts : [null]).map((o) => {
    const group = lines.filter((l) => !l.option || l.option === o);
    const sub = Math.round(group.reduce((s, l) => s + lineTotal(l), 0) * 100) / 100;
    const disc = Math.round(sub * discount * 100) / 100;
    return { option: o, subtotal_gbp: sub, discount_gbp: disc, total_gbp: sub - disc, rate_card_gbp: 0, lines: group.filter((l) => l.source !== "offer").length };
  });
}

/** Products and prices for a proposal: any title, the issues each line runs in, % off a line or the whole proposal, and options. */
export function ProposalLines({ lines, onChange, titles, rates, defaultTitleId, discount, onDiscount, kind, onKind, disabled, serverTotals, stale }: {
  lines: EditLine[];
  onChange: (lines: EditLine[]) => void;
  titles: SalesTitle[];
  rates: SalesRate[];
  defaultTitleId: string | null;
  discount: number;
  onDiscount: (v: number) => void;
  kind: ProposalKind;
  onKind: (v: ProposalKind) => void;
  disabled?: boolean;
  serverTotals?: ProposalTotal[];
  stale?: boolean;
}) {
  const [issues, setIssues] = useState<Record<string, DealIssue[]>>({});
  const [addTitle, setAddTitle] = useState(defaultTitleId ?? titles[0]?.id ?? "");
  const wanted = useMemo(() => [...new Set(lines.filter((l) => l.source !== "offer").map((l) => l.title_id || defaultTitleId).filter(Boolean) as string[])], [lines, defaultTitleId]);
  useEffect(() => {
    let live = true;
    wanted.filter((t) => !issues[t]).forEach((t) => {
      getDealIssues(t).then((r) => live && setIssues((m) => ({ ...m, [t]: r }))).catch(() => live && setIssues((m) => ({ ...m, [t]: [] })));
    });
    return () => { live = false; };
  }, [wanted, issues]);

  const options = [...new Set(lines.map((l) => l.option).filter(Boolean))] as string[];
  const upd = (id: string, patch: Partial<EditLine>) => onChange(lines.map((l) => (l.id === id ? { ...l, ...patch } : l)));
  const titleName = (id?: string | null) => titles.find((t) => t.id === (id || defaultTitleId))?.name ?? "";
  const addRates = rates.filter((r) => r.title_id === addTitle && r.price_gbp != null);
  const totals = stale || !serverTotals ? localTotals(lines.filter((l) => !stale || l.source !== "offer"), discount) : serverTotals;
  const editable = lines.filter((l) => l.source !== "offer");

  function addRate(rateId: string) {
    const r = rates.find((x) => x.id === rateId);
    if (!r) return;
    onChange([...lines, { id: crypto.randomUUID(), product: r.product, qty: 1, unit_price: r.price_gbp, list_price: r.price_gbp, source: "rate_card", rate_id: r.id,
      title_id: r.title_id === defaultTitleId ? null : r.title_id, issues: [], discount_pct: 0, option: null }]);
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="grid gap-3 sm:grid-cols-3">
        <label className={labelCls}><span className="flex items-center gap-1">What sort of proposal <InfoHint>Shapes the wording: a single issue, a run of issues, a year-round programme, digital, sponsorship, or a mix.</InfoHint></span>
          <select className={selectCls} value={kind} disabled={disabled} onChange={(e) => onKind(e.target.value as ProposalKind)}>
            {KIND_OPTIONS.map((k) => <option key={k.value} value={k.value}>{k.label}</option>)}
          </select>
        </label>
        <label className={labelCls}><span className="flex items-center gap-1">% off the whole proposal <InfoHint>Taken off each option&apos;s total, after any % off a single line and any rate card offer. Worked out exactly, never by the AI.</InfoHint></span>
          <Input inputMode="decimal" value={pct(discount)} disabled={disabled} onChange={(e) => onDiscount(fromPct(e.target.value))} placeholder="0" className="h-8 text-sm" />
        </label>
      </div>

      <ul className="flex flex-col gap-2">
        {lines.map((l) => l.source === "offer" ? (
          <li key={l.id} className={`flex items-center justify-between rounded-lg border border-dashed border-border px-3 py-2 text-sm ${stale ? "opacity-50" : ""}`}>
            <span className="inline-flex items-center gap-1.5 font-medium" style={{ color: "var(--ok)" }}><BadgePercent className="size-3.5" aria-hidden="true" />{l.product.replace(/^Offer: /, "")}{l.option ? <span className="text-xs text-muted-foreground"> · {l.option}</span> : null}</span>
            <span className="font-semibold tabular-nums" style={{ color: "var(--ok)" }}>{fmtGBP(l.qty * (l.unit_price ?? 0))}</span>
          </li>
        ) : (
          <li key={l.id} className="rounded-lg border border-border/80 bg-card p-3">
            <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_5rem_7rem_5rem_7rem_auto] sm:items-end">
              <label className={labelCls}>
                <span>{titleName(l.title_id)}{l.source === "rate_card" ? " · rate card" : ""}</span>
                {l.source === "rate_card" || disabled ? <span className="flex h-8 items-center text-sm font-medium text-foreground">{l.product}</span>
                  : <Input value={l.product} onChange={(e) => upd(l.id, { product: e.target.value })} placeholder="What are you offering?" className="h-8 text-sm" aria-label="Product" />}
              </label>
              <label className={labelCls}>Qty
                <Input type="number" min={1} value={l.issues?.length || l.qty} disabled={disabled || !!l.issues?.length} title={l.issues?.length ? "Set by the issues it runs in" : undefined}
                  onChange={(e) => upd(l.id, { qty: Math.max(1, Number(e.target.value) || 1) })} className="h-8 text-right text-sm tabular-nums" />
              </label>
              <label className={labelCls}>Each (£)
                {l.source === "rate_card" || disabled ? <span className="flex h-8 items-center justify-end text-sm tabular-nums text-foreground">{fmtGBP(l.unit_price ?? 0)}</span>
                  : <Input inputMode="decimal" value={l.unit_price ?? ""} onChange={(e) => upd(l.id, { unit_price: e.target.value === "" ? null : Number(e.target.value) })} className="h-8 text-right text-sm tabular-nums" />}
              </label>
              <label className={labelCls}>% off
                <Input inputMode="decimal" value={pct(l.discount_pct)} disabled={disabled} onChange={(e) => upd(l.id, { discount_pct: fromPct(e.target.value) })} placeholder="0" className="h-8 text-right text-sm" />
              </label>
              <div className="flex h-8 items-center justify-end text-sm font-semibold tabular-nums">{fmtGBP(lineTotal(l))}</div>
              {!disabled && <Button size="icon-sm" variant="ghost" aria-label={`Remove ${l.product || "line"}`} onClick={() => onChange(lines.filter((x) => x.id !== l.id))}><Trash2 className="size-3.5" /></Button>}
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
              <span className="font-semibold text-muted-foreground">Runs in</span>
              {(l.issues ?? []).map((iid) => {
                const iss = (issues[l.title_id || defaultTitleId || ""] ?? []).find((x) => x.id === iid);
                const label = iss ? `${iss.label}${iss.edition_date ? ` · ${fmtDate(iss.edition_date)}` : ""}` : (l.issue_labels?.[(l.issues ?? []).indexOf(iid)] ?? "Issue");
                return (
                  <span key={iid} className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5">
                    {label}
                    {!disabled && <button type="button" aria-label={`Remove ${label}`} onClick={() => upd(l.id, { issues: (l.issues ?? []).filter((x) => x !== iid) })}><X className="size-3" /></button>}
                  </span>
                );
              })}
              {!disabled && <>
                <select aria-label="Add an issue" className={`${selectCls} !h-7 !w-auto max-w-64 text-xs`} value=""
                  onChange={(e) => e.target.value && upd(l.id, { issues: [...(l.issues ?? []), e.target.value] })}>
                  <option value="">{l.issues?.length ? "Add another issue…" : "Pick issues (optional)…"}</option>
                  {(issues[l.title_id || defaultTitleId || ""] ?? []).filter((i) => i.open && !(l.issues ?? []).includes(i.id)).map((i) => (
                    <option key={i.id} value={i.id}>{i.label}{i.edition_date ? ` · ${fmtDate(i.edition_date)}` : ""}</option>
                  ))}
                </select>
                <button type="button" className="inline-flex items-center gap-1 font-semibold text-primary hover:underline" onClick={() => {
                  const all = (issues[l.title_id || defaultTitleId || ""] ?? []).filter((i) => i.open && i.kind !== "month").map((i) => i.id);
                  upd(l.id, { issues: [...new Set([...(l.issues ?? []), ...all])] });
                }}><CalendarPlus className="size-3" /> Every open issue</button>
              </>}
              <span className="ml-auto flex items-center gap-1.5">
                <span className="font-semibold text-muted-foreground">Option</span>
                <Input list="proposal-options" value={l.option ?? ""} disabled={disabled} onChange={(e) => upd(l.id, { option: e.target.value || null })}
                  placeholder="in every option" className="h-7 w-44 text-xs" aria-label="Option" />
              </span>
            </div>
          </li>
        ))}
        {editable.length === 0 && <li className="rounded-lg border border-dashed border-border px-3 py-4 text-xs text-muted-foreground">No products yet.</li>}
      </ul>
      <datalist id="proposal-options">
        {[...new Set([...options, "Option A", "Option B", "Option C"])].map((o) => <option key={o} value={o} />)}
      </datalist>

      {!disabled && (
        <div className="flex flex-wrap items-center gap-2">
          <select aria-label="Title" className={`${selectCls} !w-auto max-w-56`} value={addTitle} onChange={(e) => setAddTitle(e.target.value)}>
            {titles.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
          <select aria-label="Add from the rate card" className={`${selectCls} !w-auto min-w-48 max-w-80`} value="" onChange={(e) => addRate(e.target.value)} disabled={!addRates.length}>
            <option value="">{addRates.length ? "Add from its rate card…" : "Nothing on its rate card"}</option>
            {addRates.map((r) => <option key={r.id} value={r.id}>{r.product} · {fmtGBP(r.price_gbp ?? 0)}{r.year !== new Date().getFullYear() ? ` (${r.year})` : ""}</option>)}
          </select>
          <Button size="sm" variant="ghost" className="gap-1.5" onClick={() => onChange([...lines, { id: crypto.randomUUID(), product: "", qty: 1, unit_price: null, source: "manual",
            title_id: addTitle === defaultTitleId ? null : addTitle, issues: [], discount_pct: 0, option: null }])}><Plus className="size-3.5" /> Add my own line</Button>
        </div>
      )}

      <div className="rounded-lg border border-border/70 bg-muted/20 px-3 py-2 text-sm">
        {totals.map((t) => (
          <div key={t.option ?? "all"} className="flex flex-wrap items-baseline justify-between gap-2 py-0.5">
            <span className="font-semibold">{t.option ?? "Total"}</span>
            <span className="tabular-nums">
              {t.discount_gbp ? <span className="mr-2 text-xs text-muted-foreground">{fmtGBP(t.subtotal_gbp)} less {pct(discount)}%</span> : null}
              <strong>{fmtGBP(t.total_gbp)}</strong> <span className="text-xs text-muted-foreground">before VAT</span>
            </span>
          </div>
        ))}
        {options.length > 0 && <p className="mt-1 text-[11px] text-muted-foreground">Lines without an option are part of every option. The client picks one; the order is made from that option.</p>}
        {stale && <p className="mt-1 text-[11px] text-muted-foreground">Any rate card offers are worked out again when you save.</p>}
      </div>
    </div>
  );
}
