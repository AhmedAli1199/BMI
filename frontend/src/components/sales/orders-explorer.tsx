import { backendFetch } from "@/lib/backend";
import type { OrdersPage, SalesMeta } from "@/lib/sales-types";
import { parseFilters, parseSort } from "@/lib/data-view/schema";
import { ORDER_DEFAULT_SORT, type OrderFilterKey, orderBackendQuery, orderFacetsForSidebar, orderFilterDefs } from "@/lib/sales-filters";
import { DataView, DataViewLayout } from "@/components/data-view/data-view";
import { FilterSidebar } from "@/components/data-view/filter-sidebar";
import { DataSearch, ExportButton, FilterChips, Pagination } from "@/components/data-view/toolbar";
import { OrdersTable } from "@/components/sales/orders-table";
import { fmtGBP } from "@/components/sales/sales-ui";

const SIZES = [50, 100, 250];

/** A searchable, filterable, sortable, paged bookings list with a filter
 * sidebar - the same experience on All bookings, every Invoicing view and
 * an edition's own page. `scope` pins backend filters the page is about
 * (one edition, one invoicing view); `hide` drops sidebar filters that
 * make no sense there. Filtering happens in the database, so it works the
 * same on 30 bookings or 30,000. */
export async function OrdersExplorer({
  searchParams,
  meta,
  canDelete,
  scope = {},
  hide = [],
  year,
  showEdition = true,
  emptyText = "No bookings match these filters.",
  actions,
}: {
  searchParams: Record<string, string | string[] | undefined>;
  meta: SalesMeta;
  canDelete: boolean;
  scope?: Record<string, string>;
  hide?: OrderFilterKey[];
  year: number;
  showEdition?: boolean;
  emptyText?: string;
  actions?: React.ReactNode;
}) {
  const defs = orderFilterDefs(meta, hide);
  const values = parseFilters(defs, searchParams);
  const sort = parseSort(searchParams, ORDER_DEFAULT_SORT);
  const sizeParam = Number(Array.isArray(searchParams.size) ? searchParams.size[0] : searchParams.size);
  const size = SIZES.includes(sizeParam) ? sizeParam : 100;
  const page = Math.max(1, Number(Array.isArray(searchParams.page) ? searchParams.page[0] : searchParams.page) || 1);

  const query = orderBackendQuery(values, sort, scope);
  const listQs = new URLSearchParams(query);
  listQs.set("limit", String(size));
  listQs.set("offset", String((page - 1) * size));
  const [data, facets] = await Promise.all([
    backendFetch<OrdersPage>(`/api/sales/orders?${listQs}`),
    backendFetch<Record<string, Record<string, number>>>(`/api/sales/orders/facets?${query}`).catch(() => ({})),
  ]);

  return (
    <DataView defs={defs} defaultSort={ORDER_DEFAULT_SORT} facets={orderFacetsForSidebar(facets)}>
      <DataViewLayout sidebar={<FilterSidebar title="Filter bookings" />}>
        <div className="flex flex-wrap items-center gap-2">
          <DataSearch />
          <ExportButton href={`/api/files/sales/orders/export?${query}`} />
          {actions}
        </div>
        <FilterChips />
        <p className="text-xs text-muted-foreground" aria-live="polite">
          <span className="font-semibold text-foreground tabular-nums">{data.total.toLocaleString("en-GB")}</span>{" "}
          {data.total === 1 ? "booking" : "bookings"} ·{" "}
          <span className="font-semibold text-foreground tabular-nums">{fmtGBP(data.total_value_gbp)}</span> total value
        </p>
        <OrdersTable orders={data.items} reps={meta.reps} canDelete={canDelete} year={year} showEdition={showEdition} sortable emptyText={emptyText} />
        <Pagination total={data.total} pageSize={size} sizes={SIZES} />
      </DataViewLayout>
    </DataView>
  );
}
