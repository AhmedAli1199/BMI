import { fmtGBP } from "@/components/sales/sales-ui";

const A_COLOR = "var(--chart-2)";
const B_COLOR = "var(--muted-foreground)";

/** Running total booked, week by week, lined up on each edition's own publication date - so two issues
 * months apart can be compared fairly. Solid = this edition, dashed = the one it's compared with. */
export function CompareChart({ weeks, a, b }: { weeks: number[]; a: number[]; b: number[] }) {
  const W = 800;
  const H = 220;
  const pad = { top: 12, right: 16, bottom: 26, left: 56 };
  const iw = W - pad.left - pad.right;
  const ih = H - pad.top - pad.bottom;
  const max = Math.max(...a, ...b, 1);
  const mag = 10 ** Math.floor(Math.log10(max));
  const yMax = Math.ceil(max / mag) * mag;
  const x = (i: number) => pad.left + (iw / (weeks.length - 1)) * i;
  const y = (v: number) => pad.top + ih - (v / yMax) * ih;
  const line = (vals: number[]) => vals.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const zero = weeks.indexOf(0);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" aria-hidden="true">
      {[0, 0.5, 1].map((f) => (
        <g key={f}>
          <line x1={pad.left} x2={W - pad.right} y1={y(yMax * f)} y2={y(yMax * f)} stroke="var(--border)" strokeDasharray={f ? "3 4" : undefined} />
          <text x={pad.left - 8} y={y(yMax * f) + 4} textAnchor="end" fontSize={11} fill="var(--muted-foreground)">{fmtGBP(yMax * f, { compact: true })}</text>
        </g>
      ))}
      {zero >= 0 && (
        <g>
          <line x1={x(zero)} x2={x(zero)} y1={pad.top} y2={pad.top + ih} stroke="var(--border)" />
          <text x={x(zero) + 4} y={pad.top + ih - 6} textAnchor="start" fontSize={10} fill="var(--muted-foreground)">Published</text>
        </g>
      )}
      {weeks.map((w, i) =>
        w % 4 === 0 ? (
          <text key={w} x={x(i)} y={H - 8} textAnchor="middle" fontSize={11} fill="var(--muted-foreground)">
            {w === 0 ? "0" : w < 0 ? `${-w}w before` : `+${w}w`}
          </text>
        ) : null
      )}
      <path d={line(b)} fill="none" stroke={B_COLOR} strokeWidth={1.75} strokeDasharray="5 5" />
      <path d={line(a)} fill="none" stroke={A_COLOR} strokeWidth={2.5} strokeLinejoin="round" />
      {weeks.map((w, i) => (
        <g key={`hit-${w}`}>
          <title>{`${w === 0 ? "Publication week" : w < 0 ? `${-w} weeks before` : `${w} weeks after`}: ${fmtGBP(a[i])} vs ${fmtGBP(b[i])}`}</title>
          <rect x={x(i) - iw / (weeks.length - 1) / 2} y={pad.top} width={iw / (weeks.length - 1)} height={ih} fill="transparent" />
        </g>
      ))}
    </svg>
  );
}

export function CompareLegend({ a, b }: { a: string; b: string }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
      <span className="flex items-center gap-1.5"><span aria-hidden="true" className="h-0.5 w-4 rounded-full" style={{ background: A_COLOR }} />{a}</span>
      <span className="flex items-center gap-1.5"><span aria-hidden="true" className="w-4 border-t-2 border-dashed" style={{ borderColor: B_COLOR }} />{b}</span>
    </div>
  );
}
