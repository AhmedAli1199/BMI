"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { AlertTriangle, Building2, Plus, Search } from "lucide-react";
import type { SalesOrder, SalesRep } from "@/lib/sales-types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { OrderSheet, type OrderSheetTarget } from "@/components/sales/order-sheet";
import { OrderStatusPill, fmtDate, fmtGBP } from "@/components/sales/sales-ui";

type FilterKey = "all" | "uninvoiced" | "check" | "inactive";

const FILTERS: { key: FilterKey; label: string; test: (o: SalesOrder) => boolean }[] = [
  { key: "all", label: "All bookings", test: () => true },
  { key: "uninvoiced", label: "Awaiting invoice", test: (o) => o.status === "booked" && o.value_gbp > 0 && !o.invoice_number },
  { key: "check", label: "Needs a check", test: (o) => !!o.import_warning },
  { key: "inactive", label: "Cancelled, contra & moved", test: (o) => o.status !== "booked" },
];

export function isOverdue(o: SalesOrder): boolean {
  return !!o.edition_date && new Date(o.edition_date) < new Date() && o.status === "booked" && o.value_gbp > 0 && !o.invoice_number;
}

function InvoiceCell({ o }: { o: SalesOrder }) {
  if (o.status !== "booked" || o.value_gbp === 0) {
    return o.order_ref ? (
      <span className="text-[11px] text-muted-foreground" title="Ticket / order number from the sheet - not a BMI invoice">
        Order {o.order_ref}
      </span>
    ) : (
      <span className="text-muted-foreground" title="Nothing to invoice">—</span>
    );
  }
  if (!o.invoice_number) {
    const overdue = isOverdue(o);
    return (
      <span
        className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold"
        style={{
          color: overdue ? "var(--warn)" : "var(--muted-foreground)",
          background: overdue ? "color-mix(in oklab, var(--warn) 12%, transparent)" : "var(--muted)",
        }}
        title={overdue ? "The edition has published / the event has run and there's still no invoice" : "Not invoiced yet"}
      >
        {overdue ? "Overdue" : "Not yet"}
      </span>
    );
  }
  const diff = o.invoice_value_gbp !== null ? o.value_gbp - o.invoice_value_gbp - (o.agency_commission_gbp ?? 0) : 0;
  return (
    <span className="flex flex-col leading-tight">
      <span className="font-medium text-foreground">{o.invoice_number}</span>
      {Math.abs(diff) > 1 &&
        (o.invoice_note ? (
          <span className="text-[11px] text-muted-foreground" title={`Reason for difference: ${o.invoice_note}`}>
            {fmtGBP(o.invoice_value_gbp)} invoiced · explained
          </span>
        ) : (
          <span className="text-[11px]" style={{ color: "var(--warn)" }} title="Invoiced amount differs from the booking value and no reason is recorded">
            {fmtGBP(o.invoice_value_gbp)} invoiced
          </span>
        ))}
    </span>
  );
}

export function OrdersTable({
  orders,
  reps,
  canDelete,
  year,
  showEdition = false,
  showFilters = true,
  addTo,
  emptyText = "No bookings here yet.",
  initialFilter = "all",
}: {
  orders: SalesOrder[];
  reps: SalesRep[];
  canDelete: boolean;
  year: number;
  showEdition?: boolean;
  showFilters?: boolean;
  addTo?: { editionId: string; titleId: string; editionLabel: string };
  emptyText?: string;
  initialFilter?: FilterKey;
}) {
  const [filter, setFilter] = useState<FilterKey>(initialFilter);
  const [q, setQ] = useState("");
  const [target, setTarget] = useState<OrderSheetTarget | null>(null);

  const counts = useMemo(() => Object.fromEntries(FILTERS.map((f) => [f.key, orders.filter(f.test).length])), [orders]);
  const shown = useMemo(() => {
    const f = FILTERS.find((x) => x.key === filter)!;
    const needle = q.trim().toLowerCase();
    return orders.filter(
      (o) => f.test(o) && (!needle || o.client_name.toLowerCase().includes(needle) || (o.invoice_number ?? "").toLowerCase().includes(needle))
    );
  }, [orders, filter, q]);
  const shownTotal = shown.filter((o) => o.status === "booked").reduce((s, o) => s + o.value_gbp, 0);

  return (
    <div className="flex flex-col gap-3">
      {(showFilters || addTo) && (
        <div className="flex flex-wrap items-center justify-between gap-2">
          {showFilters ? (
            <div role="tablist" aria-label="Filter bookings" className="flex flex-wrap gap-1">
              {FILTERS.filter((f) => f.key === "all" || counts[f.key] > 0).map((f) => (
                <button
                  key={f.key}
                  role="tab"
                  type="button"
                  aria-selected={filter === f.key}
                  onClick={() => setFilter(f.key)}
                  className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-ring ${
                    filter === f.key ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  {f.label}
                  <span className={`rounded-full px-1.5 text-[10px] tabular-nums ${filter === f.key ? "bg-primary-foreground/20" : "bg-muted"}`}>{counts[f.key]}</span>
                </button>
              ))}
            </div>
          ) : (
            <span />
          )}
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
              <Input aria-label="Search client or invoice number" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Client or invoice…" className="h-8 w-52 pl-8 text-xs" />
            </div>
            {addTo && (
              <Button size="sm" className="gap-1.5" onClick={() => setTarget({ mode: "create", ...addTo, year })}>
                <Plus className="size-3.5" aria-hidden="true" /> Add booking
              </Button>
            )}
          </div>
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
        <table className="w-full min-w-[820px] text-sm">
          <caption className="sr-only">Bookings - select a client to open and edit the booking</caption>
          <thead>
            <tr className="border-b border-border/70 text-left text-xs font-semibold text-muted-foreground">
              <th scope="col" className="px-4 py-2.5 font-semibold">Client</th>
              {showEdition && <th scope="col" className="px-3 py-2.5 font-semibold">Edition</th>}
              <th scope="col" className="px-3 py-2.5 font-semibold">Booked</th>
              <th scope="col" className="px-3 py-2.5 font-semibold">What</th>
              <th scope="col" className="px-3 py-2.5 font-semibold">Rep</th>
              <th scope="col" className="px-3 py-2.5 text-right font-semibold">Value</th>
              <th scope="col" className="px-3 py-2.5 font-semibold">Invoice</th>
              <th scope="col" className="px-4 py-2.5 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody>
            {shown.length === 0 && (
              <tr>
                <td colSpan={showEdition ? 8 : 7} className="px-4 py-10 text-center text-sm text-muted-foreground">
                  {q ? `No bookings match “${q}”.` : emptyText}
                </td>
              </tr>
            )}
            {shown.map((o) => {
              const inactive = o.status !== "booked";
              return (
                <tr
                  key={o.id}
                  onClick={(e) => {
                    if ((e.target as HTMLElement).closest("a,button")) return;
                    setTarget({ mode: "edit", order: o, year });
                  }}
                  className="cursor-pointer border-b border-border/60 align-top transition-colors last:border-0 hover:bg-accent/40"
                >
                  <td className="px-4 py-2.5">
                    <div className="flex items-start gap-1.5">
                      <button
                        type="button"
                        className={`text-left font-semibold hover:underline focus-visible:outline-2 focus-visible:outline-ring ${inactive ? "text-muted-foreground" : "text-foreground"}`}
                        onClick={() => setTarget({ mode: "edit", order: o, year })}
                      >
                        {o.client_name}
                      </button>
                      {o.import_warning && (
                        <AlertTriangle className="mt-0.5 size-3.5 shrink-0" style={{ color: "var(--warn)" }} aria-label="Needs a check" />
                      )}
                    </div>
                    {o.company && (
                      <Link href={`/companies/${o.company.id}`} className="mt-0.5 inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-primary">
                        <Building2 className="size-3" aria-hidden="true" />
                        {o.company.label}
                      </Link>
                    )}
                  </td>
                  {showEdition && (
                    <td className="px-3 py-2.5 text-xs">
                      <Link href={`/sales/editions/${o.edition_id}`} className="font-medium text-foreground hover:text-primary hover:underline">
                        {o.edition_label}
                      </Link>
                      {o.edition_date && <div className="text-[11px] text-muted-foreground">{fmtDate(o.edition_date)}</div>}
                    </td>
                  )}
                  <td className="px-3 py-2.5 text-xs whitespace-nowrap text-muted-foreground">{fmtDate(o.booked_on)}</td>
                  <td className="px-3 py-2.5 text-xs">
                    <span className="text-foreground">{o.size ?? "—"}</span>
                    {o.series && <span className="text-muted-foreground"> · {o.series}</span>}
                    {o.position && <div className="text-[11px] text-muted-foreground">p. {o.position}</div>}
                  </td>
                  <td className="px-3 py-2.5 text-xs whitespace-nowrap">
                    {o.credits.length > 1 ? (
                      <span title={o.credits.map((c) => `${c.name}: ${fmtGBP(c.amount_gbp)}`).join("\n")}>{o.credits.map((c) => c.code).join(" / ")}</span>
                    ) : (
                      <span title={o.rep?.name}>{o.rep?.code ?? <span className="text-muted-foreground">—</span>}</span>
                    )}
                  </td>
                  <td className={`px-3 py-2.5 text-right tabular-nums whitespace-nowrap ${inactive ? "text-muted-foreground line-through decoration-muted-foreground/50" : "font-semibold text-foreground"}`}>
                    {fmtGBP(o.value_gbp)}
                  </td>
                  <td className="px-3 py-2.5 text-xs">
                    <InvoiceCell o={o} />
                  </td>
                  <td className="px-4 py-2.5">
                    <OrderStatusPill status={o.status} />
                    {o.moved_to && <div className="mt-0.5 text-[11px] text-muted-foreground">→ {o.moved_to.label}</div>}
                    {o.status !== "booked" && !o.moved_to && o.status_reason && (
                      <div className="mt-0.5 max-w-44 truncate text-[11px] text-muted-foreground" title={`Sheet said: ${o.status_reason}`}>
                        “{o.status_reason}”
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
          {shown.length > 1 && (
            <tfoot>
              <tr className="border-t border-border/70 bg-muted/30 text-xs">
                <td colSpan={showEdition ? 5 : 4} className="px-4 py-2 font-semibold text-muted-foreground">
                  {shown.length} bookings shown
                </td>
                <td className="px-3 py-2 text-right font-bold tabular-nums text-foreground">{fmtGBP(shownTotal)}</td>
                <td colSpan={2} className="px-4 py-2 text-muted-foreground">booked value (live bookings only)</td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>

      <OrderSheet target={target} reps={reps} canDelete={canDelete} onClose={() => setTarget(null)} />
    </div>
  );
}
