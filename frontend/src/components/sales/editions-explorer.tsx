"use client";

import Link from "next/link";
import { useMemo } from "react";
import { AlertTriangle, Layers, Lock } from "lucide-react";
import type { EditionSummary, SalesTitle } from "@/lib/sales-types";
import type { FilterDef, SortState } from "@/lib/data-view/schema";
import type { Accessors, SortAccessors } from "@/lib/data-view/client-engine";
import { fmtPercent, pctChange } from "@/lib/automation-format";
import { PRODUCT_LINE_OPTIONS } from "@/lib/sales-filters";
import { Delta } from "@/components/automations/hub-ui";
import { ClientDataView } from "@/components/data-view/client-data-view";
import { DataViewLayout, useDataView } from "@/components/data-view/data-view";
import { FilterSidebar } from "@/components/data-view/filter-sidebar";
import { DataSearch, FilterChips, SortableTh } from "@/components/data-view/toolbar";
import { EmptyState, TitleIcon, fmtDate, fmtGBP } from "@/components/sales/sales-ui";

const DEFAULT_SORT: SortState = { key: "date", dir: "asc" };

/** vs the same editions last year at the same point - null when there's nothing to compare. */
const change = (e: EditionSummary) => pctChange(e.booked_gbp, e.previous_same_point_gbp);

const ACCESSORS: Accessors<EditionSummary> = {
  q: (e) => [e.label, e.name, e.period_label, e.title.name],
  title: (e) => e.title.id,
  line: (e) => e.title.product_line,
  status: (e) => e.status,
  to_invoice: (e) => e.uninvoiced > 0,
  check: (e) => e.warnings > 0,
  trend: (e) => {
    const c = change(e);
    return c === null ? "none" : c >= 0 ? "ahead" : "behind";
  },
  booked: (e) => e.booked_gbp,
  date: (e) => e.edition_date,
};

const SORTS: SortAccessors<EditionSummary> = {
  edition: (e) => e.label,
  title: (e) => e.title.name,
  date: (e) => e.edition_date,
  orders: (e) => e.orders,
  booked: (e) => e.booked_gbp,
  change: (e) => change(e),
  invoiced: (e) => (e.booked_gbp ? e.invoiced_gbp / e.booked_gbp : null),
  to_invoice: (e) => e.uninvoiced,
};

function editionDefs(titles: SalesTitle[]): FilterDef[] {
  return [
    { kind: "search", key: "q", label: "Search editions", placeholder: "Edition, issue name or title…" },
    { kind: "multi", key: "title", label: "Title", section: "What", searchable: true, options: titles.map((t) => ({ value: t.id, label: t.name.replace(/\s*\(.*\)/, "") })) },
    { kind: "multi", key: "line", label: "Type", section: "What", options: PRODUCT_LINE_OPTIONS },
    {
      kind: "multi", key: "status", label: "Status", section: "State",
      options: [
        { value: "open", label: "Open", hint: "Still taking bookings" },
        { value: "closed", label: "Closed", hint: "No longer taking bookings" },
      ],
    },
    { kind: "tristate", key: "to_invoice", label: "Invoicing", section: "State", yes: "Has bookings to invoice", no: "All invoiced" },
    { kind: "tristate", key: "check", label: "Import check", section: "State", yes: "Has rows to check", no: "No issues" },
    {
      kind: "multi", key: "trend", label: "vs last year", section: "Performance",
      hint: "Compared with the equivalent edition last year at the same point in its sales.",
      options: [
        { value: "ahead", label: "Level or ahead" },
        { value: "behind", label: "Behind" },
        { value: "none", label: "Nothing to compare" },
      ],
    },
    { kind: "range", key: "booked", label: "Booked value", section: "Performance", prefix: "£", step: 1000 },
    { kind: "dates", key: "date", label: "Edition / event date", section: "Performance" },
  ];
}

export function EditionsExplorer({ editions, titles, year }: { editions: EditionSummary[]; titles: SalesTitle[]; year: number }) {
  const defs = useMemo(() => editionDefs(titles), [titles]);
  return (
    <ClientDataView rows={editions} defs={defs} defaultSort={DEFAULT_SORT} accessors={ACCESSORS} sortAccessors={SORTS}>
      {(rows) => <EditionsBody rows={rows} all={editions} titles={titles} year={year} />}
    </ClientDataView>
  );
}

function EditionsBody({ rows, all, titles, year }: { rows: EditionSummary[]; all: EditionSummary[]; titles: SalesTitle[]; year: number }) {
  const { params, update } = useDataView();
  const grouped = params.get("group") !== "none";
  const groups = grouped
    ? titles.map((t) => ({ title: t, rows: rows.filter((e) => e.title.id === t.id) })).filter((g) => g.rows.length)
    : [{ title: null, rows }];
  const booked = rows.reduce((s, e) => s + e.booked_gbp, 0);

  return (
    <DataViewLayout sidebar={<FilterSidebar title="Filter editions" />}>
      <div className="flex flex-wrap items-center gap-2">
        <DataSearch />
        <div role="group" aria-label="Layout" className="flex rounded-lg border border-border bg-card p-0.5 text-xs font-semibold">
          {[
            { v: undefined, label: "By title" },
            { v: "none", label: "One list" },
          ].map((o) => {
            const on = (o.v === "none") !== grouped;
            return (
              <button
                key={o.label}
                type="button"
                aria-pressed={on}
                onClick={() => update({ group: o.v })}
                className={`rounded-md px-2.5 py-1.5 transition-colors ${on ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}
              >
                {o.label}
              </button>
            );
          })}
        </div>
      </div>
      <FilterChips />
      <p className="text-xs text-muted-foreground" aria-live="polite">
        <span className="font-semibold text-foreground tabular-nums">{rows.length}</span> of {all.length} editions in {year} ·{" "}
        <span className="font-semibold text-foreground tabular-nums">{fmtGBP(booked)}</span> booked
      </p>

      {rows.length === 0 ? (
        <EmptyState icon={Layers} title={all.length ? "No editions match these filters" : `No editions in ${year} yet`}>
          {all.length ? "Try removing a filter." : "Create one with “New edition” - it takes the place of copying the template sheet in the old workbook."}
        </EmptyState>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
          <table className="w-full min-w-[860px] text-sm">
            <caption className="sr-only">Editions in {year}</caption>
            <thead>
              <tr className="border-b border-border/70 text-xs text-muted-foreground">
                <SortableTh sortKey="edition" className="pl-4">Edition</SortableTh>
                {!grouped && <SortableTh sortKey="title">Title</SortableTh>}
                <SortableTh sortKey="date">Date</SortableTh>
                <SortableTh sortKey="orders" align="right" firstDir="desc">Bookings</SortableTh>
                <SortableTh sortKey="booked" align="right" firstDir="desc">Booked</SortableTh>
                <SortableTh sortKey="change" firstDir="desc">vs last year</SortableTh>
                <SortableTh sortKey="invoiced" align="right" firstDir="desc">Invoiced</SortableTh>
                <SortableTh sortKey="to_invoice" firstDir="desc" className="pr-4">
                  <span className="sr-only">Flags - </span>To do
                </SortableTh>
              </tr>
            </thead>
            {groups.map((g) => (
              <tbody key={g.title?.id ?? "all"}>
                {g.title && (
                  <tr className="border-b border-border/70 bg-muted/40">
                    <th scope="rowgroup" colSpan={7} className="px-4 py-2 text-left">
                      <span className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                        <span className="flex items-center gap-1.5 text-sm font-bold text-foreground">
                          <span className="text-muted-foreground"><TitleIcon line={g.title.product_line} /></span>
                          {g.title.name}
                        </span>
                        <span className="font-normal text-muted-foreground">
                          {g.rows.length} edition{g.rows.length === 1 ? "" : "s"} ·{" "}
                          <span className="font-semibold text-foreground tabular-nums">{fmtGBP(g.rows.reduce((s, e) => s + e.booked_gbp, 0))}</span> booked
                        </span>
                        <TrendForGroup rows={g.rows} />
                      </span>
                    </th>
                  </tr>
                )}
                {g.rows.map((e) => (
                  <EditionRow key={e.id} e={e} showTitle={!grouped} />
                ))}
              </tbody>
            ))}
          </table>
        </div>
      )}
    </DataViewLayout>
  );
}

function TrendForGroup({ rows }: { rows: EditionSummary[] }) {
  const total = rows.reduce((s, e) => s + e.booked_gbp, 0);
  const prev = rows.reduce((s, e) => s + (e.previous_same_point_gbp ?? 0), 0);
  if (!prev) return null;
  return (
    <span className="font-normal" title="vs the same editions last year, at the same point">
      <Delta change={pctChange(total, prev)} goodWhenUp />
    </span>
  );
}

function EditionRow({ e, showTitle }: { e: EditionSummary; showTitle: boolean }) {
  const cmp = e.previous_same_point_gbp;
  return (
    <tr className="relative border-b border-border/60 last:border-0 hover:bg-accent/40">
      <td className="px-4 py-2.5">
        <Link href={`/sales/editions/${e.id}`} className="font-semibold text-foreground after:absolute after:inset-0">
          {e.label}
        </Link>
        {e.period_label && e.period_label !== e.name && <div className="max-w-xs truncate text-[11px] text-muted-foreground">{e.period_label}</div>}
      </td>
      {showTitle && (
        <td className="px-3 py-2.5 text-xs">
          <span className="flex items-center gap-1.5">
            <span className="text-muted-foreground"><TitleIcon line={e.title.product_line} className="size-3.5" /></span>
            {e.title.name.replace(/\s*\(.*\)/, "")}
          </span>
        </td>
      )}
      <td className="px-3 py-2.5 text-xs whitespace-nowrap text-muted-foreground">{fmtDate(e.edition_date)}</td>
      <td className="px-3 py-2.5 text-right tabular-nums">{e.orders}</td>
      <td className="px-3 py-2.5 text-right font-semibold tabular-nums">{fmtGBP(e.booked_gbp)}</td>
      <td className="px-3 py-2.5 text-xs">
        {e.previous ? (
          <span className="flex items-center gap-1.5">
            {cmp ? <Delta change={pctChange(e.booked_gbp, cmp)} goodWhenUp /> : <span className="text-muted-foreground">—</span>}
            <span className="text-muted-foreground">{fmtGBP(e.previous_booked_gbp, { compact: true })} final</span>
          </span>
        ) : (
          <span className="text-muted-foreground">No match</span>
        )}
      </td>
      <td className="px-3 py-2.5 text-right text-xs tabular-nums">{fmtPercent(e.booked_gbp ? e.invoiced_gbp / e.booked_gbp : null)}</td>
      <td className="px-4 py-2.5">
        <div className="flex items-center justify-end gap-2 text-[11px]">
          {e.uninvoiced > 0 && (
            <span className="rounded-full px-1.5 py-0.5 font-semibold whitespace-nowrap" style={{ color: "var(--warn)", background: "color-mix(in oklab, var(--warn) 12%, transparent)" }}>
              {e.uninvoiced} to invoice
            </span>
          )}
          {e.warnings > 0 && (
            <span className="flex items-center gap-0.5" style={{ color: "var(--warn)" }} title={`${e.warnings} imported row(s) need a check`}>
              <AlertTriangle className="size-3.5" aria-hidden="true" />
              <span className="sr-only">{e.warnings} rows need a check</span>
            </span>
          )}
          {e.status === "closed" && (
            <span className="flex items-center gap-0.5 text-muted-foreground" title="Closed - no longer taking bookings">
              <Lock className="size-3" aria-hidden="true" /> Closed
            </span>
          )}
        </div>
      </td>
    </tr>
  );
}
