"use client";

import Link from "next/link";
import { useMemo } from "react";
import { ChevronRight, UserX } from "lucide-react";
import type { Commissions } from "@/lib/sales-types";
import type { FilterDef, SortState } from "@/lib/data-view/schema";
import type { Accessors, SortAccessors } from "@/lib/data-view/client-engine";
import { KpiTile } from "@/components/automations/hub-ui";
import { ClientDataView } from "@/components/data-view/client-data-view";
import { DataViewLayout } from "@/components/data-view/data-view";
import { FilterSidebar } from "@/components/data-view/filter-sidebar";
import { DataSearch, FilterChips, SortableTh } from "@/components/data-view/toolbar";
import { InfoHint } from "@/components/sales/info-hint";
import { EmptyState, fmtDate, fmtGBP } from "@/components/sales/sales-ui";

type RepBlock = Commissions["reps"][number];
/** One salesperson's credit on one edition - the unit that's filtered and sorted. */
type Row = RepBlock["editions"][number] & { repId: string };

const DEFAULT_SORT: SortState = { key: "date", dir: "asc" };

const ACCESSORS: Accessors<Row> = {
  q: (r) => [r.edition.label, r.title],
  rep: (r) => r.repId,
  title: (r) => r.title,
  credit: (r) => r.credit_gbp,
  date: (r) => r.edition_date,
};

const SORTS: SortAccessors<Row> = {
  edition: (r) => r.edition.label,
  title: (r) => r.title,
  date: (r) => r.edition_date,
  orders: (r) => r.orders,
  credit: (r) => r.credit_gbp,
  commission: (r) => r.commission_gbp,
};

/** Commission by salesperson, broken down by edition. Filtering (a title,
 * a period, a person) recalculates every total, so "what did Steve earn on
 * Onboard Hospitality in Q2?" is two clicks. */
export function CommissionsExplorer({ data }: { data: Commissions }) {
  const rows = useMemo<Row[]>(() => data.reps.flatMap((r) => r.editions.map((e) => ({ ...e, repId: r.rep.id }))), [data]);
  const defs = useMemo<FilterDef[]>(() => {
    const titles = [...new Set(rows.map((r) => r.title))].sort();
    return [
      { kind: "search", key: "q", label: "Search editions", placeholder: "Edition or title…" },
      ...(data.scoped_to_me
        ? []
        : [{
            kind: "multi" as const, key: "rep", label: "Salesperson", section: "Who", searchable: true,
            options: data.reps.map((r) => ({ value: r.rep.id, label: `${r.rep.name}${r.rep.active ? "" : " (former)"}` })),
          }]),
      { kind: "multi", key: "title", label: "Title", section: "What", searchable: true, options: titles.map((t) => ({ value: t, label: t.replace(/\s*\(.*\)/, "") })) },
      { kind: "dates", key: "date", label: "Edition / event date", section: "When", hint: "Commission is counted on the edition's date - e.g. pick a quarter to see that quarter's commission." },
      { kind: "range", key: "credit", label: "Credited per edition", section: "Amount", prefix: "£", step: 500 },
    ];
  }, [rows, data]);

  return (
    <ClientDataView rows={rows} defs={defs} defaultSort={DEFAULT_SORT} accessors={ACCESSORS} sortAccessors={SORTS}>
      {(visible) => <Body data={data} visible={visible} />}
    </ClientDataView>
  );
}

function Body({ data, visible }: { data: Commissions; visible: Row[] }) {
  const blocks = data.reps
    .map((r) => {
      const eds = visible.filter((v) => v.repId === r.rep.id);
      return {
        rep: r.rep,
        editions: eds,
        credit: eds.reduce((s, e) => s + e.credit_gbp, 0),
        commission: eds.reduce((s, e) => s + e.commission_gbp, 0),
        orders: eds.reduce((s, e) => s + e.orders, 0),
      };
    })
    .filter((b) => b.editions.length)
    .sort((a, b) => b.commission - a.commission);
  const totalCredit = blocks.reduce((s, b) => s + b.credit, 0);
  const totalCommission = blocks.reduce((s, b) => s + b.commission, 0);

  return (
    <DataViewLayout sidebar={<FilterSidebar title="Filter commission" />}>
      {!data.scoped_to_me && (
        <section aria-label="Totals" className="grid gap-4 sm:grid-cols-3">
          <KpiTile label="Credited bookings" value={fmtGBP(totalCredit, { compact: true })} footer={`${blocks.length} salespeople`} />
          <KpiTile
            label="Commission"
            value={fmtGBP(totalCommission, { compact: true })}
            footer={
              <span className="flex items-center gap-1">
                at each person&apos;s rate
                <InfoHint>
                  2% of each person&apos;s credited share of live bookings, unless a different rate is set on the booking itself. Every
                  &ldquo;Commission payable&rdquo; figure in the 2026 sheets works out at 2% (two at 5%) - BMI to confirm the rule for the exceptions.
                </InfoHint>
              </span>
            }
          />
          <KpiTile label="Bookings" value={blocks.reduce((s, b) => s + b.orders, 0).toLocaleString("en-GB")} footer="live bookings credited" />
        </section>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <DataSearch />
      </div>
      <FilterChips />

      {blocks.length === 0 ? (
        <EmptyState icon={UserX} title="Nothing matches these filters">Try removing a filter.</EmptyState>
      ) : (
        <section aria-label="By salesperson" className="flex flex-col gap-3">
          {blocks.map((b) => (
            <details key={b.rep.id} open={data.scoped_to_me || blocks.length === 1} className="group overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs">
              <summary className="flex cursor-pointer list-none items-center gap-4 px-4 py-3.5 hover:bg-accent/30 [&::-webkit-details-marker]:hidden">
                <ChevronRight className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-90" aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <div className="font-semibold text-foreground">
                    {b.rep.name}
                    {!b.rep.active && <span className="font-normal text-muted-foreground"> · former</span>}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {b.orders} bookings across {b.editions.length} editions · {Math.round(b.rep.commission_rate * 1000) / 10}% rate
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-muted-foreground">Credited</div>
                  <div className="font-semibold tabular-nums">{fmtGBP(b.credit)}</div>
                </div>
                <div className="w-28 text-right">
                  <div className="text-xs text-muted-foreground">Commission</div>
                  <div className="font-serif text-lg font-bold tabular-nums" style={{ color: "var(--ok)" }}>{fmtGBP(b.commission)}</div>
                </div>
              </summary>
              <table className="w-full border-t border-border/70 text-sm">
                <caption className="sr-only">{b.rep.name}&apos;s commission by edition</caption>
                <thead>
                  <tr className="bg-muted/30 text-xs text-muted-foreground">
                    <SortableTh sortKey="edition" className="pl-12">Edition</SortableTh>
                    <SortableTh sortKey="date">Date</SortableTh>
                    <SortableTh sortKey="orders" align="right" firstDir="desc">Bookings</SortableTh>
                    <SortableTh sortKey="credit" align="right" firstDir="desc">Credited</SortableTh>
                    <SortableTh sortKey="commission" align="right" firstDir="desc" className="pr-4">Commission</SortableTh>
                  </tr>
                </thead>
                <tbody>
                  {b.editions.map((e) => (
                    <tr key={e.edition.id} className="border-t border-border/50">
                      <td className="px-4 py-2 pl-12">
                        <Link href={`/sales/editions/${e.edition.id}`} className="font-medium text-foreground hover:text-primary hover:underline">
                          {e.edition.label}
                        </Link>
                      </td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">{fmtDate(e.edition_date)}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{e.orders}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{fmtGBP(e.credit_gbp)}</td>
                      <td className="px-4 py-2 text-right font-semibold tabular-nums">{fmtGBP(e.commission_gbp)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          ))}
        </section>
      )}
    </DataViewLayout>
  );
}
