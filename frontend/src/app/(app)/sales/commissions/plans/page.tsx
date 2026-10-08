import { notFound } from "next/navigation";
import { backendFetch } from "@/lib/backend";
import type { CommissionPlans } from "@/lib/commission-types";
import { SalesHeader } from "@/components/sales/sales-ui";
import { PlansView } from "@/components/commission/plans-view";
import { LoadStructureButton } from "@/components/commission/commission-ui";

export default async function CommissionPlansPage() {
  const data = await backendFetch<CommissionPlans>("/api/commission/plans").catch(() => null);
  if (!data) notFound();
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="Commission plans"
        crumbs={[{ label: "Sales Orders", href: "/sales" }, { label: "Commissions", href: "/sales/commissions" }]}
        description="What each salesperson earns on each product: a rate on their own revenue, an extra rate on new business, and any bonuses. Changes apply to every month that isn't approved yet."
        actions={data.can_edit ? (data.seed_available ? <LoadStructureButton /> : <LoadStructureButton replace label="Reload BMI's structure" />) : undefined}
      />
      <PlansView data={data} />
    </div>
  );
}
