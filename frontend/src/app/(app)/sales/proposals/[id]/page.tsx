import { notFound } from "next/navigation";
import { backendFetch } from "@/lib/backend";
import type { Proposal } from "@/lib/proposals-types";
import { ProposalEditor } from "@/components/sales/proposal-editor";
import { SalesHeader } from "@/components/sales/sales-ui";

export default async function ProposalPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const proposal = await backendFetch<Proposal>(`/api/proposals/${id}`).catch(() => null);
  if (!proposal) notFound();
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title={proposal.campaign_name}
        crumbs={[{ label: "Sales Orders", href: "/sales" }, { label: "Proposals", href: "/sales/proposals" }]}
        description={`For ${proposal.company_name}. Edit anything, then download the Word file. Nothing is sent from here.`}
      />
      <ProposalEditor key={`${proposal.id}-${proposal.sent_at ?? ""}`} proposal={proposal} />
    </div>
  );
}
