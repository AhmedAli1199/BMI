import Link from "next/link";
import { Search } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import { canUseAutomations } from "@/lib/access";
import type { OrdersPage, SalesMeta } from "@/lib/sales-types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { OrdersTable } from "@/components/sales/orders-table";
import { SalesHeader, fmtGBP } from "@/components/sales/sales-ui";

const PAGE = 100;
const selectCls = "h-8 rounded-lg border border-input bg-card px-2.5 text-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

export default async function BookingsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; year?: string; title?: string; rep?: string; status?: string; page?: string }>;
}) {
  const sp = await searchParams;
  const [meta, session] = await Promise.all([backendFetch<SalesMeta>("/api/sales/meta"), getSession()]);
  const page = Math.max(1, Number(sp.page) || 1);
  const year = sp.year === "all" ? "" : sp.year || String(new Date().getFullYear());
  const qs = new URLSearchParams({ limit: String(PAGE), offset: String((page - 1) * PAGE) });
  if (sp.q) qs.set("search", sp.q);
  if (year) qs.set("year", year);
  if (sp.title) qs.set("title_id", sp.title);
  if (sp.rep) qs.set("rep_id", sp.rep);
  if (sp.status) qs.set("status", sp.status);
  const data = await backendFetch<OrdersPage>(`/api/sales/orders?${qs}`);
  const pages = Math.ceil(data.total / PAGE);
  const pageHref = (p: number) => {
    const n = new URLSearchParams(Object.entries(sp).filter(([, v]) => v) as [string, string][]);
    n.set("page", String(p));
    return `/sales/bookings?${n}`;
  };

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="All bookings"
        crumbs={[{ label: "Sales Orders", href: "/sales" }]}
        description="Search every booking across every title - by client, invoice number, salesperson or year."
      />

      <form method="get" action="/sales/bookings" className="flex flex-wrap items-center gap-2 rounded-xl border border-border/80 bg-card p-3 shadow-2xs" role="search">
        <div className="relative min-w-56 flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input name="q" defaultValue={sp.q ?? ""} placeholder="Client or invoice number…" aria-label="Search client or invoice number" className="h-8 pl-8 text-xs" />
        </div>
        <select name="year" defaultValue={sp.year ?? String(new Date().getFullYear())} aria-label="Year" className={selectCls}>
          <option value="all">All years</option>
          {meta.years.map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
        <select name="title" defaultValue={sp.title ?? ""} aria-label="Title" className={selectCls}>
          <option value="">All titles</option>
          {meta.titles.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
        <select name="rep" defaultValue={sp.rep ?? ""} aria-label="Salesperson" className={selectCls}>
          <option value="">Everyone</option>
          {meta.reps.map((r) => (
            <option key={r.id} value={r.id}>{r.name}{r.active ? "" : " (former)"}</option>
          ))}
        </select>
        <select name="status" defaultValue={sp.status ?? ""} aria-label="Status" className={selectCls}>
          <option value="">Any status</option>
          <option value="booked">Booked</option>
          <option value="cancelled">Cancelled</option>
          <option value="contra">Contra</option>
          <option value="moved">Moved</option>
        </select>
        <Button type="submit" size="sm">Search</Button>
        {(sp.q || sp.title || sp.rep || sp.status || sp.year) && (
          <Link href="/sales/bookings" className="text-xs font-semibold text-muted-foreground hover:text-foreground">Clear</Link>
        )}
      </form>

      <div className="-mb-3 flex items-center justify-between text-xs text-muted-foreground">
        <span>
          <span className="font-semibold text-foreground">{data.total.toLocaleString("en-GB")}</span> bookings ·{" "}
          <span className="font-semibold text-foreground tabular-nums">{fmtGBP(data.total_value_gbp)}</span> total value
        </span>
        {pages > 1 && <span>Page {page} of {pages}</span>}
      </div>

      <OrdersTable
        orders={data.items}
        reps={meta.reps}
        canDelete={canUseAutomations(session)}
        year={Number(year) || new Date().getFullYear()}
        showEdition
        showFilters={false}
        emptyText="No bookings match these filters."
      />

      {pages > 1 && (
        <nav aria-label="Pages" className="flex items-center justify-center gap-2">
          {page > 1 && <Button size="sm" variant="outline" nativeButton={false} render={<Link href={pageHref(page - 1)} />}>Previous</Button>}
          {page < pages && <Button size="sm" variant="outline" nativeButton={false} render={<Link href={pageHref(page + 1)} />}>Next 100</Button>}
        </nav>
      )}
    </div>
  );
}
