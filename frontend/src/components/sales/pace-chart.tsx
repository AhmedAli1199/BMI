import { MONTHS_SHORT, fmtGBP } from "@/components/sales/sales-ui";

const THIS_COLOR = "var(--chart-2)";
const LAST_COLOR = "var(--muted-foreground)";

/** Cumulative booked value through the year: this year (solid, filled)
 * against last year (dashed). Reading where the solid line sits against
 * the dashed one is the fastest "are we ahead or behind" check there is -
 * much clearer than two sets of monthly bars. Months still to come this
 * year aren't drawn. Hovering a month shows its exact figures. */
export function PaceChart({
  monthly,
  currentMonth,
}: {
  monthly: { month: number; this_year: number; last_year: number }[];
  currentMonth: number | null; // 1-12 for the current year, null for a finished year
}) {
  const W = 800;
  const H = 240;
  const pad = { top: 14, right: 16, bottom: 26, left: 56 };
  const iw = W - pad.left - pad.right;
  const ih = H - pad.top - pad.bottom;

  const cum = monthly.map((m, i) => ({
    month: m.month,
    thisYear: monthly.slice(0, i + 1).reduce((s, x) => s + x.this_year, 0),
    lastYear: monthly.slice(0, i + 1).reduce((s, x) => s + x.last_year, 0),
    thisMonth: m.this_year,
  }));
  const lastIdx = currentMonth ? currentMonth - 1 : 11;
  const max = Math.max(...cum.map((c) => c.lastYear), ...cum.slice(0, lastIdx + 1).map((c) => c.thisYear), 1);
  const mag = 10 ** Math.floor(Math.log10(max));
  const yMax = Math.ceil(max / mag) * mag;

  const x = (i: number) => pad.left + (iw / 11) * i;
  const y = (v: number) => pad.top + ih - (v / yMax) * ih;
  const line = (pts: { i: number; v: number }[]) => pts.map((p, k) => `${k ? "L" : "M"}${x(p.i).toFixed(1)},${y(p.v).toFixed(1)}`).join(" ");
  const thisPts = cum.slice(0, lastIdx + 1).map((c, i) => ({ i, v: c.thisYear }));
  const lastPts = cum.map((c, i) => ({ i, v: c.lastYear }));
  const area = `${line(thisPts)} L${x(lastIdx).toFixed(1)},${y(0)} L${x(0).toFixed(1)},${y(0)} Z`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" aria-hidden="true">
      <defs>
        <linearGradient id="pace-fill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={THIS_COLOR} stopOpacity={0.22} />
          <stop offset="100%" stopColor={THIS_COLOR} stopOpacity={0.02} />
        </linearGradient>
      </defs>
      {[0, 0.25, 0.5, 0.75, 1].map((f) => (
        <g key={f}>
          <line x1={pad.left} x2={W - pad.right} y1={y(yMax * f)} y2={y(yMax * f)} stroke="var(--border)" strokeDasharray={f === 0 ? undefined : "3 4"} />
          <text x={pad.left - 8} y={y(yMax * f) + 4} textAnchor="end" fontSize={11} fill="var(--muted-foreground)">
            {fmtGBP(yMax * f, { compact: true })}
          </text>
        </g>
      ))}
      {cum.map((c, i) => (
        <text key={c.month} x={x(i)} y={H - 8} textAnchor="middle" fontSize={11} fill="var(--muted-foreground)">
          {MONTHS_SHORT[i]}
        </text>
      ))}

      <path d={line(lastPts)} fill="none" stroke={LAST_COLOR} strokeWidth={1.75} strokeDasharray="5 5" strokeLinejoin="round" />
      <path d={area} fill="url(#pace-fill)" />
      <path d={line(thisPts)} fill="none" stroke={THIS_COLOR} strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" />
      {thisPts.length > 0 && <circle cx={x(lastIdx)} cy={y(cum[lastIdx].thisYear)} r={4} fill={THIS_COLOR} stroke="var(--card)" strokeWidth={2} />}

      {cum.map((c, i) => (
        <g key={`hit-${c.month}`}>
          <title>
            {i <= lastIdx
              ? `${MONTHS_SHORT[i]}: ${fmtGBP(c.thisYear)} booked so far this year (${fmtGBP(c.thisMonth)} that month) vs ${fmtGBP(c.lastYear)} last year`
              : `${MONTHS_SHORT[i]}: last year had reached ${fmtGBP(c.lastYear)}`}
          </title>
          <rect x={x(i) - iw / 22} y={pad.top} width={iw / 11} height={ih} fill="transparent" />
        </g>
      ))}
    </svg>
  );
}

export function PaceLegend({ year }: { year: number }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
      <span className="flex items-center gap-1.5">
        <span aria-hidden="true" className="h-0.5 w-4 rounded-full" style={{ background: THIS_COLOR }} />
        {year}
      </span>
      <span className="flex items-center gap-1.5">
        <span aria-hidden="true" className="w-4 border-t-2 border-dashed" style={{ borderColor: LAST_COLOR }} />
        {year - 1}
      </span>
    </div>
  );
}
