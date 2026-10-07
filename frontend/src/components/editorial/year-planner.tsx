import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import type { Issue, PlannerBrand } from "@/lib/editorial-types";
import { issueLabel } from "@/lib/editorial-types";
import { brandColor } from "@/components/rate-card/brand-style";
import { MONTHS, fmtDay } from "@/components/editorial/editorial-ui";

function dayFrac(iso: string, year: number): number {
  const d = new Date(iso + "T00:00:00");
  const start = new Date(year, 0, 1).getTime();
  const end = new Date(year + 1, 0, 1).getTime();
  return Math.min(1, Math.max(0, (d.getTime() - start) / (end - start)));
}

type Placed = { issue: Issue; start: number; end: number; lane: number };

/** Puts each issue in the first lane where it (and its label) doesn't overlap the one before. */
function placeInLanes(issues: Issue[], year: number): { placed: Placed[]; lanes: number } {
  const items = issues
    .filter((i) => i.edition_date && i.edition_date.startsWith(String(year)))
    .map((i) => {
      const dates = [i.editorial_deadline, i.ad_deadline, i.copy_deadline, ...i.milestones.map((m) => m.date)].filter((d): d is string => !!d && d.startsWith(String(year)));
      const pub = dayFrac(i.edition_date!, year);
      const start = Math.min(pub, ...dates.map((d) => dayFrac(d, year)));
      const width = Math.min(0.22, 0.012 + issueLabel(i).length * 0.0058);
      return start > 0.82 ? { issue: i, start: Math.min(start, pub - width), end: Math.max(pub, start) } : { issue: i, start, end: Math.max(pub, start + width) };
    })
    .sort((a, b) => a.start - b.start);
  const laneEnds: number[] = [];
  const placed = items.map((it) => {
    let lane = laneEnds.findIndex((e) => e + 0.004 < it.start);
    if (lane === -1) { lane = laneEnds.length; laneEnds.push(it.end); } else laneEnds[lane] = it.end;
    return { ...it, lane };
  });
  return { placed, lanes: Math.max(1, laneEnds.length) };
}

function tooltip(i: Issue): string {
  return [
    `${i.title_name}: ${issueLabel(i)}`,
    i.theme,
    `${i.kind === "issue" || i.kind === "guide" ? "Publishes" : "On"} ${fmtDay(i.edition_date, true)}`,
    i.ad_deadline && `Advertising deadline ${fmtDay(i.ad_deadline)}`,
    i.editorial_deadline && `Editorial deadline ${fmtDay(i.editorial_deadline)}`,
    i.copy_deadline && `Copy deadline ${fmtDay(i.copy_deadline)}`,
    ...i.milestones.map((m) => `${m.label} ${fmtDay(m.date)}`),
    i.needs_check ? "Some dates need checking" : null,
  ].filter(Boolean).join("\n");
}

const LANE = 34;

/** The wall planner: one band per brand, a row per part of the brand, Jan-Dec across. Bars run from the first
 * deadline to the publication day; diamonds are advertising deadlines, the solid dot is publication / event day. */
export function YearPlanner({ brands, year, today }: { brands: PlannerBrand[]; year: number; today: string }) {
  const todayFrac = today.startsWith(String(year)) ? dayFrac(today, year) : null;
  return (
    <div className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
      <div className="min-w-[56rem]">
        {/* month header */}
        <div className="sticky top-0 z-10 grid grid-cols-[11rem_minmax(0,1fr)] border-b border-border/70 bg-card">
          <div className="px-3 py-2 text-xs font-semibold text-muted-foreground">{year}</div>
          <div className="relative grid grid-cols-12">
            {MONTHS.map((m) => <div key={m} className="border-l border-border/50 px-1.5 py-2 text-xs font-semibold text-muted-foreground">{m}</div>)}
            {todayFrac !== null && <span className="absolute -bottom-px h-0.5 w-2 -translate-x-1/2 rounded bg-[var(--bad)]" style={{ left: `${todayFrac * 100}%` }} aria-hidden="true" />}
          </div>
        </div>
        {brands.map((b) => (
          <section key={b.key} aria-label={b.name} className="border-b border-border/70 last:border-b-0">
            <div className="flex items-center gap-2 bg-muted/30 px-3 py-1.5">
              <span className="masthead-rule w-6" style={{ background: brandColor(b.key) }} aria-hidden="true" />
              <h2 className="text-xs font-bold">{b.name}</h2>
            </div>
            {b.rows.length === 0 && <p className="px-3 py-3 text-xs text-muted-foreground">Nothing planned for {year} yet.</p>}
            {b.rows.map((row) => {
              const { placed, lanes } = placeInLanes(row.issues, year);
              if (!placed.length) return null;
              return (
                <div key={row.title_id} className="grid grid-cols-[11rem_minmax(0,1fr)] border-t border-border/40">
                  <div className="px-3 py-2 text-xs font-medium">{row.title_name}</div>
                  <div className="relative" style={{ height: lanes * LANE + 10 }}>
                    <div className="absolute inset-0 grid grid-cols-12" aria-hidden="true">{MONTHS.map((m) => <div key={m} className="border-l border-border/40" />)}</div>
                    {todayFrac !== null && <div className="absolute inset-y-0 w-px" style={{ left: `${todayFrac * 100}%`, background: "color-mix(in oklab, var(--bad) 60%, transparent)" }} aria-hidden="true" />}
                    {placed.map(({ issue: i, lane }) => <PlannerItem key={i.id} issue={i} year={year} top={lane * LANE + 5} color={brandColor(b.key)} past={!!i.edition_date && i.edition_date < today} />)}
                  </div>
                </div>
              );
            })}
          </section>
        ))}
      </div>
    </div>
  );
}

function PlannerItem({ issue: i, year, top, color, past }: { issue: Issue; year: number; top: number; color: string; past: boolean }) {
  const pub = dayFrac(i.edition_date!, year);
  const marks = [
    i.editorial_deadline && { d: i.editorial_deadline, kind: "editorial" },
    i.copy_deadline && { d: i.copy_deadline, kind: "copy" },
    i.ad_deadline && { d: i.ad_deadline, kind: "ad" },
    ...i.milestones.map((m) => ({ d: m.date, kind: "milestone" })),
  ].filter((m): m is { d: string; kind: string } => !!m && m.d.startsWith(String(year)));
  const start = Math.min(pub, ...marks.map((m) => dayFrac(m.d, year)));
  const isEvent = i.kind === "event" || i.kind === "awards";
  return (
    <Link href={`/editorial/issues/${i.id}`} title={tooltip(i)} aria-label={tooltip(i).replace(/\n/g, ". ")}
      className={`group absolute block focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ${past ? "opacity-55 hover:opacity-100" : ""}`}
      style={{ left: `${start * 100}%`, top, height: LANE - 6, width: `max(${(pub - start) * 100}%, 8px)` }}>
      {/* label */}
      <span className={`pointer-events-none absolute -top-0.5 whitespace-nowrap text-[10.5px] font-semibold leading-none text-foreground group-hover:underline ${start > 0.82 ? "right-0" : "left-0"}`}>
        {issueLabel(i)}{i.needs_check && <AlertTriangle className="ml-0.5 inline size-2.5 align-[-1px]" style={{ color: "var(--warn)" }} aria-hidden="true" />}
      </span>
      {/* bar from first deadline to publication */}
      {!isEvent && pub > start && (
        <span className="absolute bottom-1.5 left-0 right-0 h-2 rounded-full" style={{ background: `color-mix(in oklab, ${color} 22%, transparent)`, border: `1px solid color-mix(in oklab, ${color} 45%, transparent)` }} />
      )}
      {marks.map((m, k) => (
        <span key={k} className="absolute bottom-[5px] size-2.5 -translate-x-1/2 rotate-45 border-2 border-card"
          style={{ left: `${pub > start ? ((dayFrac(m.d, year) - start) / (pub - start)) * 100 : 0}%`,
            background: m.kind === "ad" ? "var(--warn)" : m.kind === "editorial" ? "var(--chart-4)" : m.kind === "copy" ? "var(--chart-5)" : "var(--chart-2)" }} />
      ))}
      <span className="absolute bottom-[3px] size-3.5 -translate-x-1/2 rounded-full border-2 border-card" style={{ left: pub > start ? "100%" : "4px", background: color }} />
    </Link>
  );
}

export function PlannerLegend() {
  const items = [
    { label: "Publication / event day", el: <span className="inline-block size-3 rounded-full bg-primary" /> },
    { label: "Advertising deadline", el: <span className="inline-block size-2.5 rotate-45" style={{ background: "var(--warn)" }} /> },
    { label: "Editorial deadline", el: <span className="inline-block size-2.5 rotate-45" style={{ background: "var(--chart-4)" }} /> },
    { label: "Copy / artwork deadline", el: <span className="inline-block size-2.5 rotate-45" style={{ background: "var(--chart-5)" }} /> },
    { label: "Other key date", el: <span className="inline-block size-2.5 rotate-45" style={{ background: "var(--chart-2)" }} /> },
    { label: "Today", el: <span className="inline-block h-3 w-px" style={{ background: "var(--bad)" }} /> },
  ];
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted-foreground" aria-label="Key">
      {items.map((i) => <li key={i.label} className="flex items-center gap-1.5">{i.el}{i.label}</li>)}
    </ul>
  );
}
