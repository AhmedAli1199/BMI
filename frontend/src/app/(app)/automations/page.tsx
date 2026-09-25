import Link from "next/link";
import { redirect } from "next/navigation";
import { ArrowRight, CheckCircle2, ChevronRight, ClipboardCheck, Power } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import { styleForKind } from "@/lib/automation-style";
import { canUseAutomations } from "@/lib/access";
import { getSession } from "@/lib/session";
import { fmtAgo, fmtCount } from "@/lib/automation-format";
import type { Page, ReviewKind, ReviewQueueItem, ScheduledJob, WorkstreamSummary } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkline } from "@/components/automations/charts";
import { HubHeader, StaffOnly } from "@/components/automations/hub-ui";

const LEGACY_TABS = new Set(["sales", "capture", "hygiene", "business-cards", "engine"]);

export default async function AutomationsOverviewPage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string }>;
}) {
  // The Hub used to be one page with tabs (?tab=hygiene) - old links and
  // bookmarks land on the page that tab became.
  const { tab } = await searchParams;
  if (tab && LEGACY_TABS.has(tab)) redirect(`/automations/${tab}`);

  const session = await getSession();
  if (!canUseAutomations(session)) return <StaffOnly />;

  const [workstreams, jobs, kinds, pendingPage, approvedPage, rejectedPage] = await Promise.all([
    backendFetch<WorkstreamSummary[]>("/api/automations/workstreams"),
    backendFetch<ScheduledJob[]>("/api/automations/jobs"),
    backendFetch<ReviewKind[]>("/api/review-queue/kinds"),
    backendFetch<Page<ReviewQueueItem>>("/api/review-queue?status=pending&sort=recent&page_size=5"),
    backendFetch<Page<ReviewQueueItem>>("/api/review-queue?status=approved&sort=recent&page_size=5"),
    backendFetch<Page<ReviewQueueItem>>("/api/review-queue?status=rejected&sort=recent&page_size=5"),
  ]);

  const kindLabel = new Map(kinds.map((k) => [k.kind, k.label]));
  const totalPending = workstreams.reduce((s, w) => s + w.pending, 0);
  const jobsLive = jobs.filter((j) => j.enabled).length;
  const recentlyResolved = [...approvedPage.items, ...rejectedPage.items]
    .sort((a, b) => new Date(b.reviewed_at ?? 0).getTime() - new Date(a.reviewed_at ?? 0).getTime())
    .slice(0, 5);

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <HubHeader
        title="Automations Hub"
        description="Background automations draft suggestions; nothing is updated, merged or sent until someone on your team approves it."
        actions={
          <Button
            nativeButton={false}
            size="sm"
            variant={totalPending > 0 ? "default" : "outline"}
            className="gap-1.5 font-semibold"
            render={<Link href="/automations/review" />}
          >
            <ClipboardCheck className="size-3.5" aria-hidden="true" />
            Review {fmtCount(totalPending)} pending
            <ArrowRight className="size-3.5" aria-hidden="true" />
          </Button>
        }
      />

      {/* Workstreams - the at-a-glance view the old tab row tried to be.
          Each row opens that workstream's own page. */}
      <section aria-labelledby="ws-heading" className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs">
        <div className="flex items-center justify-between border-b border-border/70 px-5 py-3">
          <h2 id="ws-heading" className="text-sm font-bold text-foreground">
            Workstreams
          </h2>
          <span className="text-xs text-muted-foreground">Last 7 days</span>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border/70 text-left text-xs font-semibold text-muted-foreground">
              <th scope="col" className="px-5 py-2.5 font-semibold">Workstream</th>
              <th scope="col" className="px-3 py-2.5 text-right font-semibold">Pending</th>
              <th scope="col" className="hidden px-3 py-2.5 text-right font-semibold sm:table-cell">New</th>
              <th scope="col" className="hidden px-3 py-2.5 text-right font-semibold sm:table-cell">Resolved</th>
              <th scope="col" className="hidden px-3 py-2.5 font-semibold md:table-cell">New per day</th>
              <th scope="col" className="w-10 px-3 py-2.5"><span className="sr-only">Open</span></th>
            </tr>
          </thead>
          <tbody>
            {workstreams.map((w) => (
              <tr key={w.id} className="group relative border-b border-border/60 last:border-0 hover:bg-muted/40">
                <td className="px-5 py-3.5">
                  {/* The whole row is clickable via this stretched link. */}
                  <Link
                    href={`/automations/${w.id}`}
                    className="font-semibold text-foreground after:absolute after:inset-0 focus-visible:outline-none focus-visible:after:rounded-md focus-visible:after:ring-2 focus-visible:after:ring-ring"
                  >
                    {w.label}
                  </Link>
                  <div className="mt-0.5 hidden text-xs text-muted-foreground lg:block">{w.tagline}</div>
                </td>
                <td className="px-3 py-3.5 text-right tabular-nums">
                  <span className={w.pending > 0 ? "font-bold" : "text-muted-foreground"} style={w.pending > 0 ? { color: "var(--warn)" } : undefined}>
                    {fmtCount(w.pending)}
                  </span>
                </td>
                <td className="hidden px-3 py-3.5 text-right tabular-nums sm:table-cell">{fmtCount(w.new_7d)}</td>
                <td className="hidden px-3 py-3.5 text-right tabular-nums sm:table-cell">{fmtCount(w.resolved_7d)}</td>
                <td className="hidden px-3 py-3.5 md:table-cell">
                  <Sparkline values={w.daily_new_7d} />
                </td>
                <td className="px-3 py-3.5 text-muted-foreground">
                  <ChevronRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <Link
          href="/automations/engine"
          className="flex items-center justify-between gap-3 border-t border-border/70 bg-muted/30 px-5 py-3 text-xs hover:bg-muted/60"
        >
          <span className="flex items-center gap-2 font-semibold text-foreground">
            <Power className="size-3.5" aria-hidden="true" style={{ color: jobsLive > 0 ? "var(--ok)" : "var(--muted-foreground)" }} />
            Scanners &amp; Settings
          </span>
          <span className="flex items-center gap-1 text-muted-foreground">
            {jobsLive} of {jobs.length} scanners switched on
            <ChevronRight className="size-3.5" aria-hidden="true" />
          </span>
        </Link>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <FeedCard
          title="New for review"
          icon={<ClipboardCheck className="size-4" style={{ color: "var(--warn)" }} aria-hidden="true" />}
          href="/automations/review"
          empty="Nothing waiting for review."
          items={pendingPage.items.map((i) => ({
            id: i.id,
            kind: i.kind,
            summary: i.payload.summary || "New item",
            meta: kindLabel.get(i.kind) ?? i.kind,
            when: i.created_at,
            href: `/automations/review?kind=${i.kind}`,
          }))}
        />
        <FeedCard
          title="Recently resolved"
          icon={<CheckCircle2 className="size-4" style={{ color: "var(--ok)" }} aria-hidden="true" />}
          href="/automations/review?status=approved"
          empty="Nothing resolved yet."
          items={recentlyResolved.map((i) => ({
            id: i.id,
            kind: i.kind,
            summary: i.payload.summary || "Resolved item",
            meta: `${i.status === "approved" ? "Approved" : "Rejected"}${i.reviewed_by ? ` by ${i.reviewed_by.name}` : ""} · ${kindLabel.get(i.kind) ?? i.kind}`,
            when: i.reviewed_at,
            href: `/automations/review?kind=${i.kind}&status=${i.status}`,
          }))}
        />
      </div>
    </div>
  );
}

function FeedCard({
  title,
  icon,
  href,
  empty,
  items,
}: {
  title: string;
  icon: React.ReactNode;
  href: string;
  empty: string;
  items: { id: string; kind: string; summary: string; meta: string; when: string | null; href: string }[];
}) {
  return (
    <Card className="editorial-card">
      <CardHeader className="flex flex-row items-center justify-between border-b pb-3">
        <CardTitle className="text-sm font-bold text-foreground">
          <h2 className="flex items-center gap-1.5">
            {icon}
            {title}
          </h2>
        </CardTitle>
        <Link href={href} className="text-xs font-semibold text-primary hover:underline">
          View all &rarr;
        </Link>
      </CardHeader>
      <CardContent className="flex flex-col gap-1 p-3">
        {items.length > 0 ? (
          items.map((item) => {
            const style = styleForKind(item.kind);
            const Icon = style.icon;
            return (
              <Link
                key={item.id}
                href={item.href}
                className="flex items-center gap-3 rounded-lg p-2.5 transition-colors hover:bg-accent/50"
              >
                <span className={`brand-icon size-8 shrink-0 ${style.chipBg} ${style.color}`} aria-hidden="true">
                  <Icon className="size-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-xs font-bold text-foreground">{item.summary}</div>
                  <div className="truncate text-[11px] text-muted-foreground">{item.meta}</div>
                </div>
                <span className="shrink-0 text-[11px] font-medium text-muted-foreground">{fmtAgo(item.when)}</span>
              </Link>
            );
          })
        ) : (
          <span className="p-4 text-xs text-muted-foreground">{empty}</span>
        )}
      </CardContent>
    </Card>
  );
}
