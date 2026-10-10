import { backendFetch } from "@/lib/backend";
import type { DealInput, DealPrefill } from "@/lib/deals-types";
import { DealForm } from "@/components/deals/deal-form";
import { SalesHeader } from "@/components/sales/sales-ui";
import { EMPTY_DEAL, formData } from "../_data";

export default async function NewDealPage({ searchParams }: { searchParams: Promise<{ company?: string; contact?: string; proposal?: string; edition?: string; option?: string }> }) {
  const sp = await searchParams;
  const q = new URLSearchParams();
  if (sp.company) q.set("company_id", sp.company);
  if (sp.contact) q.set("contact_id", sp.contact);
  if (sp.proposal) q.set("proposal_id", sp.proposal);
  if (sp.edition) q.set("edition_id", sp.edition);
  if (sp.option) q.set("option", sp.option);
  const [{ meta, rates }, pre] = await Promise.all([formData(), backendFetch<DealPrefill>(`/api/sales/deals/prefill?${q}`).catch(() => ({} as DealPrefill))]);
  const { company, contact, last_order: _last, option: _option, options: _options, ...rest } = pre as DealPrefill & { option?: string | null; options?: string[] };
  void _last; void _options;
  const initial: DealInput = {
    ...EMPTY_DEAL, ...Object.fromEntries(Object.entries(rest).filter(([, v]) => v != null)),
    booked_on: new Date().toISOString().slice(0, 10),
    lines: (rest.lines ?? []).map((l) => ({ ...l, discount_pct: l.discount_pct ?? 0, added_value: l.added_value ?? false, qty: l.qty ?? 1 })),
  } as DealInput;
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="New order"
        crumbs={[{ label: "Sales Orders", href: "/sales" }, { label: "Orders", href: "/sales/deals" }]}
        description={sp.proposal ? `Started from the proposal${_option ? ` (${_option})` : ""}: check the issues and prices, then confirm.` : "Everything the client has agreed, in one place. Each item becomes a booking in its issue, and the confirmation is printed from it."}
      />
      <DealForm initial={initial} titles={meta.titles} reps={meta.reps} rates={rates} company={company ?? null} contact={contact ?? null} myRepId={meta.my_rep_id ?? (rest.rep_id ?? null)} />
    </div>
  );
}
