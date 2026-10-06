import Link from "next/link";
import { FileText, Plus } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { Proposal } from "@/lib/proposals-types";
import { Button } from "@/components/ui/button";
import { EmptyState, SalesHeader, fmtDate, fmtGBP } from "@/components/sales/sales-ui";

export default async function ProposalsPage() {
  const proposals = await backendFetch<Proposal[]>("/api/proposals").catch(() => [] as Proposal[]);
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="Proposals"
        crumbs={[{ label: "Sales Orders", href: "/sales" }]}
        description="Proposals you've drafted in BMI's Word templates. Sent ones stay here and on the client's record, with what was offered and the follow-up date."
        actions={
          <Button size="sm" className="gap-1.5" nativeButton={false} render={<Link href="/sales/proposals/new" />}>
            <Plus className="size-3.5" /> New proposal
          </Button>
        }
      />
      {proposals.length === 0 ? (
        <EmptyState icon={FileText} title="No proposals yet">
          Start one from here, or from the Build a proposal button on any client&apos;s page.
        </EmptyState>
      ) : (
        <div className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs">
          <table className="w-full text-sm">
            <caption className="sr-only">Proposals</caption>
            <thead>
              <tr className="text-left text-xs text-muted-foreground">
                <th scope="col" className="px-4 py-2 font-semibold">Client</th>
                <th scope="col" className="px-2 py-2 font-semibold">Campaign</th>
                <th scope="col" className="px-2 py-2 font-semibold">Title</th>
                <th scope="col" className="px-2 py-2 text-right font-semibold">Total (before VAT)</th>
                <th scope="col" className="px-2 py-2 font-semibold">Status</th>
                <th scope="col" className="px-4 py-2 font-semibold">By</th>
              </tr>
            </thead>
            <tbody>
              {proposals.map((p) => (
                <tr key={p.id} className="border-t border-border/60 hover:bg-muted/40">
                  <td className="px-4 py-2 font-medium">
                    <Link href={`/sales/proposals/${p.id}`} className="hover:underline">{p.company_name}</Link>
                  </td>
                  <td className="px-2 py-2">{p.campaign_name}</td>
                  <td className="px-2 py-2 text-muted-foreground">{p.title_name ?? "—"}</td>
                  <td className="px-2 py-2 text-right font-semibold tabular-nums">{fmtGBP(p.total_gbp)}</td>
                  <td className="px-2 py-2">
                    {p.status === "sent" ? (
                      <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">Sent {fmtDate(p.sent_at?.slice(0, 10))}</span>
                    ) : (
                      <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-semibold text-muted-foreground">Draft</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-xs text-muted-foreground">{p.created_by ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
