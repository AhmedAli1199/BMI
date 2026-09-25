"use client";

import { Fragment, useState, useTransition } from "react";
import Link from "next/link";
import { ChevronDown, ExternalLink, Loader2 } from "lucide-react";
import { styleForKind, humanizeCron } from "@/lib/automation-style";
import { fmtAgo, fmtCount, fmtDuration, fmtPercent } from "@/lib/automation-format";
import { getKindDetail, getQueueInsights } from "@/lib/actions";
import type { AutomationStats, JobSummary, KindDetail, ReviewQueueInsights, StatsRange } from "@/lib/types";
import { Sparkline } from "@/components/automations/charts";

type Loaded = { detail: KindDetail; insights: ReviewQueueInsights | null };

/** One row per automation instead of cards - comparable columns, and room
 * for more automations without the page turning into a wall of tiles.
 * Opening a row loads its detail panel on demand (progressive disclosure:
 * the table stays scannable, the depth is one click away). */
export function AutomationsTable({ rows, range }: { rows: AutomationStats[]; range: StatsRange }) {
  const [open, setOpen] = useState<string | null>(null);
  const [loaded, setLoaded] = useState<Record<string, Loaded>>({});
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function toggle(kind: string) {
    const next = open === kind ? null : kind;
    setOpen(next);
    setError(null);
    if (next && !loaded[next]) {
      startTransition(async () => {
        try {
          const [detail, insights] = await Promise.all([
            getKindDetail(next, range),
            getQueueInsights(next).catch(() => null),
          ]);
          setLoaded((prev) => ({ ...prev, [next]: { detail, insights } }));
        } catch {
          setError("Couldn't load details - try again.");
        }
      });
    }
  }

  const rangeLabel = range === "7d" ? "7 days" : range === "30d" ? "30 days" : "all time";

  return (
    <div className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
      <table className="w-full min-w-[760px] text-sm">
        <caption className="sr-only">Automations in this workstream, {rangeLabel}. Open a row for details.</caption>
        <thead>
          <tr className="border-b border-border/70 text-left text-xs font-semibold text-muted-foreground">
            <th scope="col" className="px-4 py-2.5 font-semibold">Automation</th>
            <th scope="col" className="px-3 py-2.5 font-semibold">Scanner</th>
            <th scope="col" className="px-3 py-2.5 text-right font-semibold">Pending</th>
            <th scope="col" className="px-3 py-2.5 text-right font-semibold">New</th>
            <th scope="col" className="px-3 py-2.5 text-right font-semibold">Resolved</th>
            <th scope="col" className="px-3 py-2.5 text-right font-semibold" title="Share of resolved suggestions your team approved rather than dismissed">
              Acted on
            </th>
            <th scope="col" className="px-3 py-2.5 text-right font-semibold" title="Median time from suggestion to decision">
              Time to resolve
            </th>
            <th scope="col" className="px-3 py-2.5 font-semibold">Last 7 days</th>
            <th scope="col" className="w-10 px-3 py-2.5"><span className="sr-only">Details</span></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((a) => {
            const style = styleForKind(a.kind);
            const Icon = style.icon;
            const isOpen = open === a.kind;
            const panelId = `detail-${a.kind}`;
            return (
              <Fragment key={a.kind}>
                <tr
                  className={`cursor-pointer border-b border-border/60 transition-colors hover:bg-muted/40 ${isOpen ? "bg-muted/40" : ""}`}
                  onClick={(e) => {
                    if ((e.target as HTMLElement).closest("a,button")) return;
                    toggle(a.kind);
                  }}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <span className={`brand-icon size-8 shrink-0 ${style.chipBg} ${style.color}`} aria-hidden="true">
                        <Icon className="size-4" />
                      </span>
                      <div className="min-w-0">
                        <div className="font-semibold text-foreground">{a.label}</div>
                        <div className="line-clamp-1 max-w-[280px] text-xs text-muted-foreground">{a.description}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-3">
                    <ScannerStatus job={a.job} />
                  </td>
                  <td className="px-3 py-3 text-right tabular-nums">
                    {a.pending > 0 ? (
                      <Link
                        href={`/automations/review?kind=${a.kind}`}
                        className="font-bold hover:underline"
                        style={{ color: "var(--warn)" }}
                      >
                        {fmtCount(a.pending)}
                      </Link>
                    ) : (
                      <span className="text-muted-foreground">0</span>
                    )}
                    {a.oldest_pending_at && (
                      <div className="text-[11px] text-muted-foreground">oldest {fmtAgo(a.oldest_pending_at).replace(" ago", "")}</div>
                    )}
                  </td>
                  <td className="px-3 py-3 text-right tabular-nums">{fmtCount(a.new)}</td>
                  <td className="px-3 py-3 text-right tabular-nums">{fmtCount(a.resolved)}</td>
                  <td className="px-3 py-3 text-right tabular-nums">{fmtPercent(a.acted_on_rate)}</td>
                  <td className="px-3 py-3 text-right tabular-nums">{fmtDuration(a.median_resolve_seconds)}</td>
                  <td className="px-3 py-3">
                    <Sparkline values={a.daily_new} />
                  </td>
                  <td className="px-3 py-3">
                    <button
                      type="button"
                      onClick={() => toggle(a.kind)}
                      aria-expanded={isOpen}
                      aria-controls={panelId}
                      aria-label={`${isOpen ? "Hide" : "Show"} details for ${a.label}`}
                      className="flex size-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
                    >
                      <ChevronDown className={`size-4 transition-transform ${isOpen ? "rotate-180" : ""}`} aria-hidden="true" />
                    </button>
                  </td>
                </tr>
                {isOpen && (
                  <tr id={panelId} className="border-b border-border/60 bg-muted/20">
                    <td colSpan={9} className="px-4 py-4">
                      {loaded[a.kind] ? (
                        <DetailPanel row={a} data={loaded[a.kind]} rangeLabel={rangeLabel} />
                      ) : error ? (
                        <p className="text-xs" style={{ color: "var(--bad)" }}>{error}</p>
                      ) : (
                        <p className="flex items-center gap-2 text-xs text-muted-foreground" aria-live="polite">
                          <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
                          {pending ? "Loading details…" : ""}
                        </p>
                      )}
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ScannerStatus({ job }: { job: JobSummary | null }) {
  if (!job) return <span className="text-xs text-muted-foreground">Manual upload</span>;
  const run = job.last_run;
  const failed = run?.status === "failed";
  const color = !job.enabled ? "var(--muted-foreground)" : failed ? "var(--bad)" : "var(--ok)";
  return (
    <div className="flex items-start gap-2 text-xs">
      <span className="mt-1 size-2 shrink-0 rounded-full" style={{ background: color }} aria-hidden="true" />
      <div>
        <div className="font-semibold text-foreground">{!job.enabled ? "Off" : failed ? "Last run failed" : "On"}</div>
        <div className="whitespace-nowrap text-muted-foreground">{run ? `ran ${fmtAgo(run.started_at)}` : "never run"}</div>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border/70 bg-card p-3.5">
      <h3 className="text-xs font-bold text-foreground">{title}</h3>
      {children}
    </div>
  );
}

function DetailPanel({ row, data, rangeLabel }: { row: AutomationStats; data: Loaded; rangeLabel: string }) {
  const { detail, insights } = data;
  const totalOutcomes = detail.outcomes.reduce((s, o) => s + o.count, 0);
  const run = row.job?.last_run;
  const runSeconds = run?.finished_at ? (new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()) / 1000 : null;

  return (
    <div className="flex flex-col gap-3">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Section title={`What your team decided (${rangeLabel})`}>
          {totalOutcomes === 0 ? (
            <p className="text-xs text-muted-foreground">No decisions in this period.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {detail.outcomes.map((o) => {
                const pct = Math.round((o.count / totalOutcomes) * 100);
                return (
                  <li key={`${o.action_id}-${o.status}`} className="text-xs">
                    <div className="mb-1 flex justify-between gap-2">
                      <span className="truncate text-foreground">{o.label}</span>
                      <span className="shrink-0 tabular-nums text-muted-foreground">
                        {fmtCount(o.count)} · {pct}%
                      </span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-muted" aria-hidden="true">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${pct}%`, background: o.status === "approved" ? "var(--ok)" : "var(--muted-foreground)" }}
                      />
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </Section>

        <Section title="Waiting now, by type">
          {insights && insights.buckets.length > 0 ? (
            <ul className="flex flex-col gap-1.5">
              {insights.buckets.map((b) => (
                <li key={b.key}>
                  <Link
                    href={`/automations/review?kind=${row.kind}&bucket=${b.key}`}
                    className="flex items-center justify-between gap-2 rounded-md px-2 py-1 text-xs hover:bg-muted"
                  >
                    <span className="text-foreground">{b.label}</span>
                    <span className="font-semibold tabular-nums">{fmtCount(b.count)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-muted-foreground">
              {row.pending > 0 ? `${fmtCount(row.pending)} waiting - no breakdown for this automation.` : "Nothing waiting."}
            </p>
          )}
        </Section>

        <Section title="Scanner health">
          {row.job ? (
            <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
              <dt className="text-muted-foreground">Schedule</dt>
              <dd className="text-foreground">{humanizeCron(row.job.cron)}</dd>
              <dt className="text-muted-foreground">Status</dt>
              <dd className="text-foreground">{row.job.enabled ? "Switched on" : "Switched off"}</dd>
              <dt className="text-muted-foreground">Last run</dt>
              <dd className="text-foreground">
                {run ? `${fmtAgo(run.started_at)} · ${run.status === "failed" ? "failed" : run.status === "running" ? "running" : "succeeded"}` : "No runs recorded yet"}
              </dd>
              {run && (
                <>
                  <dt className="text-muted-foreground">Found</dt>
                  <dd className="text-foreground">{fmtCount(run.items_queued)} item{run.items_queued === 1 ? "" : "s"}{runSeconds !== null ? ` in ${fmtDuration(runSeconds)}` : ""}</dd>
                </>
              )}
              {run?.error && (
                <>
                  <dt className="text-muted-foreground">Error</dt>
                  <dd className="break-words" style={{ color: "var(--bad)" }}>{run.error}</dd>
                </>
              )}
            </dl>
          ) : (
            <p className="text-xs text-muted-foreground">Created from photo uploads, not a scheduled scanner.</p>
          )}
          <Link href="/automations/engine" className="mt-auto text-xs font-semibold text-primary hover:underline">
            All scanners &rarr;
          </Link>
        </Section>

        <Section title="Reviewers & AI cost">
          {detail.top_reviewers.length > 0 ? (
            <ul className="flex flex-col gap-1 text-xs">
              {detail.top_reviewers.map((r) => (
                <li key={r.name} className="flex justify-between gap-2">
                  <span className="truncate text-foreground">{r.name}</span>
                  <span className="tabular-nums text-muted-foreground">{fmtCount(r.count)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-muted-foreground">No named reviewers in this period.</p>
          )}
          <div className="mt-1 border-t border-border/70 pt-2 text-xs">
            {detail.ai_cost_usd === null ? (
              <span className="text-muted-foreground">No AI calls - rule-based.</span>
            ) : (
              <>
                <span className="font-semibold text-foreground tabular-nums">${detail.ai_cost_usd.toFixed(2)}</span>
                <span className="text-muted-foreground"> across {fmtCount(detail.ai_calls ?? 0)} AI calls</span>
                {detail.ai_cost_shared_with.length > 0 && (
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    Shared with {detail.ai_cost_shared_with.join(", ")} (same scanner).
                  </p>
                )}
              </>
            )}
          </div>
        </Section>
      </div>

      <div className="rounded-lg border border-border/70 bg-card">
        <div className="flex items-center justify-between border-b border-border/70 px-3.5 py-2">
          <h3 className="text-xs font-bold text-foreground">Latest items</h3>
          <Link href={`/automations/review?kind=${row.kind}`} className="flex items-center gap-1 text-xs font-semibold text-primary hover:underline">
            Open in Review Queue <ExternalLink className="size-3" aria-hidden="true" />
          </Link>
        </div>
        {detail.recent.length === 0 ? (
          <p className="px-3.5 py-3 text-xs text-muted-foreground">No items yet.</p>
        ) : (
          <ul className="divide-y divide-border/60">
            {detail.recent.map((r) => (
              <li key={r.id}>
                <Link
                  href={`/automations/review?kind=${row.kind}&status=${r.status}`}
                  className="flex items-center gap-3 px-3.5 py-2 text-xs hover:bg-muted/40"
                >
                  <StatusPill status={r.status} />
                  <span className="min-w-0 flex-1 truncate text-foreground">{r.summary}</span>
                  <span className="shrink-0 text-muted-foreground">{fmtAgo(r.created_at)}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const color = status === "approved" ? "var(--ok)" : status === "rejected" ? "var(--muted-foreground)" : "var(--warn)";
  const label = status === "approved" ? "Approved" : status === "rejected" ? "Rejected" : "Pending";
  return (
    <span
      className="w-[70px] shrink-0 rounded-full border px-2 py-px text-center text-[10.5px] font-semibold"
      style={{ color, borderColor: color }}
    >
      {label}
    </span>
  );
}
