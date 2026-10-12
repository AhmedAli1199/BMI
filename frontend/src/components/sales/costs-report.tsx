"use client";

import Link from "next/link";
import { useMemo } from "react";
import { Wallet } from "lucide-react";
import type { CostReport, CostReportRow, SalesTitle } from "@/lib/sales-types";
import type { FilterDef, SortState } from "@/lib/data-view/schema";
import type { Accessors, SortAccessors } from "@/lib/data-view/client-engine";
import { PRODUCT_LINE_OPTIONS } from "@/lib/sales-filters";
import { ClientDataView } from "@/components/data-view/client-data-view";
import { DataViewLayout } from "@/components/data-view/data-view";
import { FilterSidebar } from "@/components/data-view/filter-sidebar";
import { DataSearch, FilterChips, SortableTh } from "@/components/data-view/toolbar";
import { EmptyState, TitleIcon, fmtDate, fmtGBP } from "@/components/sales/sales-ui";

const DEFAULT_SORT: SortState = { key: "date", dir: "asc" };
const result = (r: CostReportRow) => (r.profit_gbp === null ? "none" : r.profit_gbp < 0 ? "loss" : "profit");

const ACCESSORS: Accessors<CostReportRow> = {
  q: (r) => [r.edition.label, r.title.name],
  title: (r) => r.title.id,
  line: (r) => r.title.product_line,
  result,
  budget: (r) => (r.budget_gbp === null ? "none" : r.costs_gbp > r.budget_gbp ? "over" : "within"),
  signed: (r) => r.signed_off,
  date: (r) => r.edition_date,
};

const SORTS: SortAccessors<CostReportRow> = {
  edition: (r) => r.edition.label,
  date: (r) => r.edition_date,
  booked: (r) => r.booked_gbp,
  costs: (r) => r.costs_gbp,
  budget: (r) => r.budget_gbp,
  profit: (r) => r.profit_gbp,
  margin: (r) => r.margin,
};

function defs(titles: SalesTitle[]): FilterDef[] {
  return [
    { kind: "search", key: "q", label: "Search", placeholder: "Edition or title…" },
    { kind: "multi", key: "title", label: "Title", section: "What", searchable: true, options: titles.map((t) => ({ value: t.id, label: t.name.replace(/\s*\(.*\)/, "") })) },
    { kind: "multi", key: "line", label: "Type", section: "What", options: PRODUCT_LINE_OPTIONS },
    {
      kind: "multi", key: "result", label: "Result", section: "Money",
      options: [
        { value: "profit", label: "Made a profit" },
        { value: "loss", label: "Made a loss" },
        { value: "none", label: "No costs recorded" },
      ],
    },
    {
      kind: "multi", key: "budget", label: "Against budget", section: "Money",
      options: [
        { value: "over", label: "Over budget" },
        { value: "within", label: "Within budget" },
        { value: "none", label: "No budget set" },
      ],
    },
    { kind: "tristate", key: "signed", label: "Signed off for commission", section: "Money", yes: "Signed off", no: "Not signed off" },
    { kind: "dates", key: "date", label: "Edition / event date", section: "Money" },
  ];
}

/** Every edition's costs and profit for the year, with filters - the manager's view across issues, events and awards. */
export function CostsReport({ report, titles }: { report: CostReport; titles: SalesTitle[] }) {
  const d = useMemo(() => defs(titles.filter((t) => report.rows.some((r) => r.title.id === t.id))), [titles, report.rows]);
  return (
    <ClientDataView rows={report.rows} defs={d} defaultSort={DEFAULT_SORT} accessors={ACCESSORS} sortAccessors={SORTS}>
      {(rows) => <Body rows={rows} report={report} />}
    </ClientDataView>
  );
}

function Body({ rows, report }: { rows: CostReportRow[]; report: CostReport }) {
  const withCosts = rows.filter((r) => r.cost_lines);
  const booked = withCosts.reduce((s, r) => s + r.booked_gbp, 0);
  const costs = withCosts.reduce((s, r) => s + r.costs_gbp, 0);
  return (
    <DataViewLayout sidebar={<FilterSidebar title="Filter editions" />}>
      <DataSearch />
      <FilterChips />
      <p className="text-xs text-muted-foreground" aria-live="polite">
        <span className="font-semibold text-foreground tabular-nums">{rows.length}</span> of {report.rows.length} editions ·{" "}
        <span className="font-semibold text-foreground tabular-nums">{fmtGBP(booked)}</span> sold,{" "}
        <span className="font-semibold text-foreground tabular-nums">{fmtGBP(costs)}</span> costs,{" "}
        <span className="font-semibold tabular-nums" style={{ color: booked - costs >= 0 ? "var(--ok)" : "var(--bad)" }}>{fmtGBP(booked - costs)}</span> profit
        {withCosts.length < rows.length && " (editions with costs only)"}
      </p>
      {rows.length === 0 ? (
        <EmptyState icon={Wallet} title={report.rows.length ? "No editions match these filters" : `No costs recorded for ${report.label} yet`}>
          {report.rows.length ? "Try removing a filter." : "Open an issue, event or awards and add its costs under “Costs & profit”."}
        </EmptyState>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
          <table className="w-full min-w-[820px] text-sm">
            <caption className="sr-only">Costs and profit by edition, {report.label}</caption>
            <thead>
              <tr className="border-b border-border/70 text-xs text-muted-foreground">
                <SortableTh sortKey="edition" className="pl-4">Edition</SortableTh>
                <SortableTh sortKey="date">Date</SortableTh>
                <SortableTh sortKey="booked" align="right" firstDir="desc">Sold</SortableTh>
                <SortableTh sortKey="budget" align="right" firstDir="desc">Budget</SortableTh>
                <SortableTh sortKey="costs" align="right" firstDir="desc">Costs</SortableTh>
                <SortableTh sortKey="profit" align="right" firstDir="desc">Profit</SortableTh>
                <SortableTh sortKey="margin" align="right" firstDir="desc" className="pr-4">Margin</SortableTh>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const over = r.budget_gbp !== null && r.costs_gbp > r.budget_gbp;
                return (
                  <tr key={r.edition.id} className="relative border-b border-border/60 last:border-0 hover:bg-accent/40">
                    <td className="px-4 py-2.5">
                      <Link href={`/sales/editions/${r.edition.id}`} className="flex items-center gap-1.5 font-semibold text-foreground after:absolute after:inset-0">
                        <span className="text-muted-foreground"><TitleIcon line={r.title.product_line} /></span>
                        {r.edition.label}
                      </Link>
                      <div className="pl-5 text-[11px] text-muted-foreground">
                        {r.cost_lines ? `${r.cost_lines} cost line${r.cost_lines === 1 ? "" : "s"}` : "No costs recorded"}
                        {r.top_category && ` · mostly ${report.categories[r.top_category]?.toLowerCase() ?? r.top_category}`}
                        {r.signed_off && " · signed off"}
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-xs whitespace-nowrap">{r.edition_date ? fmtDate(r.edition_date) : "No date"}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{fmtGBP(r.booked_gbp)}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-muted-foreground">{r.budget_gbp !== null ? fmtGBP(r.budget_gbp) : "—"}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums" style={over ? { color: "var(--warn)" } : undefined} title={over ? "Over budget" : undefined}>
                      {r.cost_lines ? fmtGBP(r.costs_gbp) : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-right font-semibold tabular-nums" style={r.profit_gbp !== null ? { color: r.profit_gbp >= 0 ? "var(--ok)" : "var(--bad)" } : undefined}>
                      {r.profit_gbp !== null ? fmtGBP(r.profit_gbp) : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{r.margin !== null ? `${Math.round(r.margin * 100)}%` : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </DataViewLayout>
  );
}
