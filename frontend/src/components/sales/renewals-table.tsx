"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Building2, Plus, Search } from "lucide-react";
import type { EditionSummary, Renewals, SalesRep } from "@/lib/sales-types";
import type { FilterDef, SortState } from "@/lib/data-view/schema";
import type { Accessors, SortAccessors } from "@/lib/data-view/client-engine";
import { ClientDataView } from "@/components/data-view/client-data-view";
import { DataViewLayout } from "@/components/data-view/data-view";
import { FilterSidebar } from "@/components/data-view/filter-sidebar";
import { DataSearch, FilterChips, SortableTh } from "@/components/data-view/toolbar";
import { EmptyState } from "@/components/sales/sales-ui";
import { Button } from "@/components/ui/button";
import { OrderSheet, type OrderSheetTarget } from "@/components/sales/order-sheet";
import { InfoHint } from "@/components/sales/info-hint";
import { fmtDate, fmtGBP } from "@/components/sales/sales-ui";

type Row = Renewals["items"][number];

const DEFAULT_SORT: SortState = { key: "spent", dir: "desc" };

const ACCESSORS: Accessors<Row> = {
  q: (r) => [r.client_name, r.company?.label, r.rep?.name, r.rep?.code, r.size, r.last_edition.label],
  rep: (r) => r.rep?.id ?? "none",
  size: (r) => r.size ?? "none",
  linked: (r) => !!r.company,
  repeat: (r) => r.last_year_orders > 1,
  spent: (r) => r.last_year_value_gbp,
  last: (r) => r.last_booked_on,
};

const SORTS: SortAccessors<Row> = {
  client: (r) => r.client_name,
  last: (r) => r.last_booked_on,
  spent: (r) => r.last_year_value_gbp,
  rep: (r) => r.rep?.name,
};

/** Last year's advertisers who haven't rebooked - filter by salesperson,
 * spend, size or when they last booked, and book any of them in a click. */
export function RenewalsTable({ data, editions, reps }: { data: Renewals; editions: EditionSummary[]; reps: SalesRep[] }) {
  const defs = useMemo<FilterDef[]>(() => {
    const repsSeen = new Map<string, string>();
    const sizes = new Set<string>();
    for (const r of data.items) {
      repsSeen.set(r.rep?.id ?? "none", r.rep ? r.rep.name : "No salesperson");
      sizes.add(r.size ?? "none");
    }
    return [
      { kind: "search", key: "q", label: "Search advertisers", placeholder: "Advertiser, company, salesperson, size…" },
      { kind: "multi", key: "rep", label: "Salesperson", section: "Who", searchable: true, options: [...repsSeen].map(([value, label]) => ({ value, label })) },
      { kind: "tristate", key: "linked", label: "CRM company", section: "Who", yes: "Linked", no: "Not linked" },
      { kind: "range", key: "spent", label: "Spent last year", section: "Value", prefix: "£", step: 500 },
      { kind: "tristate", key: "repeat", label: "Frequency", section: "Value", yes: "Booked more than once", no: "Booked once" },
      {
        kind: "multi", key: "size", label: "Last size booked", section: "Value", searchable: true,
        options: [...sizes].sort().map((v) => ({ value: v, label: v === "none" ? "Not recorded" : v })),
      },
      { kind: "dates", key: "last", label: "Last booked on", section: "When" },
    ];
  }, [data.items]);

  return (
    <ClientDataView rows={data.items} defs={defs} defaultSort={DEFAULT_SORT} accessors={ACCESSORS} sortAccessors={SORTS}>
      {(rows) => <RenewalsBody rows={rows} data={data} editions={editions} reps={reps} />}
    </ClientDataView>
  );
}

function RenewalsBody({ rows, data, editions, reps }: { rows: Row[]; data: Renewals; editions: EditionSummary[]; reps: SalesRep[] }) {
  const today = new Date().toISOString().slice(0, 10);
  const open = editions.filter((e) => e.status === "open");
  const defaultEd = open.find((e) => (e.edition_date ?? "") >= today) ?? open[0] ?? editions[0];
  const [editionId, setEditionId] = useState(defaultEd?.id ?? "");
  const [target, setTarget] = useState<OrderSheetTarget | null>(null);
  const chosen = editions.find((e) => e.id === editionId);

  return (
    <DataViewLayout sidebar={<FilterSidebar title="Filter advertisers" />}>
      <div className="flex flex-wrap items-center gap-2">
        <DataSearch />
        {editions.length > 0 && (
          <label className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
            Book renewals into
            <select
              value={editionId}
              onChange={(e) => setEditionId(e.target.value)}
              className="h-8 rounded-lg border border-input bg-card px-2.5 text-xs text-foreground outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              {editions.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.label}
                  {e.edition_date ? ` (${fmtDate(e.edition_date, false)})` : ""}
                  {e.status === "closed" ? " - closed" : ""}
                </option>
              ))}
            </select>
            <InfoHint>&ldquo;Book&rdquo; opens a new booking in this edition, pre-filled with the advertiser, their CRM company, salesperson and last year&apos;s size - adjust anything before saving.</InfoHint>
          </label>
        )}
      </div>
      <FilterChips />
      <p className="text-xs text-muted-foreground" aria-live="polite">
        <span className="font-semibold text-foreground tabular-nums">{rows.length}</span> of {data.items.length} advertisers ·{" "}
        <span className="font-semibold text-foreground tabular-nums">{fmtGBP(rows.reduce((t, r) => t + r.last_year_value_gbp, 0))}</span> spent with{" "}
        {data.title.name} last year
      </p>
      {rows.length === 0 ? (
        <EmptyState icon={Search} title="No advertisers match these filters">Try removing a filter.</EmptyState>
      ) : (

      <div className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
        <table className="w-full min-w-[760px] text-sm">
          <caption className="sr-only">Last year&apos;s advertisers who haven&apos;t rebooked this title yet</caption>
          <thead>
            <tr className="border-b border-border/70 text-left text-xs font-semibold text-muted-foreground">
              <SortableTh sortKey="client" className="pl-4">Advertiser</SortableTh>
              <SortableTh sortKey="last" firstDir="desc">Last booking</SortableTh>
              <SortableTh sortKey="spent" align="right" firstDir="desc">Spent last year</SortableTh>
              <SortableTh sortKey="rep">Salesperson</SortableTh>
              <th scope="col" className="px-4 py-2.5 text-right font-semibold"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.client_name} className="border-b border-border/60 last:border-0 hover:bg-accent/30">
                <td className="px-4 py-2.5">
                  <div className="font-semibold text-foreground">{r.client_name}</div>
                  {r.company && (
                    <Link href={`/companies/${r.company.id}`} className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-primary">
                      <Building2 className="size-3" aria-hidden="true" /> {r.company.label}
                    </Link>
                  )}
                </td>
                <td className="px-3 py-2.5 text-xs">
                  <Link href={`/sales/editions/${r.last_edition.id}`} className="font-medium text-foreground hover:text-primary hover:underline">
                    {r.last_edition.label}
                  </Link>
                  <div className="text-[11px] text-muted-foreground">
                    {r.size ?? "—"} · {fmtGBP(r.last_value_gbp)}
                    {r.last_booked_on ? ` · booked ${fmtDate(r.last_booked_on)}` : ""}
                  </div>
                </td>
                <td className="px-3 py-2.5 text-right tabular-nums">
                  <span className="font-semibold">{fmtGBP(r.last_year_value_gbp)}</span>
                  {r.last_year_orders > 1 && <div className="text-[11px] text-muted-foreground">{r.last_year_orders} bookings</div>}
                </td>
                <td className="px-3 py-2.5 text-xs">{r.rep ? r.rep.name : <span className="text-muted-foreground">—</span>}</td>
                <td className="px-4 py-2.5 text-right">
                  <Button
                    size="xs"
                    variant="outline"
                    className="gap-1"
                    disabled={!chosen}
                    aria-label={`Book ${r.client_name} into ${chosen?.label ?? "an edition"}`}
                    onClick={() =>
                      chosen &&
                      setTarget({
                        mode: "create",
                        editionId: chosen.id,
                        titleId: chosen.title.id,
                        year: chosen.year,
                        editionLabel: chosen.label,
                        defaults: {
                          client_name: r.client_name,
                          company: r.company,
                          rep: r.rep,
                          size: r.size,
                          value_gbp: r.last_value_gbp,
                        },
                      })
                    }
                  >
                    <Plus className="size-3" aria-hidden="true" /> Book
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      )}
      <OrderSheet target={target} reps={reps} canDelete={false} onClose={() => setTarget(null)} />
    </DataViewLayout>
  );
}
