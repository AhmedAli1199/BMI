"use client";

import { useState, useTransition } from "react";
import { Check, Pencil, Plus, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import type { CostLine, CostLineInput, EditionCosts } from "@/lib/sales-types";
import { deleteCostLine, saveCostLine } from "@/lib/sales-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { InfoHint } from "@/components/sales/info-hint";
import { fmtGBP } from "@/components/sales/sales-ui";
import { friendlyError } from "@/lib/errors";

const KIND_LABEL: Record<CostLine["kind"], string> = { cost: "Cost", income: "Income", summary: "Sheet total", note: "Note" };

type Draft = { kind: CostLineInput["kind"]; label: string; amount: string; section: string };

/** An event's direct costs next to its revenue - venue, food, AV, travel,
 * photographer, overheads - and the profit they leave. Lines come from the
 * events sheet's cost block on import; anyone can add, correct or remove
 * lines here. The sheet's own totals are shown greyed for reference but
 * never added up: totals and profit are always calculated from the lines. */
export function EditionCostsPanel({ editionId, booked, costs: initial }: { editionId: string; booked: number; costs: EditionCosts }) {
  const [costs, setCosts] = useState(initial);
  const [editing, setEditing] = useState<string | "new" | null>(null);
  const [draft, setDraft] = useState<Draft>({ kind: "cost", label: "", amount: "", section: "" });
  const [pending, start] = useTransition();

  // Lines in sheet order; a text line that other lines sit under is shown
  // as a heading (an event day / venue) with its subtotal.
  const headings = new Set(costs.lines.map((l) => l.section).filter(Boolean) as string[]);
  const subtotal = (section: string) =>
    costs.lines.filter((l) => l.section === section && l.kind === "cost").reduce((t, l) => t + (l.amount_gbp ?? 0), 0);
  const sections = [...headings];
  const margin = costs.profit_gbp !== null && booked ? costs.profit_gbp / booked : null;

  function edit(l?: CostLine) {
    setEditing(l ? l.id : "new");
    setDraft(
      l
        ? { kind: l.kind === "summary" ? "note" : l.kind, label: l.label, amount: l.amount_gbp?.toString() ?? "", section: l.section ?? "" }
        : { kind: "cost", label: "", amount: "", section: sections[sections.length - 1] ?? "" }
    );
  }

  function save() {
    if (!draft.label.trim()) return toast.error("Describe the line");
    const amount = draft.amount.trim() ? Number(draft.amount) : null;
    if (amount !== null && Number.isNaN(amount)) return toast.error("The amount isn't a number");
    start(async () => {
      try {
        setCosts(
          await saveCostLine(
            editionId,
            { kind: draft.kind, label: draft.label.trim(), amount_gbp: draft.kind === "note" ? null : amount, section: draft.section.trim() || null },
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
        <div className="flex gap-2">
          <select
            aria-label="Type"
            value={draft.kind}
            onChange={(e) => setDraft({ ...draft, kind: e.target.value as Draft["kind"] })}
            className="h-8 rounded-md border border-input bg-background px-2 text-xs"
          >
            <option value="cost">Cost</option>
            <option value="income">Other income</option>
            <option value="note">Note</option>
          </select>
          <Input aria-label="Description" value={draft.label} onChange={(e) => setDraft({ ...draft, label: e.target.value })} placeholder="e.g. Room hire, AV, photographer" className="h-8 text-sm" autoFocus />
        </div>
        <Input aria-label="Section" value={draft.section} onChange={(e) => setDraft({ ...draft, section: e.target.value })} placeholder="Section (optional) - e.g. Edinburgh 27th January" className="mt-1.5 h-7 text-xs" />
      </td>
      <td className="px-2 py-2 align-top">
        {draft.kind !== "note" && (
          <Input aria-label="Amount in £" type="number" step="0.01" value={draft.amount} onChange={(e) => setDraft({ ...draft, amount: e.target.value })} placeholder="£" className="h-8 text-right text-sm tabular-nums" />
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
            Direct costs of running this event, from the cost block under the bookings on the original sheet - add or correct lines here.
            Profit is the booked value minus the cost lines. Greyed &ldquo;sheet total&rdquo; lines are the sheet&apos;s own sums, shown for
            reference only. Amounts are as written on the sheet (mostly before VAT).
          </InfoHint>
        </h2>
        <dl className="ml-auto flex flex-wrap gap-x-6 gap-y-1 text-xs">
          <Fig label="Booked" value={fmtGBP(booked)} />
          <Fig label="Costs" value={fmtGBP(costs.total_costs_gbp)} />
          {costs.other_income_gbp > 0 && <Fig label="Other income" value={fmtGBP(costs.other_income_gbp)} hint="Income lines from the sheet (e.g. a sponsorship line) - usually the same money as the bookings, so not added to profit." />}
          {costs.profit_gbp !== null && (
            <Fig
              label="Profit"
              value={`${fmtGBP(costs.profit_gbp)}${margin !== null ? ` · ${Math.round(margin * 100)}%` : ""}`}
              tone={costs.profit_gbp >= 0 ? "ok" : "bad"}
            />
          )}
        </dl>
      </header>
      <table className="w-full text-sm">
        <caption className="sr-only">Cost lines</caption>
        <tbody>
          {costs.lines.map((l) =>
            l.kind === "note" && headings.has(l.label) && editing !== l.id ? (
              <tr key={l.id} className="group border-t border-border/70 bg-muted/40">
                <th scope="rowgroup" colSpan={2} className="px-4 py-1.5 text-left text-xs font-semibold">{l.label}</th>
                <td className="px-2 py-1.5 text-right text-xs font-semibold tabular-nums text-muted-foreground">
                  {subtotal(l.label) ? fmtGBP(subtotal(l.label)) : ""}
                </td>
                <td className="px-3 py-1 text-right">
                  <span className="opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
                    <Button size="icon-sm" variant="ghost" onClick={() => edit(l)} aria-label={`Edit ${l.label}`}><Pencil className="size-3.5" /></Button>
                  </span>
                </td>
              </tr>
            ) : (
              <LineRow key={l.id} l={l} editing={editing} editor={editor} onEdit={edit} onDelete={remove} pending={pending} />
            )
          )}
          {costs.lines.length === 0 && editing !== "new" && (
            <tr>
              <td colSpan={4} className="px-4 py-5 text-sm text-muted-foreground">
                No costs recorded for this edition. Add venue, catering, AV, travel and other direct costs to see its profit.
              </td>
            </tr>
          )}
          {editing === "new" && editor("new")}
        </tbody>
      </table>
      {editing === null && (
        <div className="border-t border-border/60 px-4 py-2">
          <Button size="sm" variant="ghost" className="gap-1.5" onClick={() => edit()}>
            <Plus className="size-3.5" /> Add a line
          </Button>
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
  editing,
  editor,
  onEdit,
  onDelete,
  pending,
}: {
  l: CostLine;
  editing: string | null;
  editor: (key: string) => React.ReactNode;
  onEdit: (l: CostLine) => void;
  onDelete: (id: string) => void;
  pending: boolean;
}) {
  if (editing === l.id) return <>{editor(l.id)}</>;
  return (
    <tr className={`group border-t border-border/50 ${l.kind === "summary" ? "text-muted-foreground" : ""}`}>
      <td className="w-28 px-4 py-1.5 align-top">
        <span
          className={`rounded px-1.5 py-0.5 text-[10px] font-semibold whitespace-nowrap ${
            l.kind === "cost" ? "bg-muted" : l.kind === "income" ? "text-emerald-700 dark:text-emerald-300" : "text-muted-foreground"
          }`}
        >
          {KIND_LABEL[l.kind]}
        </span>
      </td>
      <td className={`py-1.5 pr-2 ${l.kind === "note" ? "text-xs text-muted-foreground italic" : ""}`}>{l.label}</td>
      <td className="w-36 px-2 py-1.5 text-right tabular-nums">
        {l.amount_gbp !== null && <span className={l.kind === "summary" ? "" : "font-medium"}>{fmtGBP(l.amount_gbp)}</span>}
        {l.amount_inc_vat_gbp !== null && <div className="text-[10.5px] text-muted-foreground">{fmtGBP(l.amount_inc_vat_gbp)} inc VAT</div>}
      </td>
      <td className="w-24 px-3 py-1.5 text-right whitespace-nowrap">
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
