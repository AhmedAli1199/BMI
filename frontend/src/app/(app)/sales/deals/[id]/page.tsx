import Link from "next/link";
import { notFound } from "next/navigation";
import { AlertTriangle, ExternalLink } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { Deal, DealScheduleRow } from "@/lib/deals-types";
import { DealActions } from "@/components/deals/deal-actions";
import { DealStatusPill } from "@/components/deals/deal-ui";
import { InfoHint } from "@/components/sales/info-hint";
import { SalesHeader, fmtDate, fmtGBP } from "@/components/sales/sales-ui";

const XERO: Record<string, [string, string]> = {
  paid: ["Paid", "var(--ok)"], part_paid: ["Part paid", "var(--warn)"], unpaid: ["Awaiting payment", "var(--muted-foreground)"],
  overdue: ["Overdue", "var(--bad)"], voided: ["Voided", "var(--muted-foreground)"], not_in_xero: ["Not found in Xero", "var(--warn)"],
};

function Tile({ label, value, hint, strong }: { label: string; value: string; hint?: string; strong?: boolean }) {
  return (
    <div className={`rounded-xl border p-3 shadow-2xs ${strong ? "border-primary/40 bg-primary/5" : "border-border/80 bg-card"}`}>
      <div className="flex items-center gap-1 text-xs font-semibold text-muted-foreground">{label}{hint && <InfoHint>{hint}</InfoHint>}</div>
      <div className={`mt-1 tabular-nums ${strong ? "text-2xl font-bold" : "text-lg font-semibold"}`}>{value}</div>
    </div>
  );
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-semibold text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 whitespace-pre-line break-words text-sm">{children || "—"}</dd>
    </div>
  );
}

function copySoon(r: DealScheduleRow) {
  if (!r.copy_due || r.published) return false;
  const days = (new Date(r.copy_due).getTime() - Date.now()) / 86400000;
  return days <= 14;
}

export default async function DealPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let d: Deal;
  try {
    d = await backendFetch<Deal>(`/api/sales/deals/${id}`);
  } catch {
    notFound();
  }
  const t = d.totals;
  const live = d.schedule.filter((r) => r.status !== "cancelled");
  const ready = live.filter((r) => r.ready_to_invoice);
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-5 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title={`Order ${d.number}: ${d.client_name}`}
        crumbs={[{ label: "Sales Orders", href: "/sales" }, { label: "Orders", href: "/sales/deals" }]}
        description={[d.insertions, d.rep ? `Sold by ${d.split_names.length ? d.split_names.map((s) => `${s.name} (${Math.round(s.pct * 100)}%)`).join(" and ") : d.rep.name}` : null, `ordered ${fmtDate(d.booked_on)}`].filter(Boolean).join(" · ")}
        actions={<DealActions d={d} />}
      />

      <div className="flex flex-wrap items-center gap-2 text-sm">
        <DealStatusPill status={d.status} />
        {d.status === "pencilled" && <span className="text-muted-foreground">Held for the client. It doesn&apos;t count in sales figures or commission until it&apos;s confirmed.</span>}
        {d.status === "cancelled" && <span className="text-muted-foreground">Cancelled: {d.cancelled_reason}</span>}
        {d.sent_at
          ? <span className="text-muted-foreground">· {d.document === "schedule" ? "Schedule" : "Confirmation"} sent {fmtDate(d.sent_at.slice(0, 10))}{d.sent_to ? ` to ${d.sent_to}` : ""}</span>
          : d.status === "confirmed" && <span style={{ color: "var(--warn)" }}>· The {d.document === "schedule" ? "schedule of works" : "confirmation"} hasn&apos;t been sent yet</span>}
        {d.rebooked_from_id && <Link href={`/sales/deals/${d.rebooked_from_id}`} className="text-primary hover:underline">· Rebooked from order {d.rebooked_from_number}</Link>}
        {d.proposal_id && <Link href={`/sales/proposals/${d.proposal_id}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline">· From a proposal <ExternalLink className="size-3" aria-hidden="true" /></Link>}
      </div>

      {d.warnings.length > 0 && (
        <ul className="flex flex-col gap-1 rounded-xl border px-4 py-3 text-sm" style={{ borderColor: "color-mix(in oklab, var(--warn) 40%, transparent)", background: "color-mix(in oklab, var(--warn) 8%, transparent)" }}>
          {d.warnings.map((w) => <li key={w} className="flex gap-2"><AlertTriangle className="mt-0.5 size-4 shrink-0" style={{ color: "var(--warn)" }} aria-hidden="true" />{w}</li>)}
        </ul>
      )}

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6" aria-label="Totals">
        <Tile label="Order total" value={fmtGBP(t.total_gbp)} strong hint="What was agreed, before VAT." />
        <Tile label="Agency commission" value={fmtGBP(t.agency_gbp)} />
        <Tile label="To invoice in all" value={fmtGBP(t.payable_gbp)} hint="The total less any agency's commission, before VAT." />
        <Tile label="Invoiced so far" value={fmtGBP(t.invoiced_gbp)} />
        <Tile label="Ready to invoice" value={fmtGBP(t.to_invoice_gbp)} hint={d.invoice_plan === "upfront" ? "Everything not invoiced yet - this order is invoiced up front." : "Items that have run and aren't invoiced yet."} />
        <Tile label="Below rate card" value={t.off_rate_card_pct != null ? `${t.off_rate_card_pct}%` : "—"} hint={`Rate card value ${fmtGBP(t.rate_card_gbp)}${t.added_value_gbp ? `, of which ${fmtGBP(t.added_value_gbp)} given free` : ""}.`} />
      </section>

      <section className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs" aria-labelledby="sched-h">
        <h2 id="sched-h" className="flex items-center gap-1 border-b border-border/70 px-4 py-3 text-sm font-bold">
          Schedule <InfoHint>Every item is a booking in its own issue, month or event. Each earns commission and counts in that issue&apos;s figures when it runs.</InfoHint>
          {ready.length > 0 && <span className="ml-2 rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ color: "var(--warn)", background: "color-mix(in oklab, var(--warn) 12%, transparent)" }}>{ready.length} ready to invoice</span>}
        </h2>
        <table className="w-full min-w-[56rem] text-sm">
          <thead>
            <tr className="border-b border-border/70 text-left text-xs text-muted-foreground">
              <th scope="col" className="px-4 py-2 font-semibold">Runs</th>
              <th scope="col" className="px-2 py-2 font-semibold">Item</th>
              <th scope="col" className="px-2 py-2 font-semibold">Issue, month or event</th>
              <th scope="col" className="px-2 py-2 font-semibold">Copy due</th>
              <th scope="col" className="px-2 py-2 text-right font-semibold">Value</th>
              <th scope="col" className="px-4 py-2 font-semibold">Invoice</th>
            </tr>
          </thead>
          <tbody>
            {d.schedule.map((r, i) => (
              <tr key={r.order_id ?? i} className={`border-b border-border/60 last:border-0 ${r.status === "cancelled" ? "text-muted-foreground line-through" : ""}`}>
                <td className="whitespace-nowrap px-4 py-2 tabular-nums">{fmtDate(r.runs_on)}{r.published && r.status !== "cancelled" && <span className="ml-1 text-[11px] text-muted-foreground no-underline">ran</span>}</td>
                <td className="px-2 py-2">
                  {r.order_id ? <Link href={`/sales/orders/${r.order_id}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium hover:underline">{r.description || "Item"} <ExternalLink className="size-3 text-muted-foreground" aria-label="Open the booking" /></Link> : r.description}
                  {r.added_value && <span className="ml-1.5 rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground">Free</span>}
                  {r.status === "cancelled" && <span className="ml-1.5 text-[11px]">cancelled</span>}
                </td>
                <td className="px-2 py-2">
                  {r.edition_id ? <Link href={`/sales/editions/${r.edition_id}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline">{r.edition} <ExternalLink className="size-3" aria-hidden="true" /></Link> : "—"}
                </td>
                <td className="whitespace-nowrap px-2 py-2 tabular-nums" style={copySoon(r) ? { color: "var(--warn)", fontWeight: 600 } : undefined}>{fmtDate(r.copy_due)}</td>
                <td className="px-2 py-2 text-right tabular-nums">{r.added_value ? "—" : fmtGBP(r.value_gbp)}{r.agency_gbp ? <div className="text-[11px] text-muted-foreground">less {fmtGBP(r.agency_gbp)} agency</div> : null}</td>
                <td className="px-4 py-2 text-xs">
                  {r.invoice_number ? (
                    <span>{r.invoice_number}{r.xero_state && XERO[r.xero_state] && <span className="ml-1.5 font-semibold" style={{ color: XERO[r.xero_state][1] }}>{XERO[r.xero_state][0]}</span>}</span>
                  ) : r.ready_to_invoice ? <span className="font-semibold" style={{ color: "var(--warn)" }}>Ready to invoice</span>
                    : r.added_value || r.status === "cancelled" ? "" : <span className="text-muted-foreground">{d.invoice_plan === "on_publication" ? "When it runs" : "Not yet"}</span>}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="bg-muted/30">
              <td colSpan={4} className="px-4 py-2 font-bold">{live.length} item{live.length === 1 ? "" : "s"}{t.discount_gbp ? ` · ${fmtGBP(t.discount_gbp)} discount` : ""}</td>
              <td className="px-2 py-2 text-right font-bold tabular-nums">{fmtGBP(t.total_gbp)}</td>
              <td />
            </tr>
          </tfoot>
        </table>
      </section>

      <section className="grid gap-4 rounded-xl border border-border/80 bg-card p-4 shadow-2xs sm:grid-cols-2 lg:grid-cols-4" aria-label="Details">
        <Detail label="Their contact">{[d.contact_name, d.contact_email].filter(Boolean).join("\n")}</Detail>
        <Detail label="Confirmation address">{d.confirmation_address}</Detail>
        <Detail label="Invoice to">{[d.invoice_to, d.invoice_email ? `Email: ${d.invoice_email}` : null].filter(Boolean).join("\n")}</Detail>
        <Detail label="Their order or PO number">{d.po_number}</Detail>
        <Detail label="Agency">{d.agency_name ? `${d.agency_name}${d.agency_pct ? ` (${Math.round(d.agency_pct * 1000) / 10}%)` : ""}` : null}</Detail>
        <Detail label="Invoicing">{{ upfront: "All of it now", on_publication: "Each item as it runs", custom: "As agreed" }[d.invoice_plan]}</Detail>
        <Detail label="Client company">{d.company_id ? <Link href={`/companies/${d.company_id}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline">{d.client_name} <ExternalLink className="size-3" aria-hidden="true" /></Link> : d.client_name}</Detail>
        <Detail label="Document">{d.document === "schedule" ? "Schedule of works" : "Order confirmation"}</Detail>
        {(d.special_instructions || d.copy_instructions || d.production_contact) && (
          <div className="sm:col-span-2 lg:col-span-4 grid gap-4 sm:grid-cols-3">
            <Detail label="Special instructions">{d.special_instructions}</Detail>
            <Detail label="Copy and artwork">{d.copy_instructions}</Detail>
            <Detail label="Production contact">{d.production_contact}</Detail>
          </div>
        )}
        {d.notes && <div className="sm:col-span-2 lg:col-span-4"><Detail label="Notes for the team">{d.notes}</Detail></div>}
      </section>
    </div>
  );
}
