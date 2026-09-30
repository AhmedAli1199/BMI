import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowRight, ClipboardCheck, ScanLine } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import { canUseAutomations } from "@/lib/access";
import { getSession } from "@/lib/session";
import { SOURCE_LABELS } from "@/lib/sources";
import { WORKSTREAM_IDS, fmtAgo, fmtCount, fmtDuration, fmtPercent, pctChange } from "@/lib/automation-format";
import type { WorkstreamStats } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { PhotoUploadDialog } from "@/components/photo-upload-dialog";
import { AutomationsTable } from "@/components/automations/automations-table";
import { ChartLegend, NewResolvedChart } from "@/components/automations/charts";
import { Delta, HubHeader, KpiTile, RangeSwitch, StaffOnly, parseRange } from "@/components/automations/hub-ui";

export default async function WorkstreamPage({
  params,
  searchParams,
}: {
  params: Promise<{ workstream: string }>;
  searchParams: Promise<{ range?: string }>;
}) {
  const { workstream } = await params;
  if (!(WORKSTREAM_IDS as readonly string[]).includes(workstream)) notFound();
  const range = parseRange((await searchParams).range);

  const session = await getSession();
  if (!canUseAutomations(session)) return <StaffOnly />;

  const stats = await backendFetch<WorkstreamStats>(`/api/automations/workstreams/${workstream}/stats?range=${range}`);
  const t = stats.totals;
  const periodLabel = range === "7d" ? "previous 7 days" : range === "30d" ? "previous 30 days" : null;
  const basePath = `/automations/${workstream}`;
  const isBusinessCards = workstream === "business-cards";

  // "Review N pending" goes straight to the automation with the most
  // waiting - the Review Queue filters by one automation at a time.
  const busiest = [...stats.automations].sort((a, b) => b.pending - a.pending)[0];
  const reviewHref = busiest && busiest.pending > 0 ? `/automations/review?kind=${busiest.kind}` : "/automations/review";

  const chartTotals = stats.daily.reduce((acc, d) => ({ n: acc.n + d.new, r: acc.r + d.resolved }), { n: 0, r: 0 });
  const firstBacklog = stats.daily[0]?.backlog ?? 0;
  const lastBacklog = stats.daily[stats.daily.length - 1]?.backlog ?? 0;
  const chartEmpty = chartTotals.n === 0 && chartTotals.r === 0 && lastBacklog === 0;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <HubHeader
        crumb
        title={stats.label}
        description={stats.tagline}
        actions={
          <>
            <RangeSwitch basePath={basePath} current={range} />
            <Button
              nativeButton={false}
              size="sm"
              variant={t.pending > 0 ? "default" : "outline"}
              className="gap-1.5 font-semibold"
              render={<Link href={reviewHref} />}
            >
              <ClipboardCheck className="size-3.5" aria-hidden="true" />
              {t.pending > 0 ? `Review ${fmtCount(t.pending)} pending` : "Open Review Queue"}
              <ArrowRight className="size-3.5" aria-hidden="true" />
            </Button>
          </>
        }
      />

      {/* This page is mainly for doing, not reading - uploads come first. */}
      {isBusinessCards && (
        <section
          aria-labelledby="upload-heading"
          className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-primary/25 bg-primary/5 p-5"
        >
          <div className="flex items-start gap-3">
            <span className="brand-icon size-10 shrink-0 text-primary" aria-hidden="true">
              <ScanLine className="size-5" />
            </span>
            <div>
              <h2 id="upload-heading" className="text-sm font-bold text-foreground">
                Upload photos
              </h2>
              <p className="mt-0.5 max-w-xl text-xs text-muted-foreground">
                Snap business cards from an event or returned-copy labels from the mail room. Details are read
                automatically, checked against the CRM, and queued here for your approval.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <PhotoUploadDialog kind="business-card" publications={Object.keys(SOURCE_LABELS).filter((p) => p !== "manual")} />
            <PhotoUploadDialog kind="returned-copy" publications={Object.keys(SOURCE_LABELS).filter((p) => p !== "manual")} />
          </div>
        </section>
      )}

      <section aria-label="Key figures" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile
          label="Pending now"
          value={fmtCount(t.pending)}
          footer={t.oldest_pending_at ? `Oldest has waited ${fmtAgo(t.oldest_pending_at).replace(" ago", "")}` : "Nothing waiting"}
        />
        <KpiTile
          label="New suggestions"
          value={fmtCount(t.new)}
          delta={<Delta change={pctChange(t.new, t.new_prev)} goodWhenUp={false} />}
          footer={periodLabel ? `${fmtCount(t.new_prev ?? 0)} in the ${periodLabel}` : "All time"}
        />
        <KpiTile
          label="Resolved by your team"
          value={fmtCount(t.resolved)}
          delta={<Delta change={pctChange(t.resolved, t.resolved_prev)} goodWhenUp />}
          footer={periodLabel ? `${fmtCount(t.resolved_prev ?? 0)} in the ${periodLabel}` : "All time"}
        />
        <KpiTile
          label="Acted on"
          value={fmtPercent(t.acted_on_rate)}
          footer={
            t.median_resolve_seconds !== null
              ? `Median ${fmtDuration(t.median_resolve_seconds)} from suggestion to decision`
              : "No decisions in this period"
          }
        />
      </section>

      <section aria-labelledby="trend-heading" className="rounded-xl border border-border/80 bg-card p-5 shadow-2xs">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 id="trend-heading" className="text-sm font-bold text-foreground">
            New vs resolved{" "}
            <span className="font-normal text-muted-foreground">
              · last {stats.chart_days} days{range === "all" ? " (totals above are all-time)" : ""}
            </span>
          </h2>
          {!chartEmpty && <ChartLegend />}
        </div>
        {chartEmpty ? (
          <p className="py-10 text-center text-sm text-muted-foreground">No activity in this period.</p>
        ) : (
          <>
            <p className="sr-only">
              Over the last {stats.chart_days} days: {chartTotals.n} new and {chartTotals.r} resolved. The pending backlog went
              from {firstBacklog} to {lastBacklog}.
            </p>
            <NewResolvedChart points={stats.daily} />
          </>
        )}
      </section>

      <section aria-labelledby="automations-heading" className="flex flex-col gap-3">
        <div className="flex items-baseline justify-between gap-2">
          <h2 id="automations-heading" className="text-sm font-bold text-foreground">
            Automations <span className="font-normal text-muted-foreground">· {stats.automations.length}</span>
          </h2>
          <span className="text-xs text-muted-foreground">Open a row for decisions, scanner health and cost</span>
        </div>
        <AutomationsTable key={range} rows={stats.automations} range={range} />
      </section>
    </div>
  );
}
