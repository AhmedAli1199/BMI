import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import { canUseAutomations } from "@/lib/access";
import type { SalesMeta } from "@/lib/sales-types";
import { OrdersExplorer } from "@/components/sales/orders-explorer";
import { SalesHeader } from "@/components/sales/sales-ui";

export default async function BookingsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const [sp, meta, session] = await Promise.all([searchParams, backendFetch<SalesMeta>("/api/sales/meta"), getSession()]);

  return (
    <div className="mx-auto flex w-full max-w-[90rem] flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="All bookings"
        crumbs={[{ label: "Sales Orders", href: "/sales" }]}
        description="Every booking across every title and year. Narrow it down with the filters, sort by any column, and export exactly what you see."
      />
      <OrdersExplorer searchParams={sp} meta={meta} canDelete={canUseAutomations(session)} year={new Date().getFullYear()} />
    </div>
  );
}
