/** Hand-drawn SVG charts for the Automations Hub - no chart library, so
 * they render on the server with the page and cost nothing extra to load.
 * Colours come from theme variables, so all three themes work. */

const NEW_COLOR = "var(--chart-2)";
const RESOLVED_COLOR = "var(--ok)";
const BACKLOG_COLOR = "var(--chart-1)";

/** Tiny trend line for a table cell. Decorative - the number next to it
 * carries the meaning, so it's hidden from screen readers. */
export function Sparkline({
  values,
  className = "",
  color = NEW_COLOR,
}: {
  values: number[];
  className?: string;
  color?: string;
}) {
  const w = 80;
  const h = 22;
  const max = Math.max(...values, 1);
  const step = values.length > 1 ? w / (values.length - 1) : w;
  const points = values.map((v, i) => `${(i * step).toFixed(1)},${(h - 2 - (v / max) * (h - 4)).toFixed(1)}`).join(" ");
  const allZero = values.every((v) => v === 0);
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className={`h-[22px] w-20 ${className}`} aria-hidden="true">
      <polyline
        points={points}
        fill="none"
        stroke={allZero ? "var(--border)" : color}
        strokeWidth={1.75}
        strokeLinejoin="round"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

type DayPoint = { date: string; new: number; resolved: number; backlog: number };

function shortDate(iso: string): string {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
}

/** New vs Resolved per day (bars, left scale) with the pending backlog at
 * the end of each day (line, right scale - backlog is usually far larger
 * than any one day's flow, so it gets its own axis). Hovering a day shows
 * its exact numbers via the native tooltip. */
export function NewResolvedChart({ points }: { points: DayPoint[] }) {
  const W = 800;
  const H = 220;
  const pad = { top: 12, right: 44, bottom: 26, left: 36 };
  const iw = W - pad.left - pad.right;
  const ih = H - pad.top - pad.bottom;

  const barMax = Math.max(...points.flatMap((p) => [p.new, p.resolved]), 1);
  const backlogMax = Math.max(...points.map((p) => p.backlog), 1);
  const niceMax = (m: number) => {
    const mag = 10 ** Math.floor(Math.log10(m));
    return Math.ceil(m / mag) * mag;
  };
  const yMax = niceMax(barMax);
  const bMax = niceMax(backlogMax);

  const slot = iw / points.length;
  const groupW = Math.min(slot * 0.72, 36);
  const barW = points.length > 45 ? groupW / 2 : Math.max(groupW / 2 - 1, 1);
  const y = (v: number) => pad.top + ih - (v / yMax) * ih;
  const yb = (v: number) => pad.top + ih - (v / bMax) * ih;
  const cx = (i: number) => pad.left + slot * i + slot / 2;

  const labelEvery = Math.ceil(points.length / 7);
  const backlogPath = points.map((p, i) => `${i === 0 ? "M" : "L"}${cx(i).toFixed(1)},${yb(p.backlog).toFixed(1)}`).join(" ");

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" aria-hidden="true">
      {[0, 0.5, 1].map((f) => (
        <g key={f}>
          <line x1={pad.left} x2={W - pad.right} y1={y(yMax * f)} y2={y(yMax * f)} stroke="var(--border)" strokeDasharray={f === 0 ? undefined : "3 4"} />
          <text x={pad.left - 8} y={y(yMax * f) + 4} textAnchor="end" fontSize={11} fill="var(--muted-foreground)">
            {Math.round(yMax * f).toLocaleString("en-GB")}
          </text>
          <text x={W - pad.right + 8} y={yb(bMax * f) + 4} textAnchor="start" fontSize={11} fill="var(--muted-foreground)">
            {Math.round(bMax * f).toLocaleString("en-GB")}
          </text>
        </g>
      ))}

      {points.map((p, i) => (
        <g key={p.date}>
          <title>{`${shortDate(p.date)}: ${p.new} new, ${p.resolved} resolved, ${p.backlog} pending at end of day`}</title>
          {/* full-height hit area so the tooltip works even on a 0 day */}
          <rect x={pad.left + slot * i} y={pad.top} width={slot} height={ih} fill="transparent" />
          <rect x={cx(i) - barW - 0.5} y={y(p.new)} width={barW} height={Math.max(pad.top + ih - y(p.new), 0)} rx={1.5} fill={NEW_COLOR} />
          <rect x={cx(i) + 0.5} y={y(p.resolved)} width={barW} height={Math.max(pad.top + ih - y(p.resolved), 0)} rx={1.5} fill={RESOLVED_COLOR} />
          {i % labelEvery === 0 || i === points.length - 1 ? (
            <text x={cx(i)} y={H - 8} textAnchor="middle" fontSize={11} fill="var(--muted-foreground)">
              {shortDate(p.date)}
            </text>
          ) : null}
        </g>
      ))}

      <path d={backlogPath} fill="none" stroke={BACKLOG_COLOR} strokeWidth={2} strokeLinejoin="round" pointerEvents="none" />
      {points.length <= 31 &&
        points.map((p, i) => <circle key={p.date} cx={cx(i)} cy={yb(p.backlog)} r={2.5} fill={BACKLOG_COLOR} pointerEvents="none" />)}
    </svg>
  );
}

export function ChartLegend() {
  const item = (color: string, label: string, line = false) => (
    <span className="flex items-center gap-1.5">
      <span
        aria-hidden="true"
        className={line ? "h-0.5 w-4 rounded-full" : "size-2.5 rounded-sm"}
        style={{ background: color }}
      />
      {label}
    </span>
  );
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
      {item(NEW_COLOR, "New")}
      {item(RESOLVED_COLOR, "Resolved")}
      {item(BACKLOG_COLOR, "Pending backlog (right axis)", true)}
    </div>
  );
}
