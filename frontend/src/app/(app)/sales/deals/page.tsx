import Link from "next/link";
import { ClipboardList, Plus } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { SalesMeta } from "@/lib/sales-types";
import type { DealListItem, DealSettings } from "@/lib/deals-types";
import type { FilterDef, SortState } from "@/lib/data-view/schema";
import { parseFilters, parseSort } from "@/lib/data-view/schema";
import { DataView, DataViewLayout } from "@/components/data-view/data-view";
import { FilterSidebar } from "@/components/data-view/filter-sidebar";
import { DataSearch, FilterChips, Pagination, SortableTh } from "@/components/data-view/toolbar";
import { Button } from "@/components/ui/button";
import { DealStatusPill } from "@/components/deals/deal-ui";
import { DealSettingsButton } from "@/components/deals/deal-settings";
import { EmptyState, SalesHeader, fmtDate, fmtGBP } from "@/components/sales/sales-ui";

const SIZES = [50, 100, 200];
const DEFAULT_SORT: SortState = { key: "number", dir: "desc" };

type Page = { items: DealListItem[]; total: number; total_value_gbp: number };

export default async function DealsPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const sp = await searchParams;
  const [meta, settings] = await Promise.all([
    backendFetch<SalesMeta>("/api/sales/meta"),
    backendFetch<DealSettings>("/api/sales/deals/settings").catch(() => null),
  ]);
  const year = new Date().getFullYear();
  const defs: FilterDef[] = [
    { kind: "search", key: "q", label: "Search orders", placeholder: "Client, order no., PO, contact, agency…" },
    { kind: "multi", key: "status", label: "Status", section: "Order", options: [
      { value: "pencilled", label: "Pencilled", hint: "Held for the client, not confirmed yet" }, { value: "confirmed", label: "Confirmed" }, { value: "cancelled", label: "Cancelled" }] },
    { kind: "single", key: "mine", label: "Whose", section: "Order", options: [{ value: "1", label: "Only my orders" }] },
    { kind: "multi", key: "rep", label: "Salesperson", section: "Order", options: meta.reps.filter((r) => r.active).map((r) => ({ value: r.id, label: r.name })) },
    { kind: "multi", key: "title", label: "Title", section: "Where it runs", searchable: true, options: meta.titles.map((t) => ({ value: t.id, label: t.name })) },
    { kind: "single", key: "year", label: "Ordered in", section: "When", options: [year + 1, year, year - 1, year - 2].map((y) => ({ value: String(y), label: String(y) })) },
  ];
  const values = parseFilters(defs, sp);
  const sort = parseSort(sp, DEFAULT_SORT);
  const sizeParam = Number(Array.isArray(sp.size) ? sp.size[0] : sp.size);
  const size = SIZES.includes(sizeParam) ? sizeParam : 50;
  const page = Math.max(1, Number(Array.isArray(sp.page) ? sp.page[0] : sp.page) || 1);
  const qs = new URLSearchParams({ sort: sort.key, desc: String(sort.dir === "desc"), limit: String(size), offset: String((page - 1) * size) });
  const list = (v: unknown) => (Array.isArray(v) ? v : v ? [String(v)] : []);
  if (typeof values.q === "string") qs.set("q", values.q);
  list(values.status).forEach((v) => qs.append("status", v));
  list(values.rep).forEach((v) => qs.append("rep_id", v));
  list(values.title).forEach((v) => qs.append("title_id", v));
  if (values.year) qs.set("year", String(values.year));
  if (values.mine) qs.set("mine", "true");
  const data = await backendFetch<Page>(`/api/sales/deals?${qs}`).catch(() => ({ items: [], total: 0, total_value_gbp: 0 }));

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="Orders"
        crumbs={[{ label: "Sales Orders", href: "/sales" }]}
        description="Client orders with everything agreed in one place: items across issues, months and events, package prices, discounts and agency commission. Each one prints as BMI's order confirmation or schedule of works."
        actions={<div className="flex items-center gap-2">
          {settings && <DealSettingsButton settings={settings} />}
          <Button size="sm" className="gap-1.5" nativeButton={false} render={<Link href="/sales/deals/new" />}><Plus className="size-3.5" /> New order</Button>
        </div>}
      />
      <DataView defs={defs} defaultSort={DEFAULT_SORT}>
        <DataViewLayout sidebar={<FilterSidebar title="Filter orders" />}>
          <div className="flex flex-wrap items-center gap-2"><DataSearch /></div>
          <FilterChips />
          <p className="text-xs text-muted-foreground" aria-live="polite">
            <span className="font-semibold text-foreground tabular-nums">{data.total.toLocaleString("en-GB")}</span> {data.total === 1 ? "order" : "orders"} ·{" "}
            <span className="font-semibold text-foreground tabular-nums">{fmtGBP(data.total_value_gbp)}</span> not cancelled
          </p>
          {data.items.length === 0 ? (
            <EmptyState icon={ClipboardList} title="No orders here yet">
              Start one with New order, or from a client&apos;s page, an issue, or a proposal they&apos;ve agreed to.
            </EmptyState>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
              <table className="w-full min-w-[46rem] text-sm">
                <caption className="sr-only">Orders</caption>
                <thead>
                  <tr className="border-b border-border/70 text-xs text-muted-foreground">
                    <SortableTh sortKey="number" firstDir="desc">Order</SortableTh>
                    <SortableTh sortKey="client">Client</SortableTh>
                    <th scope="col" className="px-3 py-2.5 text-left font-semibold">Runs</th>
                    <th scope="col" className="px-3 py-2.5 text-left font-semibold">Salesperson</th>
                    <SortableTh sortKey="value" align="right" firstDir="desc">Total</SortableTh>
                    <th scope="col" className="px-3 py-2.5 text-right font-semibold">Invoiced</th>
                    <th scope="col" className="px-3 py-2.5 text-left font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((d) => (
                    <tr key={d.id} className="border-b border-border/60 last:border-0 hover:bg-muted/40">
                      <td className="px-3 py-2 font-semibold tabular-nums"><Link href={`/sales/deals/${d.id}`} className="text-primary hover:underline">{d.number}</Link></td>
                      <td className="px-3 py-2">
                        <Link href={`/sales/deals/${d.id}`} className="font-medium hover:underline">{d.client_name}</Link>
                        <div className="text-[11px] text-muted-foreground">{[d.agency_name ? `via ${d.agency_name}` : null, d.po_number ? `PO ${d.po_number}` : null, `ordered ${fmtDate(d.booked_on)}`].filter(Boolean).join(" · ")}</div>
                      </td>
                      <td className="px-3 py-2 text-xs">{d.items} item{d.items === 1 ? "" : "s"}{d.first && <div className="text-muted-foreground">{fmtDate(d.first)}{d.last && d.last !== d.first ? ` to ${fmtDate(d.last)}` : ""}</div>}</td>
                      <td className="px-3 py-2 text-xs">{d.rep ?? "—"}</td>
                      <td className="px-3 py-2 text-right font-semibold tabular-nums">{fmtGBP(d.total_gbp)}</td>
                      <td className="px-3 py-2 text-right text-xs tabular-nums">{d.invoiced_gbp ? fmtGBP(d.invoiced_gbp) : "—"}</td>
                      <td className="whitespace-nowrap px-3 py-2">
                        <DealStatusPill status={d.status} />
                        {d.status === "confirmed" && !d.sent_at && <div className="mt-0.5 text-[11px]" style={{ color: "var(--warn)" }}>not sent yet</div>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <Pagination total={data.total} pageSize={size} sizes={SIZES} />
        </DataViewLayout>
      </DataView>
    </div>
  );
}
