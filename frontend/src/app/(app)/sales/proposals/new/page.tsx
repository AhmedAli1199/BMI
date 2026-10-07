import { backendFetch } from "@/lib/backend";
import type { SalesMeta, SalesRate } from "@/lib/sales-types";
import type { CompanyListItem } from "@/lib/types";
import { ProposalNewForm } from "@/components/sales/proposal-new-form";
import { SalesHeader } from "@/components/sales/sales-ui";

export default async function NewProposalPage({ searchParams }: { searchParams: Promise<{ company?: string; edition?: string }> }) {
  const sp = await searchParams;
  const year = new Date().getFullYear();
  const [meta, rates, company, issue] = await Promise.all([
    backendFetch<SalesMeta>("/api/sales/meta"),
    backendFetch<SalesRate[]>(`/api/sales/rates?year=${year}`).catch(() => [] as SalesRate[]),
    sp.company ? backendFetch<CompanyListItem>(`/api/companies/${sp.company}`).catch(() => null) : Promise.resolve(null),
    sp.edition ? backendFetch<{ id: string; title_id: string }>(`/api/editorial/issues/${sp.edition}`).catch(() => null) : Promise.resolve(null),
  ]);
  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="New proposal"
        crumbs={[{ label: "Sales Orders", href: "/sales" }, { label: "Proposals", href: "/sales/proposals" }]}
        description="Choose the client and what you're offering. The wording is drafted for you to edit - prices only ever come from the rate card or what you type."
      />
      <ProposalNewForm
        titles={meta.titles}
        rates={rates}
        year={year}
        company={company ? { id: company.id, label: company.name } : null}
        initialTitleId={issue?.title_id ?? null}
        initialEditionId={issue?.id ?? null}
      />
    </div>
  );
}
