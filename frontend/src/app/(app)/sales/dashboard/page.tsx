import Link from "next/link";
import { AlertTriangle, CalendarClock } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { PaceRow, PaceState, SalesDashboard } from "@/lib/sales-types";
import { fmtPercent } from "@/lib/automation-format";
import { KpiTile } from "@/components/automations/hub-ui";
import { InfoHint } from "@/components/sales/info-hint";
import { WeeklyChart } from "@/components/sales/weekly-chart";
import { EmptyState, PaceBar, SalesHeader, SectionTitle, fmtDate, fmtGBP } from "@/components/sales/sales-ui";

const STATE_LABEL: Record<PaceState, string> = {
  behind: "Behind",
  on_pace: "On pace",
  ahead: "Ahead",
  not_comparable: "Too early to compare",
};
const STATE_COLOR: Record<PaceState, string> = {
  behind: "var(--warn)",
  on_pace: "var(--muted-foreground)",
  ahead: "var(--ok)",
  not_comparable: "var(--muted-foreground)",
};

function StatePill({ state }: { state: PaceState }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-semibold" style={{ color: STATE_COLOR[state] }}>
      <span aria-hidden="true" className="size-1.5 rounded-full" style={{ background: STATE_COLOR[state] }} />
      {STATE_LABEL[state]}
    </span>
  );
}

function gapText(r: PaceRow) {
  if (r.gap_gbp === null || r.gap_pct === null) return null;
  const sign = r.gap_gbp >= 0 ? "+" : "−";
  return `${sign}${fmtGBP(Math.abs(r.gap_gbp), { compact: true })} (${sign}${Math.abs(Math.round(r.gap_pct * 100))}%)`;
}

export default async function SalesDashboardPage() {
  const d = await backendFetch<SalesDashboard>("/api/sales/dashboard");
  const behind = d.pace.filter((p) => p.state === "behind").length;
  const ahead = d.pace.filter((p) => p.state === "ahead").length;
  const weeklyTotal = d.weekly.reduce((s, w) => s + w.value_gbp, 0);
  const weeklyLast = d.weekly.reduce((s, w) => s + w.last_year_value_gbp, 0);
  const max = Math.max(...d.pace.map((p) => Math.max(p.booked_gbp, p.previous_point_gbp ?? 0)), 1);

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="Sales dashboard"
        description="How every issue and event is selling against the same point last cycle, the weekly flow of bookings, and what the team has been doing. Every figure is a sum over the order register - click through to the bookings behind it."
      />

      {d.unattributed.orders > 0 && (
        <div role="status" className="flex items-start gap-2.5 rounded-xl border border-border/80 bg-card p-4 text-sm shadow-2xs">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" style={{ color: "var(--warn)" }} aria-hidden="true" />
          <p className="text-muted-foreground">
            <span className="font-semibold text-foreground">
              {d.unattributed.orders} {d.unattributed.orders === 1 ? "booking" : "bookings"} ({fmtGBP(d.unattributed.value_gbp)}) in {d.unattributed_year}
            </span>{" "}
            {d.unattributed.orders === 1 ? "isn't" : "aren't"} credited to any salesperson, so {d.unattributed.orders === 1 ? "it doesn't" : "they don't"} show in the per-person
            figures below. Open the booking and pick a salesperson to fix it.
          </p>
        </div>
      )}

      <section aria-label="Key figures" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile label="Editions selling" value={d.pace.length.toLocaleString("en-GB")} footer="Open, publishing in the next few months" />
        <KpiTile label="Behind last cycle" value={behind.toLocaleString("en-GB")} footer={`${fmtPercent(d.threshold_pct)} or more below the same point`} />
        <KpiTile label="Ahead of last cycle" value={ahead.toLocaleString("en-GB")} footer={`${fmtPercent(d.threshold_pct)} or more above`} />
        <KpiTile label={`Booked, last ${d.weekly.length} weeks`} value={fmtGBP(weeklyTotal, { compact: true })} footer={`${fmtGBP(weeklyLast, { compact: true })} the same weeks last year`} />
      </section>

      <section aria-labelledby="tracker-heading">
        <SectionTitle
          id="tracker-heading"
          hint={`Each edition is compared with its equivalent from last cycle at the same distance before publication (so an issue that moved a fortnight isn't judged against a calendar date). "Behind" means ${fmtPercent(d.threshold_pct)} or more below. An edition is only judged once last cycle had at least ${fmtGBP(d.min_prior_gbp)} across ${d.min_prior_orders} bookings by that point - earlier than that a comparison would just be noise.`}
        >
          Edition tracker
        </SectionTitle>
        {d.pace.length === 0 ? (
          <EmptyState icon={CalendarClock} title="No editions are currently selling">
            Open editions with a publication date in the coming months appear here.
          </EmptyState>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
            <table className="w-full min-w-[46rem] text-sm">
              <caption className="sr-only">Editions on sale compared with the same point last cycle</caption>
              <thead>
                <tr className="border-b border-border/70 text-left text-xs font-semibold text-muted-foreground">
                  <th scope="col" className="px-4 py-2.5 font-semibold">Edition</th>
                  <th scope="col" className="px-3 py-2.5 text-right font-semibold">Booked</th>
                  <th scope="col" className="px-3 py-2.5 text-right font-semibold">Last cycle, same point</th>
                  <th scope="col" className="px-3 py-2.5 text-right font-semibold">Gap</th>
                  <th scope="col" className="w-[18%] px-3 py-2.5 font-semibold"><span className="sr-only">Progress</span></th>
                  <th scope="col" className="px-4 py-2.5 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody>
                {d.pace.map((p) => (
                  <tr key={p.edition.id} className="border-b border-border/60 last:border-0 hover:bg-accent/40">
                    <td className="px-4 py-2.5">
                      <Link href={`/sales/editions/${p.edition.id}`} className="font-semibold text-foreground hover:text-primary hover:underline">
                        {p.edition.label}
                      </Link>
                      <div className="text-[11px] text-muted-foreground">
                        {p.edition_date ? `${p.kind === "event" ? "Runs" : "Publishes"} ${fmtDate(p.edition_date, false)}` : "No date"} · {p.orders} bookings
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-right font-semibold tabular-nums">{fmtGBP(p.booked_gbp, { compact: true })}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-muted-foreground">
                      {p.previous_point_gbp === null ? "—" : fmtGBP(p.previous_point_gbp, { compact: true })}
                      {p.previous && (
                        <div className="text-[11px]">
                          <Link href={`/sales/editions/${p.previous.id}`} className="hover:text-foreground hover:underline">
                            {p.previous.label}
                          </Link>
                        </div>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-right text-xs font-semibold tabular-nums">{gapText(p) ?? <span className="font-normal text-muted-foreground">—</span>}</td>
                    <td className="px-3 py-2.5">
                      {p.state !== "not_comparable" && <PaceBar value={p.booked_gbp} compare={p.previous_point_gbp} max={max} />}
                    </td>
                    <td className="px-4 py-2.5">
                      <StatePill state={p.state} />
                      {p.reason && <div className="max-w-[14rem] text-[11px] leading-snug text-muted-foreground">{p.reason}</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="weekly-heading" className="rounded-xl border border-border/80 bg-card p-5 shadow-2xs">
        <SectionTitle id="weekly-heading" hint="Value of bookings taken each week (by the booking date on the order). The dark tick on each bar is the same week last year. Cancelled, contra and moved bookings aren't counted.">
          Weekly bookings
          <span className="font-normal text-muted-foreground">· last {d.weekly.length} weeks</span>
        </SectionTitle>
        <WeeklyChart weekly={d.weekly} />
      </section>

      <section aria-labelledby="activity-heading">
        <SectionTitle
          id="activity-heading"
          hint={`What each person has done in the last ${d.activity_days} days: bookings credited to them, and follow-up drafts they've dealt with in their queue. Listed alphabetically - this is a picture of what's happening, not a ranking or a target.`}
        >
          Team activity
          <span className="font-normal text-muted-foreground">· last {d.activity_days} days</span>
        </SectionTitle>
        <div className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
          <table className="w-full min-w-[32rem] text-sm">
            <caption className="sr-only">Recent activity per salesperson</caption>
            <thead>
              <tr className="border-b border-border/70 text-left text-xs font-semibold text-muted-foreground">
                <th scope="col" className="px-4 py-2.5 font-semibold">Salesperson</th>
                <th scope="col" className="px-3 py-2.5 text-right font-semibold">Bookings</th>
                <th scope="col" className="px-3 py-2.5 text-right font-semibold">Booked value</th>
                <th scope="col" className="px-3 py-2.5 text-right font-semibold">Follow-ups actioned</th>
                <th scope="col" className="px-4 py-2.5 text-right font-semibold">Waiting in queue</th>
              </tr>
            </thead>
            <tbody>
              {d.activity.map((a) => (
                <tr key={a.rep.id} className="border-b border-border/60 last:border-0 hover:bg-accent/40">
                  <td className="px-4 py-2.5">
                    <Link href={`/sales/bookings?rep=${a.rep.id}`} className="font-semibold text-foreground hover:text-primary hover:underline">
                      {a.rep.name}
                    </Link>
                    {!a.rep.active && <span className="text-xs text-muted-foreground"> · former</span>}
                  </td>
                  <td className="px-3 py-2.5 text-right tabular-nums">{a.bookings}</td>
                  <td className="px-3 py-2.5 text-right tabular-nums">{fmtGBP(a.booked_gbp, { compact: true })}</td>
                  <td className="px-3 py-2.5 text-right tabular-nums">{a.followups_actioned ?? <span className="text-muted-foreground">no login</span>}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums">{a.followups_outstanding ?? <span className="text-muted-foreground">—</span>}</td>
                </tr>
              ))}
              {d.activity.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-sm text-muted-foreground">No activity recorded yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <p className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
          Proposals sent and replies aren&apos;t counted yet - they need the proposal-logging and pipeline automations.
          <InfoHint>Only activity the system actually records appears here. Nothing is estimated.</InfoHint>
        </p>
      </section>
    </div>
  );
}
