import Link from "next/link";
import { notFound } from "next/navigation";
import { BellRing, FileText } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import { canUseAutomations } from "@/lib/access";
import type { ManagementAlert, WeeklySummary, WeeklySummaryListItem } from "@/lib/sales-types";
import { RunJobButton } from "@/components/run-job-button";
import { EmptyState, SalesHeader, SectionTitle, fmtDate } from "@/components/sales/sales-ui";

const dateTime = (iso: string) => new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

export default async function SummariesPage({ searchParams }: { searchParams: Promise<{ id?: string }> }) {
  const session = await getSession();
  if (!canUseAutomations(session)) notFound();

  const { id } = await searchParams;
  const [list, alerts] = await Promise.all([
    backendFetch<WeeklySummaryListItem[]>("/api/management/summaries"),
    backendFetch<ManagementAlert[]>("/api/management/alerts?limit=20"),
  ]);
  const chosen = id ?? list[0]?.id;
  const current = chosen ? await backendFetch<WeeklySummary>(`/api/management/summaries/${chosen}`) : null;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="Weekly summary & alerts"
        description="The Monday leadership brief and the early-warning alerts for editions running behind last cycle. Every figure comes from the order register, the same numbers as the dashboard."
        actions={
          <>
            <RunJobButton jobId="weekly_management_summary" />
            <Link href="/sales/dashboard" className="text-xs font-semibold text-primary hover:underline">
              Open the dashboard →
            </Link>
          </>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <section aria-labelledby="brief-heading" className="lg:col-span-2">
          <SectionTitle id="brief-heading" hint="Every section always appears. Only the headline may be written by AI, and it is discarded if it contains any figure that isn't in the source data; the rest is assembled directly from the numbers.">
            {current ? `Week of ${fmtDate(current.week_of)}` : "Latest brief"}
          </SectionTitle>
          {!current ? (
            <EmptyState icon={FileText} title="No summary has been written yet">
              The brief is written on Monday mornings once &quot;Weekly management summary&quot; is switched on under Scanners &amp; Settings. Use Run now to write this week&apos;s straight away.
            </EmptyState>
          ) : (
            <article className="flex flex-col gap-5 rounded-xl border border-border/80 bg-card p-5 shadow-2xs">
              <p className="text-xs text-muted-foreground">
                Written {dateTime(current.generated_at)} · {current.source === "ai" ? "headline written by AI, figures from the register" : "assembled from the figures directly"}
              </p>
              {current.sections.map((s) => (
                <section key={s.key} aria-labelledby={`sec-${s.key}`}>
                  <h3 id={`sec-${s.key}`} className={s.key === "headline" ? "sr-only" : "mb-1.5 text-sm font-bold text-foreground"}>
                    {s.title}
                  </h3>
                  {s.paragraphs.map((p, i) => (
                    <p key={i} className={s.key === "headline" ? "editorial-title text-lg font-semibold leading-snug text-foreground" : "mb-1.5 text-sm text-foreground/90"}>
                      {p}
                    </p>
                  ))}
                  {s.table ? (
                    <div className="mt-2 overflow-x-auto rounded-lg border border-border/70">
                      <table className="w-full min-w-[34rem] text-sm">
                        <caption className="sr-only">{s.title}</caption>
                        <thead>
                          <tr className="border-b border-border/70 text-left text-xs font-semibold text-muted-foreground">
                            {s.table.columns.map((c, i) => (
                              <th key={c} scope="col" className={`px-3 py-2 font-semibold ${i ? "text-right" : ""}`}>
                                {c}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {s.table.rows.map((r, ri) => (
                            <tr key={ri} className="border-b border-border/60 last:border-0 hover:bg-accent/40">
                              {r.cells.map((c, ci) => {
                                const href = ci === 0 ? r.href : r.links?.[String(ci)];
                                return (
                                  <td key={ci} className={`px-3 py-2 ${ci ? "text-right tabular-nums" : "font-semibold text-foreground"}`}>
                                    {href ? (
                                      <Link href={href} className="hover:text-primary hover:underline">
                                        {c}
                                      </Link>
                                    ) : (
                                      c
                                    )}
                                  </td>
                                );
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : s.bullets.length > 0 && (
                    <ul className="mt-1 flex list-disc flex-col gap-1 pl-5 text-sm text-foreground/90">
                      {s.bullets.map((b, i) => (
                        <li key={i}>
                          {b.href ? (
                            <Link href={b.href} className="hover:text-primary hover:underline">
                              {b.text}
                            </Link>
                          ) : (
                            b.text
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              ))}
            </article>
          )}
        </section>

        <div className="flex flex-col gap-6">
          <section aria-labelledby="alerts-heading">
            <SectionTitle
              id="alerts-heading"
              hint="Fired daily when an issue or event has booked far less than its equivalent edition had at the same point last cycle. The same edition isn't alerted again within the cooldown."
              aside={<RunJobButton jobId="management_alerts_scan" />}
            >
              Recent alerts
            </SectionTitle>
            {alerts.length === 0 ? (
              <EmptyState icon={BellRing} title="No alerts have fired">
                Nothing has fallen behind its equivalent edition by enough to alert.
              </EmptyState>
            ) : (
              <ul className="flex flex-col divide-y divide-border/60 overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs">
                {alerts.map((a) => (
                  <li key={a.id} className="px-4 py-3">
                    <Link href={`/sales/editions/${a.subject_id}`} className="text-sm font-semibold text-foreground hover:text-primary hover:underline">
                      {a.subject_label}
                    </Link>
                    <p className="mt-0.5 text-xs text-muted-foreground">{a.message}</p>
                    <p className="mt-1 text-[11px] text-muted-foreground/80">{dateTime(a.fired_at)}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {list.length > 1 && (
            <section aria-labelledby="archive-heading">
              <SectionTitle id="archive-heading">Earlier weeks</SectionTitle>
              <ul className="flex flex-col divide-y divide-border/60 overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs">
                {list.map((s) => (
                  <li key={s.id}>
                    <Link href={`/sales/summaries?id=${s.id}`} className={`block px-4 py-2.5 text-sm hover:bg-accent/40 ${s.id === chosen ? "font-semibold text-primary" : "text-foreground"}`}>
                      Week of {fmtDate(s.week_of)}
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
