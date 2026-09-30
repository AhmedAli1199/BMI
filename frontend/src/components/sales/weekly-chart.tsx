import { fmtGBP } from "@/components/sales/sales-ui";

const THIS_COLOR = "var(--chart-2)";

/** Booked value per week for the last few weeks: bars for this year, a
 * tick on each for the same week a year earlier. Reading a bar against its
 * tick is the quick "busier or quieter than last year" check. */
export function WeeklyChart({ weekly }: { weekly: { week_start: string; orders: number; value_gbp: number; last_year_value_gbp: number }[] }) {
  const W = 800;
  const H = 200;
  const pad = { top: 12, right: 12, bottom: 26, left: 56 };
  const iw = W - pad.left - pad.right;
  const ih = H - pad.top - pad.bottom;
  const max = Math.max(...weekly.flatMap((w) => [w.value_gbp, w.last_year_value_gbp]), 1);
  const mag = 10 ** Math.floor(Math.log10(max));
  const yMax = Math.ceil(max / mag) * mag;
  const slot = iw / weekly.length;
  const y = (v: number) => pad.top + ih - (v / yMax) * ih;
  const label = (iso: string) => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" });

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Booked value per week against the same week last year">
      {[0, 0.5, 1].map((f) => (
        <g key={f}>
          <line x1={pad.left} x2={W - pad.right} y1={y(yMax * f)} y2={y(yMax * f)} stroke="var(--border)" strokeDasharray={f === 0 ? undefined : "3 4"} />
          <text x={pad.left - 8} y={y(yMax * f) + 4} textAnchor="end" fontSize={11} fill="var(--muted-foreground)">
            {fmtGBP(yMax * f, { compact: true })}
          </text>
        </g>
      ))}
      {weekly.map((w, i) => {
        const x = pad.left + slot * i + slot * 0.2;
        const bw = slot * 0.6;
        return (
          <g key={w.week_start}>
            <title>{`Week of ${label(w.week_start)}: ${fmtGBP(w.value_gbp)} across ${w.orders} booking(s); ${fmtGBP(w.last_year_value_gbp)} the same week last year`}</title>
            <rect x={x} y={y(w.value_gbp)} width={bw} height={Math.max(0, y(0) - y(w.value_gbp))} rx={2} fill={THIS_COLOR} opacity={0.85} />
            <line x1={x - 3} x2={x + bw + 3} y1={y(w.last_year_value_gbp)} y2={y(w.last_year_value_gbp)} stroke="var(--foreground)" strokeWidth={2} opacity={0.7} />
            {(i % 2 === 0 || weekly.length < 8) && (
              <text x={x + bw / 2} y={H - 8} textAnchor="middle" fontSize={10} fill="var(--muted-foreground)">
                {label(w.week_start)}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
