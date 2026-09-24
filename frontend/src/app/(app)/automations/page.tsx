import Link from "next/link";
import {
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  Power,
  Settings2,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Timer,
} from "lucide-react";
import { backendFetch } from "@/lib/backend";
import {
  AUTOMATION_CATEGORIES,
  categoryForKind,
  humanizeCron,
  styleForKind,
} from "@/lib/automation-style";
import { canUseAutomations } from "@/lib/access";
import { getSession } from "@/lib/session";
import type { ReviewKind, ReviewQueueCounts, ScheduledJob } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PhotoUploadDialog } from "@/components/photo-upload-dialog";
import { RunJobButton } from "@/components/run-job-button";
import { SOURCE_LABELS } from "@/lib/sources";

const BUSINESS_CARD_KINDS = new Set(["business_card_new", "business_card_existing"]);

function KindCard({ k, c }: { k: ReviewKind; c: { pending: number; approved: number; rejected: number } }) {
  const style = styleForKind(k.kind);
  const Icon = style.icon;
  const handled = c.approved + c.rejected;

  return (
    <Link key={k.kind} href={`/automations/review?kind=${k.kind}`} className="group block">
      <Card className={`editorial-card h-full overflow-hidden transition-all hover:shadow-xs ${style.ring}`}>
        <div className={`masthead-rule w-full ${style.accent}`} />
        <CardContent className="flex flex-col justify-between gap-3 p-4">
          <div>
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2.5">
                <span
                  className={`brand-icon size-8 shrink-0 transition-transform group-hover:scale-105 ${style.chipBg} ${style.color}`}
                >
                  <Icon className="size-4" />
                </span>
                <div>
                  <div className="text-xs font-bold text-foreground group-hover:text-primary transition-colors">
                    {k.label}
                  </div>
                  <div className="text-[10.5px] text-muted-foreground">
                    {handled.toLocaleString()} handled all-time
                  </div>
                </div>
              </div>
              <Badge
                variant={c.pending > 0 ? "default" : "secondary"}
                className={`shrink-0 text-[10.5px] font-semibold ${
                  c.pending > 0 ? "bg-amber-600 hover:bg-amber-700" : ""
                }`}
              >
                {c.pending > 0 ? `${c.pending} pending` : "Up to date"}
              </Badge>
            </div>
            <p className="mt-2.5 text-xs leading-relaxed text-muted-foreground line-clamp-2">
              {k.description}
            </p>
          </div>

          <div className="flex items-center justify-between border-t border-border/70 pt-2 text-[11px]">
            <span className="text-muted-foreground">
              {k.actions.length} action{k.actions.length === 1 ? "" : "s"}
            </span>
            <span className="flex items-center gap-1 font-semibold text-primary group-hover:translate-x-0.5 transition-transform">
              Review <ArrowRight className="size-3" />
            </span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

export default async function AutomationsPage() {
  const session = await getSession();
  if (!canUseAutomations(session)) {
    return (
      <div className="mx-auto flex w-full max-w-lg flex-col items-center gap-3 p-6 pt-24 text-center">
        <ShieldAlert className="size-8 text-muted-foreground opacity-60" />
        <h1 className="text-lg font-bold text-foreground">Administrators &amp; Data Managers only</h1>
        <p className="text-sm text-muted-foreground">
          Job status, settings, and LLM cost are restricted here. Your Today queue and Review Queue are
          still yours - use the sidebar.
        </p>
        <Link href="/automations/today" className="text-xs font-semibold text-primary hover:underline">
          Go to your Today queue
        </Link>
      </div>
    );
  }

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
  const publications = Object.keys(SOURCE_LABELS).filter((p) => p !== "manual");

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 p-4 sm:p-6 lg:p-8">
      {/* Executive Header */}
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/80 pb-5">
        <div>
          <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
            <Sparkles className="size-3.5" />
            <span>Automations Suite · Intelligent Workflows</span>
          </div>
          <h1 className="editorial-title text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            Automations Hub
          </h1>
          <p className="mt-1 max-w-2xl text-xs text-muted-foreground sm:text-sm">
            Intelligent background agents drafting actions for sales acceleration, inbound lead capture,
            and CRM data hygiene.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link href="/automations/today">
            <Button variant="outline" size="sm" className="gap-1.5 font-semibold">
              <CalendarClock className="size-3.5 text-primary" />
              Today
            </Button>
          </Link>
          <Link href="/automations/settings">
            <Button variant="outline" size="sm" className="gap-1.5 font-semibold">
              <Settings2 className="size-3.5" />
              Settings
            </Button>
          </Link>
          <Link href="/automations/review">
            <Button
              variant={totalPending > 0 ? "default" : "outline"}
              size="sm"
              className="gap-1.5 font-semibold"
            >
              <ClipboardCheck className="size-3.5" />
              {totalPending.toLocaleString()} waiting for review
              <ArrowRight className="size-3.5" />
            </Button>
          </Link>
        </div>
      </div>

      {/* Guaranteed Human Review Trust Banner */}
      <Card className="editorial-card relative overflow-hidden border-primary/20 bg-gradient-to-br from-primary/[0.06] via-transparent to-transparent">
        <div className="absolute -right-10 -top-10 size-40 rounded-full bg-primary/10 blur-3xl" aria-hidden="true" />
        <CardContent className="relative flex flex-wrap items-center justify-between gap-4 p-5">
          <div className="flex items-center gap-3.5">
            <div className="flex size-11 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
              <ShieldCheck className="size-5" />
            </div>
            <div>
              <p className="text-sm font-bold text-foreground">Guaranteed Human Review</p>
              <p className="text-xs text-muted-foreground">
                Every automated suggestion is staged for your approval. Nothing is updated, merged, or sent
                without your confirmation.
              </p>
            </div>
          </div>
          {totalPending > 0 && (
            <Link href="/automations/review">
              <Button size="sm" className="shrink-0 gap-1.5 font-semibold">
                Start Reviewing ({totalPending})
                <ArrowRight className="size-3.5" />
              </Button>
            </Link>
          )}
        </CardContent>
      </Card>

      {/* KPI Strip */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="editorial-card h-full overflow-hidden transition-all hover:shadow-xs">
          <div className="h-1 w-full bg-gradient-to-r from-amber-600 to-amber-700" />
          <CardContent className="flex items-center justify-between p-6">
            <div>
              <div className="editorial-stat font-serif text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                {totalPending.toLocaleString()}
              </div>
              <div className="mt-1 text-sm font-bold text-foreground">Waiting for review</div>
              <div className="text-xs text-muted-foreground">Across all active automations</div>
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
              <div className="mt-1 text-sm font-bold text-foreground">Handled all-time</div>
              <div className="text-xs text-muted-foreground">Decisions confirmed by your team</div>
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
              <div className="mt-1 text-sm font-bold text-foreground">Active scanners</div>
              <div className="text-xs text-muted-foreground">Background mailbox &amp; CRM workers</div>
            </div>
            <span className="flex size-12 shrink-0 items-center justify-center rounded-xl border border-border bg-muted/60 text-blue-600 dark:text-blue-400">
              <Timer className="size-6" />
            </span>
          </CardContent>
        </Card>
      </div>

      {/* Each automation kind now appears in exactly one tab - previously
          "pending > 0" kinds were repeated in an Action Center tier AND
          their category tier AND (for business cards) a Photo Intake
          tier, which is what made the page feel duplicated and bloated.
          Progressive disclosure: pick a workstream, see only that
          workstream's automations. Business card capture gets its own
          dedicated tab (per BMI's ask) rather than being buried at the
          end of a long scroll. */}
      <Tabs defaultValue="sales" className="w-full">
        <div className="overflow-x-auto border-b border-border/80 bg-muted/30 px-1">
          <TabsList className="h-auto w-max gap-1 bg-transparent p-0 pt-1">
            {AUTOMATION_CATEGORIES.filter((cat) => cat.id !== "capture").map((cat) => (
              <TabsTrigger
                key={cat.id}
                value={cat.id}
                className="shrink-0 whitespace-nowrap rounded-t-md rounded-b-none border-b-2 border-transparent px-3.5 py-2 text-xs font-semibold data-[state=active]:border-primary data-[state=active]:bg-card"
              >
                {cat.label}
              </TabsTrigger>
            ))}
            <TabsTrigger
              value="capture"
              className="shrink-0 whitespace-nowrap rounded-t-md rounded-b-none border-b-2 border-transparent px-3.5 py-2 text-xs font-semibold data-[state=active]:border-primary data-[state=active]:bg-card"
            >
              Lead &amp; Contact Capture
            </TabsTrigger>
            <TabsTrigger
              value="business-cards"
              className="shrink-0 whitespace-nowrap rounded-t-md rounded-b-none border-b-2 border-transparent px-3.5 py-2 text-xs font-semibold data-[state=active]:border-primary data-[state=active]:bg-card"
            >
              Business Card &amp; Photo Capture
            </TabsTrigger>
            <TabsTrigger
              value="engine"
              className="shrink-0 whitespace-nowrap rounded-t-md rounded-b-none border-b-2 border-transparent px-3.5 py-2 text-xs font-semibold data-[state=active]:border-primary data-[state=active]:bg-card"
            >
              Scanners &amp; Settings
            </TabsTrigger>
          </TabsList>
        </div>

        {AUTOMATION_CATEGORIES.map((cat) => {
          const categoryKinds = kinds.filter(
            (k) => categoryForKind(k.kind) === cat.id && !BUSINESS_CARD_KINDS.has(k.kind)
          );
          const catPending = categoryKinds.reduce((sum, k) => sum + countFor(k.kind).pending, 0);

          return (
            <TabsContent key={cat.id} value={cat.id} className="mt-5 flex flex-col gap-3">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-2">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="editorial-heading text-base font-bold text-foreground">{cat.label}</h2>
                    <Badge variant="outline" className={`text-[10px] font-semibold ${cat.badgeColor}`}>
                      {categoryKinds.length} {categoryKinds.length === 1 ? "automation" : "automations"}
                    </Badge>
                    {catPending > 0 && (
                      <Badge variant="default" className="text-[10px] font-bold">
                        {catPending} pending
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">{cat.tagline}</p>
                </div>
              </div>

              {categoryKinds.length > 0 ? (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {categoryKinds.map((k) => (
                    <KindCard key={k.kind} k={k} c={countFor(k.kind)} />
                  ))}
                </div>
              ) : (
                <Card className="editorial-card border-dashed">
                  <CardContent className="flex flex-col items-center justify-center gap-2 py-8 text-center">
                    <CheckCircle2 className="size-6 text-muted-foreground opacity-50" />
                    <p className="text-xs text-muted-foreground">
                      No automations in this workstream yet.
                    </p>
                  </CardContent>
                </Card>
              )}
            </TabsContent>
          );
        })}

        {/* Business Card & Photo Capture - its own tab, not the tail end
            of a long page, so reps know exactly where to find it. */}
        <TabsContent value="business-cards" className="mt-5 flex flex-col gap-4">
          <div className="border-b border-border/60 pb-2">
            <h2 className="editorial-heading text-base font-bold text-foreground">
              Business Card &amp; Photo Capture
            </h2>
            <p className="text-xs text-muted-foreground">
              Photograph trade-show business cards or undeliverable magazine labels. Contact details
              are parsed, cross-referenced against 70,000+ records, and queued for confirmation.
            </p>
          </div>

          <Card className="editorial-card">
            <CardContent className="flex flex-wrap items-center justify-between gap-4 p-5">
              <div className="max-w-xl">
                <p className="text-xs font-medium text-foreground">
                  Instant AI optical recognition and deduplication
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Upload a photo to start - no scanner or desktop app required.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <PhotoUploadDialog kind="business-card" publications={publications} />
                <PhotoUploadDialog kind="returned-copy" publications={publications} />
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {kinds
              .filter((k) => BUSINESS_CARD_KINDS.has(k.kind))
              .map((k) => (
                <KindCard key={k.kind} k={k} c={countFor(k.kind)} />
              ))}
          </div>
        </TabsContent>

        {/* Scanners & Settings - engine/job status, not an automation
            queue, kept out of the workstream tabs above. */}
        <TabsContent value="engine" className="mt-5 flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-2">
            <div>
              <h2 className="editorial-heading text-base font-bold text-foreground">
                Automations Engine &amp; Background Scanners
              </h2>
              <p className="text-xs text-muted-foreground">
                Scheduled background workers that discover inbound emails, bounces, and calendar
                triggers.
              </p>
            </div>
            <Badge variant="outline" className="text-xs font-semibold">
              {jobsLive} of {jobs.length} Active
            </Badge>
          </div>

          <Card className="editorial-card">
            <CardContent className="flex flex-col divide-y divide-border/70 p-0">
              {jobs.map((j) => (
                <div key={j.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
                  <div className="flex items-center gap-3">
                    <span
                      className={`flex size-8 shrink-0 items-center justify-center rounded-lg border ${
                        j.enabled
                          ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-600"
                          : "border-border bg-muted/60 text-muted-foreground"
                      }`}
                    >
                      <Power className="size-3.5" />
                    </span>
                    <div>
                      <div className="text-xs font-bold text-foreground">{j.label}</div>
                      <div className="text-[11px] text-muted-foreground">{j.description}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
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
                      {j.enabled ? "ACTIVE" : "STANDBY"}
                    </Badge>
                    <RunJobButton jobId={j.id} hasCursor={j.has_cursor} />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
