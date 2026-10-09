import Link from "next/link";
import { CalendarDays, ChevronRight, MonitorSmartphone, Newspaper, Trophy, type LucideIcon } from "lucide-react";
import type { OrderStatus, ProductLine } from "@/lib/sales-types";
import { InfoHint } from "@/components/sales/info-hint";

export const MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** £ with thousands separators; `compact` for tiles ("£1.74m", "£215k"). */
export function fmtGBP(n: number | null | undefined, opts: { compact?: boolean } = {}): string {
  if (n === null || n === undefined) return "—";
  const sign = n < 0 ? "-" : "";
  const a = Math.abs(n);
  if (opts.compact) {
    if (a >= 1_000_000) return `${sign}£${(a / 1_000_000).toFixed(a >= 10_000_000 ? 1 : 2)}m`;
    if (a >= 10_000) return `${sign}£${Math.round(a / 1000)}k`;
    if (a >= 1000) return `${sign}£${(a / 1000).toFixed(1)}k`;
  }
  return `${sign}£${a.toLocaleString("en-GB", { minimumFractionDigits: a % 1 ? 2 : 0, maximumFractionDigits: 2 })}`;
}

export function fmtDate(iso: string | null | undefined, withYear = true): string {
  if (!iso) return "—";
  return new Date(iso + (iso.length === 10 ? "T00:00:00" : "")).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    ...(withYear ? { year: "numeric" } : {}),
  });
}

export function pct(part: number, whole: number): number | null {
  return whole > 0 ? part / whole : null;
}

const LINE_ICON: Record<ProductLine, LucideIcon> = {
  print: Newspaper,
  digital: MonitorSmartphone,
  events: CalendarDays,
  awards: Trophy,
};

export function TitleIcon({ line, className = "size-4" }: { line: ProductLine; className?: string }) {
  const Icon = LINE_ICON[line] ?? Newspaper;
  return <Icon className={className} aria-hidden="true" />;
}

export const PRODUCT_LINE_LABEL: Record<ProductLine, string> = {
  print: "Print",
  digital: "Digital",
  events: "Events",
  awards: "Awards",
};

/** Breadcrumb + title + description + actions - the Sales Orders twin of
 * the Automations Hub's HubHeader, so both sections read as one app. */
export function SalesHeader({
  title,
  description,
  crumbs = [],
  actions,
  eyebrow,
}: {
  title: string;
  description?: React.ReactNode;
  crumbs?: { label: string; href: string }[];
  actions?: React.ReactNode;
  eyebrow?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/80 pb-5">
      <div className="min-w-0">
        <nav aria-label="Breadcrumb" className="mb-1.5 flex flex-wrap items-center gap-1 text-xs font-semibold text-muted-foreground">
          {crumbs.length === 0 ? (
            <span className="uppercase tracking-wider text-primary">Sales Orders</span>
          ) : (
            <>
              {crumbs.map((c) => (
                <span key={c.href} className="flex items-center gap-1">
                  <Link href={c.href} className="hover:text-foreground">
                    {c.label}
                  </Link>
                  <ChevronRight className="size-3.5" aria-hidden="true" />
                </span>
              ))}
              <span className="text-foreground" aria-current="page">
                {title}
              </span>
            </>
          )}
        </nav>
        <h1 className="editorial-title text-2xl font-bold tracking-tight text-foreground sm:text-3xl">{title}</h1>
        {eyebrow && <div className="mt-1">{eyebrow}</div>}
        {description && <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

/** Section heading with an optional (i) hint and right-side slot. */
export function SectionTitle({
  id,
  children,
  hint,
  aside,
}: {
  id?: string;
  children: React.ReactNode;
  hint?: React.ReactNode;
  aside?: React.ReactNode;
}) {
  return (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
      <h2 id={id} className="flex items-center gap-1.5 text-sm font-bold text-foreground">
        {children}
        {hint && <InfoHint>{hint}</InfoHint>}
      </h2>
      {aside}
    </div>
  );
}

/** Year segmented control - links, so the choice is shareable/bookmarkable. */
export function YearSwitch({
  years,
  current,
  href,
}: {
  years: number[];
  current: number;
  href: (year: number) => string;
}) {
  const shown = years.slice(0, 4);
  return (
    <div role="group" aria-label="Year" className="flex items-center gap-0.5 rounded-lg border border-border/80 bg-card p-0.5">
      {shown.map((y) => {
        const active = y === current;
        return (
          <Link
            key={y}
            href={href(y)}
            scroll={false}
            aria-current={active ? "true" : undefined}
            className={`rounded-md px-3 py-1.5 text-xs font-semibold tabular-nums transition-colors focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring ${
              active ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
          >
            {y}
          </Link>
        );
      })}
    </div>
  );
}

const STATUS_STYLE: Record<OrderStatus, { label: string; color: string }> = {
  booked: { label: "Booked", color: "var(--ok)" },
  cancelled: { label: "Cancelled", color: "var(--bad)" },
  contra: { label: "Contra", color: "var(--chart-4)" },
  moved: { label: "Moved", color: "var(--muted-foreground)" },
  pencilled: { label: "Pencilled", color: "var(--warn)" },
};

export function OrderStatusPill({ status }: { status: OrderStatus }) {
  const s = STATUS_STYLE[status];
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold"
      style={{ color: s.color, borderColor: `color-mix(in oklab, ${s.color} 35%, transparent)` }}
    >
      <span className="size-1.5 rounded-full" style={{ background: s.color }} aria-hidden="true" />
      {s.label}
    </span>
  );
}

/** "This vs same point last year" as a thin two-layer bar: the solid bar
 * is this year, the tick is where last year was by now. */
export function PaceBar({ value, compare, max }: { value: number; compare: number | null; max: number }) {
  const w = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  const c = compare !== null && max > 0 ? Math.min(100, (compare / max) * 100) : null;
  const ahead = compare === null || value >= compare;
  return (
    <div className="relative h-2 w-full rounded-full bg-muted" aria-hidden="true">
      <div
        className="absolute inset-y-0 left-0 rounded-full"
        style={{ width: `${w}%`, background: ahead ? "var(--chart-2)" : "var(--warn)" }}
      />
      {c !== null && (
        <div className="absolute -top-0.5 h-3 w-0.5 rounded-full bg-foreground/70" style={{ left: `calc(${c}% - 1px)` }} />
      )}
    </div>
  );
}

export function EmptyState({ icon: Icon, title, children }: { icon: LucideIcon; title: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border/80 bg-card/50 px-6 py-12 text-center">
      <Icon className="size-7 text-muted-foreground/60" aria-hidden="true" />
      <div className="text-sm font-semibold text-foreground">{title}</div>
      {children && <div className="max-w-md text-xs text-muted-foreground">{children}</div>}
    </div>
  );
}
