import Link from "next/link";
import { BarChart3, FileText, Library, PenLine, Plus } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { Proposal, WritingProfileState } from "@/lib/proposals-types";
import { Button } from "@/components/ui/button";
import { EmptyState, SalesHeader, fmtDate, fmtGBP } from "@/components/sales/sales-ui";

const PAGE = 200;

export default async function ProposalsPage({ searchParams }: { searchParams: Promise<{ show?: string }> }) {
  const sp = await searchParams;
  const shown = Math.min(Math.max(Number(sp.show) || PAGE, PAGE), 2000);
  const [fetched, style] = await Promise.all([
    // one more than we show, to know whether there are older ones
    backendFetch<Proposal[]>(`/api/proposals?limit=${shown + 1}`).catch(() => [] as Proposal[]),
    backendFetch<WritingProfileState>("/api/proposal-style").catch(() => null),
  ]);
  const more = fetched.length > shown;
  const proposals = more ? fetched.slice(0, shown) : fetched;
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="Proposals"
        crumbs={[{ label: "Sales Orders", href: "/sales" }]}
        description="Proposals sent as an email or as a Word document in BMI's templates. Sent ones stay here and on the client's record, with what was offered and the follow-up date."
        actions={
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" className="gap-1.5" nativeButton={false} render={<Link href="/sales/proposals/report" />}>
              <BarChart3 className="size-3.5" /> Report
            </Button>
            <Button size="sm" variant="outline" className="gap-1.5" nativeButton={false} render={<Link href="/sales/proposals/style" />}>
              <PenLine className="size-3.5" /> How you write
            </Button>
            <Button size="sm" variant="outline" className="gap-1.5" nativeButton={false} render={<Link href="/sales/proposals/examples" />}>
              <Library className="size-3.5" /> Examples library
            </Button>
            <Button size="sm" className="gap-1.5" nativeButton={false} render={<Link href="/sales/proposals/new" />}>
              <Plus className="size-3.5" /> New proposal
            </Button>
          </div>
        }
      />
      {style && style.status !== "ready" && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border/80 bg-card px-4 py-3 text-sm shadow-2xs">
          <PenLine className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          <span className="min-w-0 flex-1">Teach the Brain how you write: show it a few of your past proposals and your drafts come out in your own style. About 10 minutes.</span>
          <Link href="/sales/proposals/style" className="text-sm font-medium text-primary hover:underline">Start</Link>
        </div>
      )}
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
          <div className="flex items-center justify-between gap-2 border-t border-border/60 px-4 py-2 text-xs text-muted-foreground">
            <span>
              Showing the newest {proposals.length.toLocaleString("en-GB")} proposal{proposals.length === 1 ? "" : "s"}
              {more ? "" : " - that's all of them"}
            </span>
            {more && shown < 2000 && (
              <Link href={`/sales/proposals?show=${shown + PAGE}`} scroll={false} className="font-semibold text-primary hover:underline">
                Show more
              </Link>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
