import Link from "next/link";
import { AlertTriangle, ArrowRight, HeartPulse, ShieldAlert, ShieldCheck } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { DataHealthMetric, DataHealthStats } from "@/lib/types";
import { canUseAutomations } from "@/lib/access";
import { getSession } from "@/lib/session";
import { getPublicationFilter } from "@/lib/publication";
import { styleForKind } from "@/lib/automation-style";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

/** A metric is "healthy" once its share of the total drops under this -
 * zero is an unrealistic bar for a 70,000+ record CRM migrated from Act!,
 * so this marks "under control" rather than "perfect". */
const HEALTHY_THRESHOLD = 0.02;

function severity(count: number, total: number): "good" | "warn" | "bad" {
  if (count === 0) return "good";
  if (total === 0) return "warn";
  const ratio = count / total;
  if (ratio < HEALTHY_THRESHOLD) return "warn";
  return "bad";
}

const SEVERITY_STYLE: Record<
  "good" | "warn" | "bad",
  { badge: string; bar: string; icon: typeof ShieldCheck }
> = {
  good: { badge: "border-emerald-500/30 bg-emerald-500/10 text-emerald-600", bar: "bg-emerald-500", icon: ShieldCheck },
  warn: { badge: "border-amber-500/30 bg-amber-500/10 text-amber-600", bar: "bg-amber-500", icon: AlertTriangle },
  bad: { badge: "border-red-500/30 bg-red-500/10 text-red-600", bar: "bg-red-500", icon: ShieldAlert },
};

function MetricRow({ metric }: { metric: DataHealthMetric }) {
  const pct = metric.total > 0 ? Math.round((metric.count / metric.total) * 1000) / 10 : 0;
  const level = severity(metric.count, metric.total);
  const { badge, bar, icon: SeverityIcon } = SEVERITY_STYLE[level];
  const kindStyle = metric.review_kind ? styleForKind(metric.review_kind) : null;
  const Icon = kindStyle?.icon ?? SeverityIcon;
  const href = metric.review_kind
    ? `/automations/review?kind=${metric.review_kind}`
    : metric.entity_type === "company"
      ? "/companies"
      : "/contacts";

  return (
    <div className="flex flex-col gap-2.5 border-b border-border/60 p-4 last:border-b-0 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 items-start gap-3">
        <span
          className={`brand-icon size-9 shrink-0 ${kindStyle ? `${kindStyle.chipBg} ${kindStyle.color}` : badge}`}
          aria-hidden="true"
        >
          <Icon className="size-4" />
        </span>
        <div className="min-w-0">
          <div className="text-xs font-bold text-foreground">{metric.label}</div>
          <p className="mt-0.5 text-xs text-muted-foreground">{metric.description}</p>
          <div className="mt-1.5 h-1.5 w-full max-w-xs overflow-hidden rounded-full bg-muted">
            <div className={`h-full rounded-full ${bar}`} style={{ width: `${Math.min(pct, 100)}%` }} />
          </div>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-3 pl-12 sm:pl-0">
        <div className="text-right">
          <div className="text-lg font-bold text-foreground">{metric.count.toLocaleString()}</div>
          <div className="text-[10.5px] text-muted-foreground">
            {metric.total > 0 ? `${pct}% of ${metric.total.toLocaleString()}` : "—"}
          </div>
        </div>
        <Badge variant="outline" className={`text-[10px] font-bold ${badge}`}>
          {level === "good" ? "Clean" : level === "warn" ? "Watch" : "Needs attention"}
        </Badge>
        {metric.count > 0 && (
          <Link
            href={href}
            className="flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
          >
            Fix <ArrowRight className="size-3.5" />
          </Link>
        )}
      </div>
    </div>
  );
}

export default async function DataHealthPage() {
  const session = await getSession();
  if (!canUseAutomations(session)) {
    return (
      <div className="mx-auto flex w-full max-w-lg flex-col items-center gap-3 p-6 pt-24 text-center">
        <ShieldAlert className="size-8 text-muted-foreground opacity-60" aria-hidden="true" />
        <h1 className="text-lg font-bold text-foreground">Administrators &amp; Data Managers only</h1>
        <p className="text-sm text-muted-foreground">
          Record-quality figures across every publication aren&apos;t scoped per rep the way the
          review queue is.
        </p>
      </div>
    );
  }

  const sourceDb = await getPublicationFilter();
  const params = new URLSearchParams();
  if (sourceDb) params.set("source_db", sourceDb);

  const health = await backendFetch<DataHealthStats>(
    `/api/dashboard/data-health${params.size ? `?${params}` : ""}`
  );

  const completeness = health.metrics.filter((m) => !m.review_kind);
  const automationHygiene = health.metrics.filter((m) => m.review_kind);
  const totalIssues = health.metrics.reduce((sum, m) => sum + m.count, 0);
  const worst = health.metrics.reduce<DataHealthMetric | null>(
    (acc, m) => (!acc || m.count > acc.count ? m : acc),
    null
  );

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 p-4 sm:p-6 lg:p-8">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/80 pb-5">
        <div>
          <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
            <HeartPulse className="size-3.5" aria-hidden="true" />
            <span>BMI Brain · Data Health</span>
          </div>
          <h1 className="editorial-title text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            Data Health
          </h1>
          <p className="mt-1 max-w-2xl text-xs text-muted-foreground sm:text-sm">
            Record completeness across {health.total_contacts.toLocaleString()} contacts and{" "}
            {health.total_companies.toLocaleString()} companies, plus every hygiene automation&apos;s
            backlog - one place to see what&apos;s dragging on data quality and jump straight to fixing it.
          </p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="editorial-card h-full overflow-hidden">
          <div className="h-1 w-full bg-chart-1" />
          <CardContent className="p-6">
            <div className="editorial-stat font-serif text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              {totalIssues.toLocaleString()}
            </div>
            <div className="mt-1 text-sm font-bold text-foreground">Open issues</div>
            <div className="text-xs text-muted-foreground">Across every completeness &amp; hygiene metric</div>
          </CardContent>
        </Card>
        <Card className="editorial-card h-full overflow-hidden">
          <div className="h-1 w-full bg-chart-2" />
          <CardContent className="p-6">
            <div className="editorial-stat font-serif text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              {health.metrics.filter((m) => severity(m.count, m.total) === "good").length}
              <span className="text-lg text-muted-foreground">/{health.metrics.length}</span>
            </div>
            <div className="mt-1 text-sm font-bold text-foreground">Metrics clean</div>
            <div className="text-xs text-muted-foreground">No open issues at all</div>
          </CardContent>
        </Card>
        <Card className="editorial-card h-full overflow-hidden">
          <div className="h-1 w-full bg-chart-3" />
          <CardContent className="p-6">
            <div className="line-clamp-2 text-base font-bold text-foreground sm:text-lg">
              {worst && worst.count > 0 ? worst.label : "Nothing outstanding"}
            </div>
            <div className="mt-1 text-sm font-bold text-foreground">
              {worst && worst.count > 0 ? `${worst.count.toLocaleString()} affected` : "All clear"}
            </div>
            <div className="text-xs text-muted-foreground">Biggest single issue right now</div>
          </CardContent>
        </Card>
      </div>

      <div>
        <div className="mb-3">
          <h2 className="editorial-heading text-base font-bold text-foreground">Record completeness</h2>
          <p className="text-xs text-muted-foreground">
            Fields missing from contacts and companies that other features (outreach, segmentation,
            bounce detection) depend on.
          </p>
        </div>
        <Card className="editorial-card overflow-hidden">
          <CardContent className="flex flex-col p-0">
            {completeness.map((m) => (
              <MetricRow key={m.key} metric={m} />
            ))}
          </CardContent>
        </Card>
      </div>

      <div>
        <div className="mb-3">
          <h2 className="editorial-heading text-base font-bold text-foreground">Automation hygiene backlog</h2>
          <p className="text-xs text-muted-foreground">
            Pending items from the automations engine that exist specifically to keep the CRM clean -
            duplicates, bounces, unconfirmed departures.
          </p>
        </div>
        <Card className="editorial-card overflow-hidden">
          <CardContent className="flex flex-col p-0">
            {automationHygiene.map((m) => (
              <MetricRow key={m.key} metric={m} />
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
