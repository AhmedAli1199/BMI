import Link from "next/link";
import { ReceiptText } from "lucide-react";
import type { CompanyBookings, SalesRep } from "@/lib/sales-types";
import { OrdersTable } from "@/components/sales/orders-table";
import { InfoHint } from "@/components/sales/info-hint";
import { EmptyState, fmtDate, fmtGBP } from "@/components/sales/sales-ui";

/** The company page's Bookings tab - everything this company has booked,
 * across every title and year, from the Sales Order Register. */
export function CompanyBookingsPanel({ data, reps, canDelete }: { data: CompanyBookings; reps: SalesRep[]; canDelete: boolean }) {
  if (data.items.length === 0) {
    return (
      <EmptyState icon={ReceiptText} title="No bookings linked to this company">
        Bookings in the order register link to a company when their client name matches it exactly, or when someone confirms a suggested
        match in the Review Queue. You can also link one from the booking itself on its{" "}
        <Link href="/sales/editions" className="font-semibold text-primary hover:underline">
          edition page
        </Link>
        .
      </EmptyState>
    );
  }
  const years = Object.entries(data.by_year).sort(([a], [b]) => Number(a) - Number(b));
  const yMax = Math.max(...years.map(([, v]) => v), 1);
  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-4 rounded-xl border border-border/80 bg-card p-4 shadow-2xs sm:grid-cols-[1fr_auto]">
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-4">
          <div>
            <dt className="flex items-center gap-1 text-xs font-semibold text-muted-foreground">
              Lifetime value
              <InfoHint>Every live booking linked to this company, across all titles and years. Cancelled, contra and moved bookings aren&apos;t counted.</InfoHint>
            </dt>
            <dd className="font-serif text-xl font-bold tabular-nums">{fmtGBP(data.lifetime_gbp, { compact: true })}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold text-muted-foreground">Bookings</dt>
            <dd className="font-serif text-xl font-bold tabular-nums">{data.orders}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold text-muted-foreground">Last booked</dt>
            <dd className="font-medium">{fmtDate(data.last_booked)}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold text-muted-foreground">Titles</dt>
            <dd className="text-xs font-medium leading-snug">{data.titles.join(", ") || "—"}</dd>
          </div>
        </dl>
        {years.length > 1 && (
          <div className="flex items-end gap-1.5" aria-label="Booked value by year">
            {years.map(([y, v]) => (
              <div key={y} className="flex flex-col items-center gap-1" title={`${y}: ${fmtGBP(v)}`}>
                <div className="flex h-12 w-7 items-end rounded-sm bg-muted">
                  <div className="w-full rounded-sm" style={{ height: `${Math.max(4, (v / yMax) * 100)}%`, background: "var(--chart-2)" }} />
                </div>
                <span className="text-[10px] text-muted-foreground tabular-nums">{y}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      <OrdersTable orders={data.items} reps={reps} canDelete={canDelete} year={new Date().getFullYear()} showEdition showFilters={false} />
    </div>
  );
}
