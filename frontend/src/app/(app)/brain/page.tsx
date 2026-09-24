import Link from "next/link";
import {
  ArrowRight,
  BrainCircuit,
  Building2,
  CheckCircle2,
  ClipboardCheck,
  HeartPulse,
  ShieldAlert,
  Sparkles,
  Timer,
  Users,
} from "lucide-react";
import { backendFetch } from "@/lib/backend";
import {
  AUTOMATION_CATEGORIES,
  categoryForKind,
  styleForKind,
} from "@/lib/automation-style";
import { canUseAutomations } from "@/lib/access";
import { getSession } from "@/lib/session";
import { getPublicationFilter } from "@/lib/publication";
import type {
  DashboardStats,
  DataHealthStats,
  Page,
  ReviewKind,
  ReviewQueueCounts,
  ReviewQueueItem,
  ScheduledJob,
} from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const mins = Math.round(ms / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

export default async function BrainDashboardPage() {
  const session = await getSession();
  if (!canUseAutomations(session)) {
    return (
      <div className="mx-auto flex w-full max-w-lg flex-col items-center gap-3 p-6 pt-24 text-center">
        <ShieldAlert className="size-8 text-muted-foreground opacity-60" aria-hidden="true" />
        <h1 className="text-lg font-bold text-foreground">Administrators &amp; Data Managers only</h1>
        <p className="text-sm text-muted-foreground">
          This is the cross-team command center - your own Today queue is still under the sidebar.
        </p>
        <Link href="/automations/today" className="text-xs font-semibold text-primary hover:underline">
          Go to your Today queue
        </Link>
      </div>
    );
  }

  const sourceDb = await getPublicationFilter();
  const statsParams = new URLSearchParams();
  if (sourceDb) statsParams.set("source_db", sourceDb);

  const [stats, health, kinds, counts, jobs, pendingPage, approvedPage, rejectedPage] = await Promise.all([
    backendFetch<DashboardStats>(`/api/dashboard/stats${statsParams.size ? `?${statsParams}` : ""}`),
    backendFetch<DataHealthStats>(`/api/dashboard/data-health${statsParams.size ? `?${statsParams}` : ""}`),
    backendFetch<ReviewKind[]>("/api/review-queue/kinds"),
    backendFetch<ReviewQueueCounts[]>("/api/review-queue/counts"),
    backendFetch<ScheduledJob[]>("/api/automations/jobs"),
    backendFetch<Page<ReviewQueueItem>>("/api/review-queue?status=pending&sort=recent&page_size=5"),
    backendFetch<Page<ReviewQueueItem>>("/api/review-queue?status=approved&sort=recent&page_size=5"),
    backendFetch<Page<ReviewQueueItem>>("/api/review-queue?status=rejected&sort=recent&page_size=5"),
  ]);

  const countFor = (k: string) => counts.find((c) => c.kind === k) ?? { kind: k, pending: 0, approved: 0, rejected: 0 };
  const totalPending = counts.reduce((sum, c) => sum + c.pending, 0);
  const totalHandled = counts.reduce((sum, c) => sum + c.approved + c.rejected, 0);
  const jobsLive = jobs.filter((j) => j.enabled).length;
  const cleanMetrics = health.metrics.filter((m) => m.count === 0).length;
  const openIssues = health.metrics.reduce((sum, m) => sum + m.count, 0);

  const recentActivity = [...approvedPage.items, ...rejectedPage.items]
    .sort((a, b) => new Date(b.reviewed_at ?? 0).getTime() - new Date(a.reviewed_at ?? 0).getTime())
    .slice(0, 5);

  const KPIS = [
    {
      label: "Records under management",
      value: stats.total_contacts + stats.total_companies,
      sublabel: `${stats.total_contacts.toLocaleString()} contacts · ${stats.total_companies.toLocaleString()} companies`,
      icon: Users,
      color: "text-chart-1",
      accent: "bg-chart-1",
    },
    {
      label: "Waiting for review",
      value: totalPending,
      sublabel: "Across every automation",
      icon: ClipboardCheck,
      color: "text-chart-2",
      accent: "bg-chart-2",
      href: "/automations/review",
    },
    {
      label: "Handled all-time",
      value: totalHandled,
      sublabel: "Decisions confirmed by your team",
      icon: CheckCircle2,
      color: "text-chart-3",
      accent: "bg-chart-3",
    },
    {
      label: "Active scanners",
      value: jobsLive,
      valueSuffix: `/${jobs.length}`,
      sublabel: "Background mailbox & CRM workers",
      icon: Timer,
      color: "text-chart-4",
      accent: "bg-chart-4",
      href: "/automations",
    },
    {
      label: "Data health",
      value: cleanMetrics,
      valueSuffix: `/${health.metrics.length} clean`,
      sublabel: openIssues > 0 ? `${openIssues.toLocaleString()} open issues` : "Everything under control",
      icon: HeartPulse,
      color: "text-chart-5",
      accent: "bg-chart-5",
      href: "/data-health",
    },
  ];

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 p-4 sm:p-6 lg:p-8">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/80 pb-5">
        <div>
          <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
            <BrainCircuit className="size-3.5" aria-hidden="true" />
            <span>BMI Brain</span>
          </div>
          <h1 className="editorial-title text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            Command Center
          </h1>
          <p className="mt-1 max-w-2xl text-xs text-muted-foreground sm:text-sm">
            Automation throughput, data health, and CRM scale in one place. Pipeline &amp; revenue KPIs
            join once the Sales Order Register data is wired in - everything here runs off what the CRM
            already tracks today.
          </p>
        </div>
      </div>

      {/* KPI Strip */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {KPIS.map((k) => {
          const tile = (
            <Card className="editorial-card h-full overflow-hidden transition-all hover:border-primary/50 hover:shadow-xs">
              <div className={`masthead-rule w-full ${k.accent}`} />
              <CardContent className="flex flex-col gap-3 p-5">
                <span className={`brand-icon size-9 shrink-0 ${k.color}`} aria-hidden="true">
                  <k.icon className="size-4.5" />
                </span>
                <div>
                  <div className="editorial-stat text-2xl font-serif font-bold text-foreground tracking-tight">
                    {k.value.toLocaleString()}
                    {k.valueSuffix && <span className="text-base text-muted-foreground">{k.valueSuffix}</span>}
                  </div>
                  <div className="mt-0.5 text-xs font-bold text-foreground">{k.label}</div>
                  <div className="text-[11px] text-muted-foreground">{k.sublabel}</div>
                </div>
              </CardContent>
            </Card>
          );
          return k.href ? (
            <Link key={k.label} href={k.href} className="group">
              {tile}
            </Link>
          ) : (
            <div key={k.label}>{tile}</div>
          );
        })}
      </div>

      {/* Workstream breakdown */}
      <div>
        <div className="mb-3">
          <h2 className="editorial-heading text-base font-bold text-foreground">Workstreams</h2>
          <p className="text-xs text-muted-foreground">
            Pending review items by business objective - open a workstream in the Automations Hub.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          {AUTOMATION_CATEGORIES.map((cat) => {
            const categoryKinds = kinds.filter((k) => categoryForKind(k.kind) === cat.id);
            const catPending = categoryKinds.reduce((sum, k) => sum + countFor(k.kind).pending, 0);
            return (
              <Link key={cat.id} href={`/automations?tab=${cat.id}`} className="group block">
                <Card className="editorial-card h-full transition-all hover:border-primary/50 hover:shadow-xs">
                  <CardContent className="flex flex-col gap-2 p-5">
                    <div className="flex items-center justify-between">
                      <Badge variant="outline" className={`text-[10px] font-semibold ${cat.badgeColor}`}>
                        {categoryKinds.length} {categoryKinds.length === 1 ? "automation" : "automations"}
                      </Badge>
                      {catPending > 0 && (
                        <Badge variant="default" className="text-[10px] font-bold">
                          {catPending} pending
                        </Badge>
                      )}
                    </div>
                    <div className="text-sm font-bold text-foreground group-hover:text-primary transition-colors">
                      {cat.label}
                    </div>
                    <p className="text-xs text-muted-foreground">{cat.tagline}</p>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Activity feed */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="editorial-card">
          <CardHeader className="flex flex-row items-center justify-between border-b pb-3">
            <CardTitle className="flex items-center gap-1.5 text-sm font-bold text-foreground">
              <ClipboardCheck className="size-4 text-amber-600" aria-hidden="true" />
              New for review
            </CardTitle>
            <Link href="/automations/review" className="text-xs font-semibold text-primary hover:underline">
              View all &rarr;
            </Link>
          </CardHeader>
          <CardContent className="flex flex-col gap-1 p-3">
            {pendingPage.items.length > 0 ? (
              pendingPage.items.map((item) => {
                const style = styleForKind(item.kind);
                const Icon = style.icon;
                return (
                  <Link
                    key={item.id}
                    href={`/automations/review?kind=${item.kind}`}
                    className="flex items-center gap-3 rounded-lg p-2.5 transition-colors hover:bg-accent/50"
                  >
                    <span className={`brand-icon size-9 shrink-0 ${style.chipBg} ${style.color}`} aria-hidden="true">
                      <Icon className="size-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-xs font-bold text-foreground">
                        {item.payload.summary || "New item"}
                      </div>
                      <div className="truncate text-[11px] text-muted-foreground">
                        {item.kind.replace(/_/g, " ")}
                      </div>
                    </div>
                    <span className="shrink-0 text-[11px] font-medium text-muted-foreground">
                      {timeAgo(item.created_at)}
                    </span>
                  </Link>
                );
              })
            ) : (
              <span className="p-4 text-xs text-muted-foreground">Nothing waiting for review.</span>
            )}
          </CardContent>
        </Card>

        <Card className="editorial-card">
          <CardHeader className="flex flex-row items-center justify-between border-b pb-3">
            <CardTitle className="flex items-center gap-1.5 text-sm font-bold text-foreground">
              <CheckCircle2 className="size-4 text-emerald-600" aria-hidden="true" />
              Recently resolved
            </CardTitle>
            <Link href="/data-health" className="text-xs font-semibold text-primary hover:underline">
              Data health &rarr;
            </Link>
          </CardHeader>
          <CardContent className="flex flex-col gap-1 p-3">
            {recentActivity.length > 0 ? (
              recentActivity.map((item) => {
                const style = styleForKind(item.kind);
                const Icon = style.icon;
                return (
                  <Link
                    key={item.id}
                    href={`/automations/review?kind=${item.kind}&status=${item.status}`}
                    className="flex items-center gap-3 rounded-lg p-2.5 transition-colors hover:bg-accent/50"
                  >
                    <span className={`brand-icon size-9 shrink-0 ${style.chipBg} ${style.color}`} aria-hidden="true">
                      <Icon className="size-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-xs font-bold text-foreground">
                        {item.payload.summary || "Resolved item"}
                      </div>
                      <div className="truncate text-[11px] text-muted-foreground">
                        {item.status === "approved" ? "Approved" : "Rejected"} &middot; {item.kind.replace(/_/g, " ")}
                      </div>
                    </div>
                    <span className="shrink-0 text-[11px] font-medium text-muted-foreground">
                      {item.reviewed_at ? timeAgo(item.reviewed_at) : ""}
                    </span>
                  </Link>
                );
              })
            ) : (
              <span className="p-4 text-xs text-muted-foreground">Nothing resolved yet.</span>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="editorial-card border-dashed">
        <CardContent className="flex flex-wrap items-center justify-between gap-3 p-5">
          <div className="flex items-center gap-3">
            <span className="brand-icon size-9 shrink-0 text-primary" aria-hidden="true">
              <Building2 className="size-4" />
            </span>
            <div>
              <p className="text-xs font-bold text-foreground">Pipeline &amp; revenue KPIs are next</p>
              <p className="text-xs text-muted-foreground">
                Advertiser bookings, renewal windows, and revenue-by-title need the Sales Order Register
                data - scoped separately, not yet wired in.
              </p>
            </div>
          </div>
          <span className="flex items-center gap-1 text-xs font-semibold text-muted-foreground">
            <Sparkles className="size-3.5" aria-hidden="true" />
            Backlog
          </span>
        </CardContent>
      </Card>
    </div>
  );
}
