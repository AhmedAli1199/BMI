import { UserX } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { Commissions, SalesMeta } from "@/lib/sales-types";
import { CommissionsExplorer } from "@/components/sales/commissions-explorer";
import { EmptyState, SalesHeader, YearSwitch } from "@/components/sales/sales-ui";

export default async function CommissionsPage({ searchParams }: { searchParams: Promise<{ year?: string }> }) {
  const sp = await searchParams;
  const meta = await backendFetch<SalesMeta>("/api/sales/meta");
  const year = Number(sp.year) || new Date().getFullYear();
  const data = await backendFetch<Commissions>(`/api/sales/commissions?year=${year}`);

  return (
    <div className="mx-auto flex w-full max-w-[90rem] flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title={data.scoped_to_me ? "My commission" : "Commissions"}
        crumbs={[{ label: "Sales Orders", href: "/sales" }]}
        description={
          data.scoped_to_me
            ? `Your credited bookings for ${year}'s editions and the commission they earn - what the sheets' per-rep columns used to show.`
            : `Each salesperson's credited bookings for ${year}'s editions and the commission they earn - replacing the per-rep columns on every sheet.`
        }
        actions={<YearSwitch years={meta.years} current={year} href={(y) => `/sales/commissions?year=${y}`} />}
      />

      {data.reps.length === 0 ? (
        data.scoped_to_me ? (
          <EmptyState icon={UserX} title="Your login isn't linked to a salesperson yet">
            Once an administrator links your account to your initials in the order register, your bookings and commission show here.
          </EmptyState>
        ) : (
          <EmptyState icon={UserX} title={`No credited bookings for ${year}`} />
        )
      ) : (
        <CommissionsExplorer data={data} />
      )}
    </div>
  );
}
