import Link from "next/link";
import { ArrowDownRight, ArrowUpRight, ChevronRight, ShieldAlert } from "lucide-react";
import type { StatsRange } from "@/lib/types";

/** Breadcrumb + title + one-line description + right-side actions. The
 * same header on every Hub page, so moving between them feels like one
 * section rather than five different screens. */
export function HubHeader({
  title,
  description,
  crumb,
  actions,
}: {
  title: string;
  description: string;
  crumb?: boolean;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/80 pb-5">
      <div className="min-w-0">
        <nav aria-label="Breadcrumb" className="mb-1.5 flex items-center gap-1 text-xs font-semibold text-muted-foreground">
          {crumb ? (
            <>
              <Link href="/automations" className="hover:text-foreground">
                Automations Hub
              </Link>
              <ChevronRight className="size-3.5" aria-hidden="true" />
              <span className="text-foreground" aria-current="page">
                {title}
              </span>
            </>
          ) : (
            <span className="uppercase tracking-wider text-primary">BMI Brain</span>
          )}
        </nav>
        <h1 className="editorial-title text-2xl font-bold tracking-tight text-foreground sm:text-3xl">{title}</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{description}</p>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

const RANGES: { value: StatsRange; label: string }[] = [
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "all", label: "All time" },
];

/** Segmented control that drives every figure on the page. Plain links
 * (the URL is the state), so it works without JavaScript and survives a
 * refresh or a shared link. */
export function RangeSwitch({ basePath, current }: { basePath: string; current: StatsRange }) {
  return (
    <div role="group" aria-label="Date range" className="flex items-center gap-0.5 rounded-lg border border-border/80 bg-card p-0.5">
      {RANGES.map((r) => {
        const active = r.value === current;
        return (
          <Link
            key={r.value}
            href={r.value === "7d" ? basePath : `${basePath}?range=${r.value}`}
            aria-current={active ? "true" : undefined}
            scroll={false}
            className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring ${
              active ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
          >
            {r.label}
          </Link>
        );
      })}
    </div>
  );
}

export function parseRange(raw: string | undefined): StatsRange {
  return raw === "30d" || raw === "all" ? raw : "7d";
}

/** Delta chip. `goodWhenUp` decides the colour - more items resolved is
 * good (green), more new items is more work (amber), so a rising number
 * isn't automatically shown as good news. */
export function Delta({ change, goodWhenUp }: { change: number | null; goodWhenUp: boolean }) {
  if (change === null) return null;
  const pct = Math.round(change * 100);
  if (pct === 0) return <span className="text-xs font-medium text-muted-foreground">no change</span>;
  const up = pct > 0;
  const good = up === goodWhenUp;
  const Icon = up ? ArrowUpRight : ArrowDownRight;
  return (
    <span
      className="inline-flex items-center gap-0.5 text-xs font-semibold tabular-nums"
      style={{ color: good ? "var(--ok)" : "var(--warn)" }}
    >
      <Icon className="size-3.5" aria-hidden="true" />
      {Math.abs(pct)}%<span className="sr-only">{up ? " increase" : " decrease"} vs previous period</span>
    </span>
  );
}

export function KpiTile({
  label,
  value,
  footer,
  delta,
}: {
  label: string;
  value: React.ReactNode;
  footer?: React.ReactNode;
  delta?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col justify-between gap-2 rounded-xl border border-border/80 bg-card p-4 shadow-2xs">
      <div className="text-xs font-semibold text-muted-foreground">{label}</div>
      <div className="flex items-baseline gap-2">
        <div className="editorial-stat font-serif text-3xl font-bold tracking-tight text-foreground tabular-nums">{value}</div>
        {delta}
      </div>
      {footer && <div className="text-xs text-muted-foreground">{footer}</div>}
    </div>
  );
}

export function StaffOnly() {
  return (
    <div className="mx-auto flex w-full max-w-lg flex-col items-center gap-3 p-6 pt-24 text-center">
      <ShieldAlert className="size-8 text-muted-foreground opacity-60" aria-hidden="true" />
      <h1 className="text-lg font-bold text-foreground">Administrators &amp; Data Managers only</h1>
      <p className="text-sm text-muted-foreground">
        Automation stats and scanner controls are restricted. Your Today queue and Review Queue are still yours -
        use the sidebar.
      </p>
      <Link href="/automations/today" className="text-xs font-semibold text-primary hover:underline">
        Go to your Today queue
      </Link>
    </div>
  );
}
