import Link from "next/link";
import { ArrowRight, CalendarClock, FileWarning, Layers, RefreshCcw } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { SalesMeta, SalesOverview, YearBasis } from "@/lib/sales-types";
import { fmtPercent, pctChange } from "@/lib/automation-format";
import { Button } from "@/components/ui/button";
import { Delta, KpiTile } from "@/components/automations/hub-ui";
import { InfoHint } from "@/components/sales/info-hint";
import { PaceChart, PaceLegend } from "@/components/sales/pace-chart";
import {
  MONTHS_SHORT,
  PaceBar,
  SalesHeader,
  SectionTitle,
  TitleIcon,
  YearBasisSwitch,
  YearSwitch,
  fmtDate,
  fmtGBP,
  fyLabel,
} from "@/components/sales/sales-ui";

export default async function SalesOverviewPage({ searchParams }: { searchParams: Promise<{ year?: string; basis?: string }> }) {
  const { year: rawYear, basis: rawBasis } = await searchParams;
  const meta = await backendFetch<SalesMeta>("/api/sales/meta");
  const basis: YearBasis = rawBasis === "calendar" || rawBasis === "financial" ? rawBasis : meta.year_basis;
  const yearParam = Number(rawYear) ? `&year=${Number(rawYear)}` : "";
  const ov = await backendFetch<SalesOverview>(`/api/sales/overview?basis=${basis}${yearParam}`);
  const year = ov.year;
  const fy = ov.basis === "financial";
  const label = ov.label;
  const prevLabel = ov.previous_label;
  const yearWord = fy ? "financial year" : "year";
  const startMonth = MONTHS_SHORT[ov.fy_start_month - 1];
  const overviewHref = (b: YearBasis, y?: number) => `/sales?basis=${b}${y ? `&year=${y}` : ""}`;

  // Calendar years link to the editions list; financial years filter bookings by edition date.
  const periodQuery = fy ? `edition_from=${ov.period_start}&edition_to=${ov.period_end}` : `year=${year}`;
  const titleHref = (id: string) => (fy ? `/sales/bookings?title=${id}&${periodQuery}` : `/sales/editions?year=${year}&title=${id}`);
  const editionsHref = fy ? `/sales/bookings?${periodQuery}` : `/sales/editions?year=${year}`;

  const lyLabel = ov.is_current_year ? "by this date last year" : `in ${prevLabel}`;
  const compare = ov.is_current_year ? ov.last_year_same_point_gbp : ov.last_year_total_gbp;
  const titleMax = Math.max(...ov.by_title.map((t) => Math.max(t.booked_gbp, t.last_year_total_gbp)), 1);
  const repMax = Math.max(...ov.by_rep.map((r) => r.credit_gbp), 1);
  const asOfMonth = new Date(ov.as_of).getMonth() + 1;
  const currentMonth = ov.is_current_year ? ov.monthly.findIndex((m) => m.month === asOfMonth) + 1 || null : null;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="Sales Orders"
        description="BMI's order book - every booking across every title, issue and event, in one place instead of fifteen spreadsheets."
        actions={
          <>
            <YearBasisSwitch current={ov.basis} startMonth={ov.fy_start_month} href={(b) => overviewHref(b)} />
            <YearSwitch
              years={fy ? meta.financial_years : meta.years}
              current={year}
              href={(y) => overviewHref(ov.basis, y)}
              label={fy ? fyLabel : String}
            />
            <Button size="sm" className="gap-1.5 font-semibold" render={<Link href={editionsHref} />} nativeButton={false}>
              <Layers className="size-3.5" aria-hidden="true" />
              {fy ? "Bookings" : "Editions"}
              <ArrowRight className="size-3.5" aria-hidden="true" />
            </Button>
          </>
        }
      />

      <section aria-label="Key figures" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile
          label={`Booked in ${label}`}
          value={fmtGBP(ov.booked_gbp, { compact: true })}
          delta={<Delta change={pctChange(ov.booked_gbp, compare)} goodWhenUp />}
          footer={
            <span className="flex items-center gap-1">
              {fmtGBP(compare, { compact: true })} {lyLabel}
              <InfoHint>
                {fy
                  ? `Live bookings for editions published or held from ${fmtDate(ov.period_start)} to ${fmtDate(ov.period_end)}`
                  : `Live bookings for ${year}'s editions`}{" "}
                - cancelled, contra and moved bookings aren&apos;t counted.
                {ov.is_current_year && ` Compared with last ${yearWord}'s editions, counting only what had been booked by today's date a year ago.`}
              </InfoHint>
            </span>
          }
        />
        <KpiTile
          label="Invoiced"
          value={fmtPercent(ov.booked_gbp ? ov.invoiced_gbp / ov.booked_gbp : null)}
          footer={`${fmtGBP(ov.invoiced_gbp, { compact: true })} of ${fmtGBP(ov.booked_gbp, { compact: true })} booked`}
        />
        <KpiTile
          label="Awaiting invoice"
          value={ov.uninvoiced_count.toLocaleString("en-GB")}
          footer={
            <Link href="/sales/invoicing" className="font-medium text-primary hover:underline">
              {fmtGBP(ov.uninvoiced_gbp, { compact: true })} not invoiced yet →
            </Link>
          }
        />
        <KpiTile
          label="Advertisers"
          value={ov.advertisers.toLocaleString("en-GB")}
          footer={
            <span>
              {ov.new_advertisers} new ·{" "}
              <Link href="/sales/renewals" className="font-medium text-primary hover:underline">
                {ov.renewal_candidates} from {prevLabel} not back yet
              </Link>
            </span>
          }
        />
      </section>

      <section aria-labelledby="pace-heading" className="rounded-xl border border-border/80 bg-card p-5 shadow-2xs">
        <SectionTitle
          id="pace-heading"
          hint={`Running total of booked value through the ${yearWord}, by the month each booking was taken. Bookings taken before the ${yearWord} began (for its editions) are the starting point in ${startMonth}.`}
          aside={<PaceLegend year={label} previous={prevLabel} />}
        >
          Booking pace
          <span className="font-normal text-muted-foreground">· {label} vs {prevLabel}</span>
        </SectionTitle>
        <p className="sr-only">
          {fmtGBP(ov.booked_gbp)} booked for {label} so far, against {fmtGBP(compare)} {lyLabel} and {fmtGBP(ov.last_year_total_gbp)} for the whole of {prevLabel}.
        </p>
        <PaceChart monthly={ov.monthly} currentMonth={currentMonth} />
      </section>

      <div className="grid gap-6 lg:grid-cols-5">
        <section aria-labelledby="titles-heading" className="lg:col-span-3">
          <SectionTitle
            id="titles-heading"
            hint={`The bar is ${label} so far. The tick marks where the title was ${lyLabel}; the full width is the larger of this ${yearWord} and ${prevLabel}'s final total.`}
          >
            By title
          </SectionTitle>
          <div className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs">
            <table className="w-full text-sm">
              <caption className="sr-only">Booked value by title</caption>
              <thead>
                <tr className="border-b border-border/70 text-left text-xs font-semibold text-muted-foreground">
                  <th scope="col" className="px-4 py-2.5 font-semibold">Title</th>
                  <th scope="col" className="px-3 py-2.5 text-right font-semibold">Booked</th>
                  <th scope="col" className="px-3 py-2.5 text-right font-semibold">vs {ov.is_current_year ? "same point" : prevLabel}</th>
                  <th scope="col" className="w-[30%] px-4 py-2.5 font-semibold"><span className="sr-only">Progress</span></th>
                </tr>
              </thead>
              <tbody>
                {ov.by_title.map((t) => {
                  const cmp = ov.is_current_year ? t.last_year_same_point_gbp : t.last_year_total_gbp;
                  return (
                    <tr key={t.title.id} className="group relative border-b border-border/60 last:border-0 hover:bg-accent/40">
                      <td className="px-4 py-2.5">
                        <Link href={titleHref(t.title.id)} className="flex items-center gap-2 font-semibold text-foreground after:absolute after:inset-0">
                          <span className="text-muted-foreground">
                            <TitleIcon line={t.title.product_line} />
                          </span>
                          {t.title.name}
                        </Link>
                        <div className="pl-6 text-[11px] text-muted-foreground">
                          {t.orders} bookings · {t.advertisers} advertisers
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-right font-semibold tabular-nums">{fmtGBP(t.booked_gbp, { compact: true })}</td>
                      <td className="px-3 py-2.5 text-right">
                        {t.orders === 0 ? (
                          <span className="text-xs text-muted-foreground">none yet</span>
                        ) : cmp > 0 ? (
                          <Delta change={pctChange(t.booked_gbp, cmp)} goodWhenUp />
                        ) : (
                          <span className="text-xs text-muted-foreground">new</span>
                        )}
                      </td>
                      <td className="px-4 py-2.5">
                        <PaceBar value={t.booked_gbp} compare={cmp || null} max={Math.max(t.booked_gbp, t.last_year_total_gbp) || titleMax} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        <div className="flex flex-col gap-6 lg:col-span-2">
          {ov.is_current_year && (
            <section aria-labelledby="upcoming-heading">
              <SectionTitle id="upcoming-heading" hint="Open editions publishing or taking place in the next ~10 weeks, with how they're selling against last year's equivalent edition at the same point.">
                Coming up
              </SectionTitle>
              <div className="flex flex-col divide-y divide-border/60 overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs">
                {ov.upcoming.length === 0 && <p className="px-4 py-6 text-center text-sm text-muted-foreground">Nothing publishing in the next 10 weeks.</p>}
                {ov.upcoming.map((e) => (
                  <Link key={e.id} href={`/sales/editions/${e.id}`} className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-accent/40">
                    <div className="flex w-11 shrink-0 flex-col items-center rounded-lg border border-border/80 py-1 text-center">
                      <span className="text-[10px] font-bold uppercase text-primary">{fmtDate(e.edition_date, false).split(" ")[1]}</span>
                      <span className="font-serif text-base leading-none font-bold tabular-nums">{fmtDate(e.edition_date, false).split(" ")[0]}</span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-semibold text-foreground">{e.label}</div>
                      <div className="text-[11px] text-muted-foreground">
                        {e.orders} bookings{e.uninvoiced ? ` · ${e.uninvoiced} to invoice` : ""}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-semibold tabular-nums">{fmtGBP(e.booked_gbp, { compact: true })}</div>
                      {e.previous_same_point_gbp ? <Delta change={pctChange(e.booked_gbp, e.previous_same_point_gbp)} goodWhenUp /> : null}
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          )}

          <section aria-labelledby="reps-heading">
            <SectionTitle id="reps-heading" hint="Each salesperson's credited share of live bookings - a shared booking is split between the people on it.">
              By salesperson
            </SectionTitle>
            <div className="flex flex-col gap-2.5 rounded-xl border border-border/80 bg-card p-4 shadow-2xs">
              {ov.by_rep.map((r) => (
                <Link key={r.rep.id} href={`/sales/bookings?rep=${r.rep.id}&${periodQuery}`} className="group flex flex-col gap-1">
                  <div className="flex items-baseline justify-between text-xs">
                    <span className="font-semibold text-foreground group-hover:text-primary">
                      {r.rep.name}
                      {!r.rep.active && <span className="font-normal text-muted-foreground"> · former</span>}
                    </span>
                    <span className="tabular-nums text-muted-foreground">
                      <span className="font-semibold text-foreground">{fmtGBP(r.credit_gbp, { compact: true })}</span> · {r.orders}
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full bg-muted" aria-hidden="true">
                    <div className="h-full rounded-full" style={{ width: `${(r.credit_gbp / repMax) * 100}%`, background: "var(--chart-1)" }} />
                  </div>
                </Link>
              ))}
            </div>
          </section>
        </div>
      </div>

      <nav aria-label="More in Sales Orders" className="grid gap-3 sm:grid-cols-3">
        {[
          { href: "/sales/renewals", icon: RefreshCcw, title: "Renewals", text: `${ov.renewal_candidates} of last year's advertisers haven't rebooked yet` },
          { href: "/sales/invoicing", icon: FileWarning, title: "Invoicing", text: `${ov.uninvoiced_count} bookings awaiting an invoice` },
          { href: fy ? `/sales/editions?year=${new Date(ov.period_end).getFullYear()}` : `/sales/editions?year=${year}`, icon: CalendarClock, title: "All editions", text: "Every issue, month and event, with its bookings" },
        ].map((l) => (
          <Link key={l.href} href={l.href} className="group flex items-start gap-3 rounded-xl border border-border/80 bg-card p-4 shadow-2xs transition-colors hover:border-primary/40">
            <l.icon className="mt-0.5 size-4 text-primary" aria-hidden="true" />
            <div>
              <div className="text-sm font-semibold text-foreground group-hover:text-primary">{l.title}</div>
              <div className="text-xs text-muted-foreground">{l.text}</div>
            </div>
          </Link>
        ))}
      </nav>
    </div>
  );
}
