import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  ClipboardCheck,
  Power,
  ShieldCheck,
  Sparkles,
  Timer,
} from "lucide-react";
import { backendFetch } from "@/lib/backend";
import { humanizeCron, styleForKind } from "@/lib/automation-style";
import type { ReviewKind, ReviewQueueCounts, ScheduledJob } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export default async function AutomationsPage() {
  const [kinds, counts, jobs] = await Promise.all([
    backendFetch<ReviewKind[]>("/api/review-queue/kinds"),
    backendFetch<ReviewQueueCounts[]>("/api/review-queue/counts"),
    backendFetch<ScheduledJob[]>("/api/automations/jobs"),
  ]);

  const countFor = (k: string) =>
    counts.find((c) => c.kind === k) ?? { kind: k, pending: 0, approved: 0, rejected: 0 };
  const totalPending = counts.reduce((sum, c) => sum + c.pending, 0);
  const totalHandled = counts.reduce((sum, c) => sum + c.approved + c.rejected, 0);
  const jobsLive = jobs.filter((j) => j.enabled).length;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 p-4 sm:p-6 lg:p-8">
      {/* Editorial header - matches the dashboard's */}
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/80 pb-5">
        <div>
          <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
            <Sparkles className="size-3.5" />
            <span>Automations · Stage 1</span>
          </div>
          <h1 className="editorial-title text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            Data Hygiene, on Autopilot
          </h1>
          <p className="mt-1 max-w-2xl text-xs text-muted-foreground sm:text-sm">
            Every automation drafts a decision and waits for a human. Nothing here sends an email,
            merges a record, or reassigns an account without you confirming it first.
          </p>
        </div>
        <Link href="/automations/review">
          <Badge
            variant={totalPending > 0 ? "default" : "outline"}
            className="cursor-pointer gap-1.5 px-3.5 py-2 text-xs font-semibold shadow-xs"
          >
            <ClipboardCheck className="size-3.5" />
            {totalPending.toLocaleString()} waiting for you
            <ArrowRight className="size-3.5" />
          </Badge>
        </Link>
      </div>

      {/* Trust banner - the human-in-the-loop promise, made visually central
          rather than a throwaway line of body copy, since this is the one
          thing that actually calms "is this going to do something dumb". */}
      <Card className="editorial-card relative overflow-hidden border-primary/20 bg-gradient-to-br from-primary/[0.06] via-transparent to-transparent">
        <div className="absolute -right-10 -top-10 size-40 rounded-full bg-primary/10 blur-3xl" aria-hidden="true" />
        <CardContent className="relative flex flex-wrap items-center gap-4 p-5">
          <div className="flex size-11 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
            <ShieldCheck className="size-5" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-bold text-foreground">Draft, never dispatch.</p>
            <p className="text-xs text-muted-foreground">
              Every item below is a suggestion, not an action already taken. It only touches the CRM
              the moment you click a specific button and choose exactly what happens.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* KPI strip - same visual language as the dashboard's, but the
          numbers that actually matter for this screen: what's waiting,
          what's been handled, and how much of the machine is switched on. */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="editorial-card h-full overflow-hidden transition-all hover:shadow-xs">
          <div className="h-1 w-full bg-gradient-to-r from-amber-600 to-amber-700" />
          <CardContent className="flex items-center justify-between p-6">
            <div>
              <div className="editorial-stat font-serif text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                {totalPending.toLocaleString()}
              </div>
              <div className="mt-1 text-sm font-bold text-foreground">Waiting for review</div>
              <div className="text-xs text-muted-foreground">Across every automation</div>
            </div>
            <span className="flex size-12 shrink-0 items-center justify-center rounded-xl border border-border bg-muted/60 text-amber-600 dark:text-amber-400">
              <ClipboardCheck className="size-6" />
            </span>
          </CardContent>
        </Card>

        <Card className="editorial-card h-full overflow-hidden transition-all hover:shadow-xs">
          <div className="h-1 w-full bg-gradient-to-r from-emerald-600 to-emerald-700" />
          <CardContent className="flex items-center justify-between p-6">
            <div>
              <div className="editorial-stat font-serif text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                {totalHandled.toLocaleString()}
              </div>
              <div className="mt-1 text-sm font-bold text-foreground">Handled so far</div>
              <div className="text-xs text-muted-foreground">Decisions your team has made</div>
            </div>
            <span className="flex size-12 shrink-0 items-center justify-center rounded-xl border border-border bg-muted/60 text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="size-6" />
            </span>
          </CardContent>
        </Card>

        <Card className="editorial-card h-full overflow-hidden transition-all hover:shadow-xs">
          <div className="h-1 w-full bg-gradient-to-r from-blue-600 to-blue-700" />
          <CardContent className="flex items-center justify-between p-6">
            <div>
              <div className="editorial-stat font-serif text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                {jobsLive}
                <span className="text-lg text-muted-foreground">/{jobs.length}</span>
              </div>
              <div className="mt-1 text-sm font-bold text-foreground">Scanners live</div>
              <div className="text-xs text-muted-foreground">Mailbox jobs currently switched on</div>
            </div>
            <span className="flex size-12 shrink-0 items-center justify-center rounded-xl border border-border bg-muted/60 text-blue-600 dark:text-blue-400">
              <Timer className="size-6" />
            </span>
          </CardContent>
        </Card>
      </div>

      {/* Automation cards - one per registered kind, richer and denser than
          a plain list: icon, live throughput, and a clear call to action. */}
      <div>
        <h2 className="editorial-heading mb-3 text-lg font-bold text-foreground">Automations</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {kinds.map((k) => {
            const style = styleForKind(k.kind);
            const Icon = style.icon;
            const c = countFor(k.kind);
            const handled = c.approved + c.rejected;
            return (
              <Link key={k.kind} href={`/automations/review?kind=${k.kind}`} className="group">
                <Card
                  className={`editorial-card h-full overflow-hidden transition-all hover:shadow-xs ${style.ring}`}
                >
                  <div className={`h-1 w-full bg-gradient-to-r ${style.accent}`} />
                  <CardContent className="flex flex-col gap-3 p-5">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <span
                          className={`flex size-11 shrink-0 items-center justify-center rounded-xl border transition-transform group-hover:scale-105 ${style.chipBg} ${style.color}`}
                        >
                          <Icon className="size-5" />
                        </span>
                        <div>
                          <div className="text-sm font-bold text-foreground">{k.label}</div>
                          <div className="text-[11px] text-muted-foreground">
                            {handled.toLocaleString()} handled all-time
                          </div>
                        </div>
                      </div>
                      <Badge
                        variant={c.pending > 0 ? "default" : "secondary"}
                        className="shrink-0 text-xs font-semibold"
                      >
                        {c.pending} pending
                      </Badge>
                    </div>
                    <p className="text-xs leading-relaxed text-muted-foreground">{k.description}</p>
                    <div className="flex items-center justify-between border-t border-border/70 pt-2.5">
                      <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                        <span className="font-semibold text-foreground">{k.actions.length}</span>
                        review action{k.actions.length === 1 ? "" : "s"} available
                      </div>
                      <span className="flex items-center gap-1 text-xs font-semibold text-primary transition-transform group-hover:translate-x-0.5">
                        Review <ArrowRight className="size-3.5" />
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
          {kinds.length === 0 && (
            <Card className="editorial-card sm:col-span-2">
              <CardContent className="py-10 text-center text-sm text-muted-foreground">
                No automations registered yet.
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Scanner status - the mailbox-polling cron jobs underneath these
          automations (see app/automations/scheduler.py). Purely
          informational: there's no on/off switch here on purpose, since
          flipping one is an env-var + restart decision made deliberately
          outside the app, not a click a reviewer should be able to make. */}
      <div>
        <h2 className="editorial-heading mb-3 text-lg font-bold text-foreground">Mailbox scanners</h2>
        <Card className="editorial-card">
          <CardHeader className="border-b pb-3">
            <p className="text-xs text-muted-foreground">
              These run on a schedule to find new items for the automations above. Both start
              switched off until mailbox access is wired in and someone deliberately turns them on.
            </p>
          </CardHeader>
          <CardContent className="flex flex-col divide-y divide-border/70 p-0">
            {jobs.map((j) => (
              <div key={j.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
                <div className="flex items-center gap-3">
                  <span
                    className={`flex size-9 shrink-0 items-center justify-center rounded-lg border ${
                      j.enabled
                        ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-600"
                        : "border-border bg-muted/60 text-muted-foreground"
                    }`}
                  >
                    <Power className="size-4" />
                  </span>
                  <div>
                    <div className="text-xs font-bold text-foreground">{j.label}</div>
                    <div className="text-[11px] text-muted-foreground">{j.description}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-medium text-muted-foreground">
                    {humanizeCron(j.cron)}
                  </span>
                  <Badge
                    variant="outline"
                    className={
                      j.enabled
                        ? "border-emerald-500/40 text-[10px] font-bold text-emerald-600"
                        : "border-border text-[10px] font-bold text-muted-foreground"
                    }
                  >
                    {j.enabled ? "LIVE" : "OFF"}
                  </Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
