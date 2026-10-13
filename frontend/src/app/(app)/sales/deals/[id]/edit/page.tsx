import { notFound } from "next/navigation";
import { backendFetch } from "@/lib/backend";
import type { Deal, DealInput } from "@/lib/deals-types";
import { DealForm } from "@/components/deals/deal-form";
import { SalesHeader } from "@/components/sales/sales-ui";
import { EMPTY_DEAL, formData } from "../../_data";

export default async function EditDealPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let d: Deal;
  try {
    d = await backendFetch<Deal>(`/api/sales/deals/${id}`);
  } catch {
    notFound();
  }
  const { meta, rates } = await formData();
  const asking = !!d.locked && !d.can_approve;
  const initial: DealInput = Object.fromEntries(Object.keys(EMPTY_DEAL).map((k) => [k, (d as unknown as Record<string, unknown>)[k] ?? (EMPTY_DEAL as unknown as Record<string, unknown>)[k]])) as unknown as DealInput;
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title={asking ? `Request a change to booking ${d.number}` : `Change booking ${d.number}`}
        crumbs={[{ label: "Sales Orders", href: "/sales" }, { label: "Bookings", href: "/sales/deals" }, { label: `Booking ${d.number}`, href: `/sales/deals/${d.id}` }]}
        description={asking
          ? "Accounts has checked this booking. Make the change below and say why - it goes to accounts, and the booking changes once they approve it."
          : "Changes go straight to the items. An item that's already invoiced and is taken off is marked cancelled, not deleted."}
      />
      <DealForm dealId={d.id} initial={initial} titles={meta.titles} reps={meta.reps} rates={rates}
        company={d.company_id ? { id: d.company_id, label: d.client_name } : null}
        contact={d.contact_id ? { id: d.contact_id, label: d.contact_name ?? "Contact" } : null} myRepId={meta.my_rep_id} requestChange={asking} />
    </div>
  );
}
