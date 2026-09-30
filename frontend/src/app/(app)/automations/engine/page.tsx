import Link from "next/link";
import { Coins, Settings2 } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import { canUseAutomations } from "@/lib/access";
import { getSession } from "@/lib/session";
import { humanizeCron } from "@/lib/automation-style";
import { fmtAgo, fmtCount, fmtDuration } from "@/lib/automation-format";
import type { JobRun, ScheduledJob } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { RunJobButton } from "@/components/run-job-button";
import { HubHeader, StaffOnly } from "@/components/automations/hub-ui";

const RUN_COLOR: Record<JobRun["status"], string> = {
  success: "var(--ok)",
  failed: "var(--bad)",
  running: "var(--warn)",
};

function runSeconds(r: JobRun): number | null {
  return r.finished_at ? (new Date(r.finished_at).getTime() - new Date(r.started_at).getTime()) / 1000 : null;
}

export default async function ScannersPage() {
  const session = await getSession();
  if (!canUseAutomations(session)) return <StaffOnly />;

  const [jobs, runs] = await Promise.all([
    backendFetch<ScheduledJob[]>("/api/automations/jobs"),
    backendFetch<Record<string, JobRun[]>>("/api/automations/job-runs?per_job=10"),
  ]);
  const active = jobs.filter((j) => j.enabled).length;
  const failing = jobs.filter((j) => runs[j.id]?.[0]?.status === "failed").length;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <HubHeader
        crumb
        title="Scanners & Settings"
        description="The background scanners that find work for the review queue - when they run, whether their last run worked, and what they found."
        actions={
          <>
            <Button variant="outline" size="sm" nativeButton={false} className="gap-1.5 font-semibold" render={<Link href="/automations/llm-usage" />}>
              <Coins className="size-3.5" aria-hidden="true" />
              AI usage &amp; cost
            </Button>
            <Button variant="outline" size="sm" nativeButton={false} className="gap-1.5 font-semibold" render={<Link href="/automations/settings" />}>
              <Settings2 className="size-3.5" aria-hidden="true" />
              Automation settings
            </Button>
          </>
        }
      />

      <p className="text-sm text-muted-foreground" aria-live="polite">
        <span className="font-semibold text-foreground">{active}</span> of {jobs.length} scanners switched on
        {failing > 0 && (
          <>
            {" · "}
            <span className="font-semibold" style={{ color: "var(--bad)" }}>
              {failing} failed on their last run
            </span>
          </>
        )}
      </p>

      <div className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
        <table className="w-full min-w-[900px] text-sm">
          <caption className="sr-only">Scheduled scanners and their recent run history</caption>
          <thead>
            <tr className="border-b border-border/70 text-left text-xs font-semibold text-muted-foreground">
              <th scope="col" className="px-4 py-2.5 font-semibold">Scanner</th>
              <th scope="col" className="px-3 py-2.5 font-semibold">Schedule</th>
              <th scope="col" className="px-3 py-2.5 font-semibold">Last run</th>
              <th scope="col" className="px-3 py-2.5 text-right font-semibold">Found</th>
              <th scope="col" className="px-3 py-2.5 text-right font-semibold">Took</th>
              <th scope="col" className="px-3 py-2.5 whitespace-nowrap font-semibold">Last 10 runs</th>
              <th scope="col" className="px-4 py-2.5 text-right font-semibold"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((j) => {
              const history = runs[j.id] ?? [];
              const last = history[0];
              const secs = last ? runSeconds(last) : null;
              return (
                <tr key={j.id} className="border-b border-border/60 align-top last:border-0">
                  <td className="px-4 py-3.5">
                    <div className="flex items-start gap-2.5">
                      <span
                        className="mt-1.5 size-2 shrink-0 rounded-full"
                        style={{ background: j.enabled ? "var(--ok)" : "var(--muted-foreground)" }}
                        aria-hidden="true"
                      />
                      <div className="min-w-0">
                        <div className="font-semibold text-foreground">
                          {j.label}
                          <span className="ml-2 text-xs font-medium text-muted-foreground">{j.enabled ? "On" : "Off"}</span>
                        </div>
                        <div className="max-w-md text-xs text-muted-foreground">{j.description}</div>
                        {last?.status === "failed" && last.error && (
                          <div className="mt-1 max-w-md break-words text-xs" style={{ color: "var(--bad)" }}>
                            {last.error}
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-3.5 text-xs text-foreground">{humanizeCron(j.cron)}</td>
                  <td className="px-3 py-3.5 text-xs">
                    {last ? (
                      <>
                        <div className="font-semibold" style={{ color: RUN_COLOR[last.status] }}>
                          {last.status === "success" ? "Succeeded" : last.status === "failed" ? "Failed" : "Running"}
                        </div>
                        <div className="text-muted-foreground">
                          {fmtAgo(last.started_at)}
                          {last.trigger === "manual" ? " · manual" : ""}
                        </div>
                      </>
                    ) : (
                      <span className="whitespace-nowrap text-muted-foreground">Never run</span>
                    )}
                  </td>
                  <td className="px-3 py-3.5 text-right text-xs tabular-nums">{last ? fmtCount(last.items_queued) : "—"}</td>
                  <td className="px-3 py-3.5 text-right text-xs tabular-nums">{secs !== null ? fmtDuration(secs) : "—"}</td>
                  <td className="px-3 py-3.5">
                    {history.length > 0 ? (
                      <ol className="flex items-end gap-1" aria-label={`${history.filter((r) => r.status === "success").length} of ${history.length} recent runs succeeded`}>
                        {/* oldest -> newest, left to right */}
                        {[...history].reverse().map((r) => (
                          <li
                            key={r.id}
                            title={`${new Date(r.started_at).toLocaleString("en-GB")} · ${r.status} · found ${r.items_queued}`}
                            className="h-5 w-2 rounded-sm"
                            style={{ background: RUN_COLOR[r.status] }}
                          />
                        ))}
                      </ol>
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex justify-end">
                      <RunJobButton jobId={j.id} hasCursor={j.has_cursor} />
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
