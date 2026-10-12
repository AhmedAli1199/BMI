"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { Check, ExternalLink, Pencil, Plus, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import type { CostLine, CostLineInput, EditionCosts } from "@/lib/sales-types";
import { deleteCostLine, saveCostLine } from "@/lib/sales-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { InfoHint } from "@/components/sales/info-hint";
import { fmtGBP } from "@/components/sales/sales-ui";
import { friendlyError } from "@/lib/errors";

const KIND_LABEL: Record<CostLine["kind"], string> = { cost: "Cost", income: "Income", summary: "Sheet total", note: "Note" };
const selectCls = "h-8 rounded-md border border-input bg-background px-2 text-xs";

type Draft = { kind: CostLineInput["kind"]; label: string; amount: string; budget: string; section: string; category: string; order: string };
const EMPTY: Draft = { kind: "cost", label: "", amount: "", budget: "", section: "", category: "", order: "" };

export type CostBooking = { id: string; label: string };

/** What an issue, event or awards cost to produce, next to what it sold - and the profit left. Costs can sit in
 * parts (an awards' judging day and its ceremony), say what they were for, carry a budget, and belong to one
 * booking (the printing of a client's cover wrap). Lines from an events sheet come in on import; the sheet's
 * own totals are shown greyed but never added up: totals and profit are always worked out from the lines. */
export function EditionCostsPanel({
  editionId,
  booked,
  costs: initial,
  bookings = [],
  startOpen = true,
}: {
  editionId: string;
  booked: number;
  costs: EditionCosts;
  bookings?: CostBooking[];
  startOpen?: boolean;
}) {
  const [costs, setCosts] = useState(initial);
  const [open, setOpen] = useState(startOpen || initial.lines.length > 0);
  const [editing, setEditing] = useState<string | "new" | null>(null);
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [pending, start] = useTransition();
  const cats = costs.categories;

  // Parts in the order they first appear. A note line named like a part is that part's heading (from the sheet).
  const partNames = [...new Set(costs.lines.map((l) => l.section).filter(Boolean) as string[])];
  const isHeading = (l: CostLine) => l.kind === "note" && !l.amount_gbp && partNames.includes(l.label);
  const groups: { part: string | null; lines: CostLine[] }[] = [
    { part: null, lines: costs.lines.filter((l) => !l.section && !isHeading(l)) },
    ...partNames.map((p) => ({ part: p, lines: costs.lines.filter((l) => l.section === p && !isHeading(l)) })),
  ].filter((g) => g.lines.length || g.part);
  const partTotals = new Map(costs.parts.map((p) => [p.part, p]));
  const hasBudget = costs.total_budget_gbp !== null;
  const margin = costs.profit_gbp !== null && booked ? costs.profit_gbp / booked : null;
  const catTotal = Object.values(costs.by_category).reduce((a, b) => a + b, 0);

  if (!open) {
    return (
      <section aria-label="Costs and profit" className="flex flex-wrap items-center gap-3 rounded-xl border border-dashed border-border/80 bg-card/60 px-4 py-3 text-sm">
        <p className="min-w-0 flex-1 text-muted-foreground">
          <span className="font-semibold text-foreground">Costs &amp; profit.</span> Record what this edition cost to produce - printing, postage,
          writers, design - to see the profit it made.
        </p>
        <Button size="sm" variant="outline" className="gap-1.5" onClick={() => { setOpen(true); edit(); }}>
          <Plus className="size-3.5" /> Add the first cost
        </Button>
      </section>
    );
  }

  function edit(l?: CostLine, part?: string | null) {
    setEditing(l ? l.id : "new");
    setDraft(
      l
        ? {
            kind: l.kind === "summary" ? "note" : l.kind, label: l.label, amount: l.amount_gbp?.toString() ?? "", budget: l.budget_gbp?.toString() ?? "",
            section: l.section ?? "", category: l.category ?? "", order: l.order?.id ?? "",
          }
        : { ...EMPTY, section: part ?? "" }
    );
  }

  function save() {
    if (!draft.label.trim()) return toast.error("Describe the line");
    const num = (v: string) => (v.trim() ? Number(v.replace(/[£,\s]/g, "")) : null);
    const amount = num(draft.amount), budget = num(draft.budget);
    if ((amount !== null && Number.isNaN(amount)) || (budget !== null && Number.isNaN(budget))) return toast.error("Amounts need to be numbers");
    const isCost = draft.kind === "cost";
    start(async () => {
      try {
        setCosts(
          await saveCostLine(
            editionId,
            {
              kind: draft.kind, label: draft.label.trim(), amount_gbp: draft.kind === "note" ? null : amount, section: draft.section.trim() || null,
              category: isCost ? draft.category || null : null, budget_gbp: isCost ? budget : null, order_id: isCost ? draft.order || null : null,
            },
            editing && editing !== "new" ? editing : undefined
          )
        );
        setEditing(null);
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't save the line"));
      }
    });
  }

  function remove(id: string) {
    start(async () => {
      try {
        setCosts(await deleteCostLine(editionId, id));
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't remove the line"));
      }
    });
  }

  const editor = (key: string) => (
    <tr key={key} className="border-t border-border/60 bg-primary/5">
      <td className="px-4 py-2" colSpan={2}>
        <div className="flex flex-wrap gap-2">
          <select aria-label="Type" value={draft.kind} onChange={(e) => setDraft({ ...draft, kind: e.target.value as Draft["kind"] })} className={selectCls}>
            <option value="cost">Cost</option>
            <option value="income">Other income</option>
            <option value="note">Note</option>
          </select>
          <Input aria-label="Description" value={draft.label} onChange={(e) => setDraft({ ...draft, label: e.target.value })} placeholder="e.g. Printing, room hire, photographer" className="h-8 min-w-48 flex-1 text-sm" autoFocus />
        </div>
        <div className="mt-1.5 flex flex-wrap gap-2">
          {draft.kind === "cost" && (
            <select aria-label="What it was for" value={draft.category} onChange={(e) => setDraft({ ...draft, category: e.target.value })} className={selectCls}>
              <option value="">What was it for?</option>
              {Object.entries(cats).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          )}
          <Input aria-label="Part" list={`parts-${editionId}`} value={draft.section} onChange={(e) => setDraft({ ...draft, section: e.target.value })}
            placeholder="Part (optional) - e.g. Judging day" className="h-8 w-48 text-xs" />
          <datalist id={`parts-${editionId}`}>{partNames.map((p) => <option key={p} value={p} />)}</datalist>
          {draft.kind === "cost" && bookings.length > 0 && (
            <select aria-label="For one booking" value={draft.order} onChange={(e) => setDraft({ ...draft, order: e.target.value })} className={`${selectCls} max-w-56`}>
              <option value="">For the whole edition</option>
              {bookings.map((b) => <option key={b.id} value={b.id}>For {b.label}</option>)}
            </select>
          )}
        </div>
      </td>
      <td className="px-2 py-2 align-top">
        {draft.kind === "cost" && (
          <Input aria-label="Budget in £" inputMode="decimal" value={draft.budget} onChange={(e) => setDraft({ ...draft, budget: e.target.value })} placeholder="Budget £" className="h-8 text-right text-sm tabular-nums" />
        )}
      </td>
      <td className="px-2 py-2 align-top">
        {draft.kind !== "note" && (
          <Input aria-label="Amount in £" inputMode="decimal" value={draft.amount} onChange={(e) => setDraft({ ...draft, amount: e.target.value })} placeholder="Actual £" className="h-8 text-right text-sm tabular-nums" />
        )}
      </td>
      <td className="px-3 py-2 text-right align-top whitespace-nowrap">
        <Button size="icon-sm" onClick={save} disabled={pending} aria-label="Save line"><Check className="size-4" /></Button>
        <Button size="icon-sm" variant="ghost" onClick={() => setEditing(null)} aria-label="Cancel"><X className="size-4" /></Button>
      </td>
    </tr>
  );

  return (
    <section aria-labelledby="costs-heading" className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs">
      <header className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-border/70 px-4 py-3">
        <h2 id="costs-heading" className="flex items-center gap-1 text-sm font-bold">
          Costs &amp; profit
          <InfoHint>
            What this edition cost to produce or run, next to what it sold. Profit is the booked value minus the cost lines. Put costs in parts
            (e.g. judging day and ceremony) to see each part&apos;s total, add a budget to compare, and link a cost to one booking (a cover
            wrap&apos;s printing) to see that booking&apos;s own profit. Greyed &ldquo;sheet total&rdquo; lines are the original sheet&apos;s sums,
            for reference only. Amounts are before VAT unless the line says otherwise.
          </InfoHint>
        </h2>
        <dl className="ml-auto flex flex-wrap gap-x-6 gap-y-1 text-xs">
          <Fig label="Booked" value={fmtGBP(booked)} />
          {hasBudget && <Fig label="Budget" value={fmtGBP(costs.total_budget_gbp)} hint="The budget of the cost lines that have one." />}
          <Fig label="Costs" value={fmtGBP(costs.total_costs_gbp)} />
          {costs.other_income_gbp > 0 && <Fig label="Other income" value={fmtGBP(costs.other_income_gbp)} hint="Income lines from the sheet (e.g. a sponsorship line) - usually the same money as the bookings, so not added to profit." />}
          {costs.profit_gbp !== null && (
            <Fig label="Profit" value={`${fmtGBP(costs.profit_gbp)}${margin !== null ? ` · ${Math.round(margin * 100)}%` : ""}`} tone={costs.profit_gbp >= 0 ? "ok" : "bad"} />
          )}
        </dl>
      </header>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[40rem] text-sm">
          <caption className="sr-only">Cost lines</caption>
          <thead>
            <tr className="text-left text-[11px] font-semibold text-muted-foreground">
              <th scope="col" className="w-24 px-4 py-1.5 font-semibold"><span className="sr-only">Type</span></th>
              <th scope="col" className="py-1.5 pr-2 font-semibold">Line</th>
              <th scope="col" className="w-28 px-2 py-1.5 text-right font-semibold">Budget</th>
              <th scope="col" className="w-32 px-2 py-1.5 text-right font-semibold">Actual</th>
              <th scope="col" className="w-24 px-3 py-1.5"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          {groups.map((g) => {
            const t = partTotals.get(g.part);
            return (
              <tbody key={g.part ?? "_"}>
                {g.part !== null && (
                  <tr className="border-t border-border/70 bg-muted/40">
                    <th scope="rowgroup" colSpan={2} className="px-4 py-1.5 text-left text-xs font-semibold">{g.part}</th>
                    <td className="px-2 py-1.5 text-right text-xs font-semibold tabular-nums text-muted-foreground">{t?.budget_gbp != null ? fmtGBP(t.budget_gbp) : ""}</td>
                    <td className="px-2 py-1.5 text-right text-xs font-semibold tabular-nums">{t?.costs_gbp ? fmtGBP(t.costs_gbp) : ""}</td>
                    <td className="px-3 py-1 text-right">
                      {editing === null && (
                        <Button size="xs" variant="ghost" className="gap-1" onClick={() => edit(undefined, g.part)} aria-label={`Add a line to ${g.part}`}><Plus className="size-3" /> Add</Button>
                      )}
                    </td>
                  </tr>
                )}
                {g.lines.map((l) => (
                  <LineRow key={l.id} l={l} cats={cats} editing={editing} editor={editor} onEdit={edit} onDelete={remove} pending={pending} />
                ))}
              </tbody>
            );
          })}
          <tbody>
            {costs.lines.length === 0 && editing !== "new" && (
              <tr>
                <td colSpan={5} className="px-4 py-5 text-sm text-muted-foreground">
                  No costs recorded yet. Add printing, postage, venue, catering, writers, travel and other direct costs to see the profit.
                </td>
              </tr>
            )}
            {editing === "new" && editor("new")}
          </tbody>
        </table>
      </div>
      {editing === null && (
        <div className="border-t border-border/60 px-4 py-2">
          <Button size="sm" variant="ghost" className="gap-1.5" onClick={() => edit()}>
            <Plus className="size-3.5" /> Add a line
          </Button>
        </div>
      )}

      {(catTotal > 0 || costs.by_booking.length > 0) && (
        <div className="grid gap-4 border-t border-border/70 px-4 py-4 md:grid-cols-2">
          {catTotal > 0 && (
            <div>
              <h3 className="mb-2 text-xs font-bold text-foreground">Where the money went</h3>
              <ul className="flex flex-col gap-1.5">
                {Object.entries(costs.by_category).map(([k, v]) => (
                  <li key={k} className="flex flex-col gap-0.5">
                    <div className="flex items-baseline justify-between text-xs">
                      <span className="text-foreground">{cats[k] ?? k}</span>
                      <span className="tabular-nums text-muted-foreground">{fmtGBP(v)} · {Math.round((v / catTotal) * 100)}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-muted" aria-hidden="true">
                      <div className="h-full rounded-full" style={{ width: `${(v / catTotal) * 100}%`, background: "var(--chart-1)" }} />
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {costs.by_booking.length > 0 && (
            <div>
              <h3 className="mb-2 flex items-center gap-1 text-xs font-bold text-foreground">
                Bookings with their own costs
                <InfoHint>What each booking sold for, the costs linked to it, and what it left. Its costs are also in the edition&apos;s totals.</InfoHint>
              </h3>
              <table className="w-full text-xs">
                <caption className="sr-only">Profit on bookings with their own costs</caption>
                <thead>
                  <tr className="text-left text-muted-foreground">
                    <th scope="col" className="py-1 font-semibold">Booking</th>
                    <th scope="col" className="py-1 text-right font-semibold">Sold</th>
                    <th scope="col" className="py-1 text-right font-semibold">Costs</th>
                    <th scope="col" className="py-1 text-right font-semibold">Profit</th>
                  </tr>
                </thead>
                <tbody>
                  {costs.by_booking.map((b) => (
                    <tr key={b.order.id} className="border-t border-border/50">
                      <td className="py-1.5 pr-2">
                        <Link href={`/sales/orders/${b.order.id}`} target="_blank" rel="noopener" className="inline-flex items-center gap-1 font-medium hover:text-primary hover:underline">
                          {b.order.label} <ExternalLink className="size-3" aria-hidden="true" /><span className="sr-only">(opens in a new tab)</span>
                        </Link>
                      </td>
                      <td className="py-1.5 text-right tabular-nums">{fmtGBP(b.value_gbp)}</td>
                      <td className="py-1.5 text-right tabular-nums">{fmtGBP(b.costs_gbp)}</td>
                      <td className="py-1.5 text-right font-semibold tabular-nums" style={{ color: b.profit_gbp >= 0 ? "var(--ok)" : "var(--bad)" }}>{fmtGBP(b.profit_gbp)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function Fig({ label, value, tone, hint }: { label: string; value: string; tone?: "ok" | "bad"; hint?: string }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <dt className="flex items-center gap-0.5 text-muted-foreground">
        {label}
        {hint && <InfoHint>{hint}</InfoHint>}
      </dt>
      <dd className="font-semibold tabular-nums" style={tone ? { color: tone === "ok" ? "var(--ok)" : "var(--bad)" } : undefined}>
        {value}
      </dd>
    </div>
  );
}

function LineRow({
  l,
  cats,
  editing,
  editor,
  onEdit,
  onDelete,
  pending,
}: {
  l: CostLine;
  cats: Record<string, string>;
  editing: string | null;
  editor: (key: string) => React.ReactNode;
  onEdit: (l: CostLine) => void;
  onDelete: (id: string) => void;
  pending: boolean;
}) {
  if (editing === l.id) return <>{editor(l.id)}</>;
  const over = l.budget_gbp !== null && l.amount_gbp !== null && l.amount_gbp > l.budget_gbp;
  return (
    <tr className={`group border-t border-border/50 ${l.kind === "summary" ? "text-muted-foreground" : ""}`}>
      <td className="px-4 py-1.5 align-top">
        <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold whitespace-nowrap ${l.kind === "cost" ? "bg-muted" : l.kind === "income" ? "" : "text-muted-foreground"}`}
          style={l.kind === "income" ? { color: "var(--ok)" } : undefined}>
          {KIND_LABEL[l.kind]}
        </span>
      </td>
      <td className={`py-1.5 pr-2 ${l.kind === "note" ? "text-xs text-muted-foreground italic" : ""}`}>
        {l.label}
        {(l.category || l.order) && (
          <div className="mt-0.5 flex flex-wrap gap-x-2 text-[11px] text-muted-foreground not-italic">
            {l.category && <span>{cats[l.category] ?? l.category}</span>}
            {l.order && (
              <Link href={`/sales/orders/${l.order.id}`} target="_blank" rel="noopener" className="inline-flex items-center gap-0.5 hover:text-primary hover:underline">
                For {l.order.label} <ExternalLink className="size-2.5" aria-hidden="true" /><span className="sr-only">(opens in a new tab)</span>
              </Link>
            )}
          </div>
        )}
      </td>
      <td className="px-2 py-1.5 text-right text-xs tabular-nums text-muted-foreground">{l.budget_gbp !== null ? fmtGBP(l.budget_gbp) : ""}</td>
      <td className="px-2 py-1.5 text-right tabular-nums">
        {l.amount_gbp !== null && (
          <span className={l.kind === "summary" ? "" : "font-medium"} style={over ? { color: "var(--warn)" } : undefined} title={over ? "Over budget" : undefined}>
            {fmtGBP(l.amount_gbp)}
          </span>
        )}
        {l.amount_inc_vat_gbp !== null && <div className="text-[10.5px] text-muted-foreground">{fmtGBP(l.amount_inc_vat_gbp)} inc VAT</div>}
      </td>
      <td className="px-3 py-1.5 text-right whitespace-nowrap">
        {l.kind !== "summary" && (
          <span className="opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
            <Button size="icon-sm" variant="ghost" onClick={() => onEdit(l)} aria-label={`Edit ${l.label}`}><Pencil className="size-3.5" /></Button>
            <Button size="icon-sm" variant="ghost" disabled={pending} onClick={() => onDelete(l.id)} aria-label={`Remove ${l.label}`}><Trash2 className="size-3.5" /></Button>
          </span>
        )}
      </td>
    </tr>
  );
}
