import Link from "next/link";
import { ChevronRight, UserX } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { Commissions, SalesMeta } from "@/lib/sales-types";
import { KpiTile } from "@/components/automations/hub-ui";
import { InfoHint } from "@/components/sales/info-hint";
import { EmptyState, SalesHeader, YearSwitch, fmtDate, fmtGBP } from "@/components/sales/sales-ui";

export default async function CommissionsPage({ searchParams }: { searchParams: Promise<{ year?: string }> }) {
  const sp = await searchParams;
  const meta = await backendFetch<SalesMeta>("/api/sales/meta");
  const year = Number(sp.year) || new Date().getFullYear();
  const data = await backendFetch<Commissions>(`/api/sales/commissions?year=${year}`);
  const totalCredit = data.reps.reduce((s, r) => s + r.credit_gbp, 0);
  const totalCommission = data.reps.reduce((s, r) => s + r.commission_gbp, 0);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title={data.scoped_to_me ? "My commission" : "Commissions"}
        crumbs={[{ label: "Sales Orders", href: "/sales" }]}
        description={
          data.scoped_to_me
            ? `Your credited bookings for ${year}'s editions and the commission they earn - what the sheets' per-rep columns used to show.`
            : `Each salesperson's credited bookings for ${year}'s editions and the commission they earn - replacing the per-rep columns on every sheet.`
        }
        actions={<YearSwitch years={meta.years} current={year} href={(y) => `/sales/commissions?year=${y}`} />}
      />

      {data.reps.length === 0 ? (
        data.scoped_to_me ? (
          <EmptyState icon={UserX} title="Your login isn't linked to a salesperson yet">
            Once an administrator links your account to your initials in the order register, your bookings and commission show here.
          </EmptyState>
        ) : (
          <EmptyState icon={UserX} title={`No credited bookings for ${year}`} />
        )
      ) : (
        <>
          {!data.scoped_to_me && (
            <section aria-label="Totals" className="grid gap-4 sm:grid-cols-3">
              <KpiTile label="Credited bookings" value={fmtGBP(totalCredit, { compact: true })} footer={`${data.reps.length} salespeople`} />
              <KpiTile
                label="Commission"
                value={fmtGBP(totalCommission, { compact: true })}
                footer={
                  <span className="flex items-center gap-1">
                    at each person&apos;s rate
                    <InfoHint>
                      2% of each person&apos;s credited share of live bookings, unless a different rate is set on the booking itself. Every
                      &ldquo;Commission payable&rdquo; figure in the 2026 sheets works out at 2% (two at 5%) - BMI to confirm the rule for
                      the exceptions.
                    </InfoHint>
                  </span>
                }
              />
              <KpiTile label="Bookings" value={data.reps.reduce((s, r) => s + r.orders, 0).toLocaleString("en-GB")} footer="live bookings credited" />
            </section>
          )}

          <section aria-label="By salesperson" className="flex flex-col gap-3">
            {data.reps.map((r) => (
              <details key={r.rep.id} open={data.scoped_to_me || data.reps.length === 1} className="group overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs">
                <summary className="flex cursor-pointer list-none items-center gap-4 px-4 py-3.5 hover:bg-accent/30 [&::-webkit-details-marker]:hidden">
                  <ChevronRight className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-90" aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold text-foreground">
                      {r.rep.name}
                      {!r.rep.active && <span className="font-normal text-muted-foreground"> · former</span>}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {r.orders} bookings across {r.editions.length} editions · {Math.round(r.rep.commission_rate * 1000) / 10}% rate
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-muted-foreground">Credited</div>
                    <div className="font-semibold tabular-nums">{fmtGBP(r.credit_gbp)}</div>
                  </div>
                  <div className="w-28 text-right">
                    <div className="text-xs text-muted-foreground">Commission</div>
                    <div className="font-serif text-lg font-bold tabular-nums" style={{ color: "var(--ok)" }}>{fmtGBP(r.commission_gbp)}</div>
                  </div>
                </summary>
                <table className="w-full border-t border-border/70 text-sm">
                  <caption className="sr-only">{r.rep.name}&apos;s commission by edition</caption>
                  <thead>
                    <tr className="bg-muted/30 text-left text-xs font-semibold text-muted-foreground">
                      <th scope="col" className="px-4 py-2 pl-12 font-semibold">Edition</th>
                      <th scope="col" className="px-3 py-2 font-semibold">Date</th>
                      <th scope="col" className="px-3 py-2 text-right font-semibold">Bookings</th>
                      <th scope="col" className="px-3 py-2 text-right font-semibold">Credited</th>
                      <th scope="col" className="px-4 py-2 text-right font-semibold">Commission</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.editions.map((e) => (
                      <tr key={e.edition.id} className="border-t border-border/50">
                        <td className="px-4 py-2 pl-12">
                          <Link href={`/sales/editions/${e.edition.id}`} className="font-medium text-foreground hover:text-primary hover:underline">
                            {e.edition.label}
                          </Link>
                        </td>
                        <td className="px-3 py-2 text-xs text-muted-foreground">{fmtDate(e.edition_date)}</td>
                        <td className="px-3 py-2 text-right tabular-nums">{e.orders}</td>
                        <td className="px-3 py-2 text-right tabular-nums">{fmtGBP(e.credit_gbp)}</td>
                        <td className="px-4 py-2 text-right font-semibold tabular-nums">{fmtGBP(e.commission_gbp)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </details>
            ))}
          </section>
        </>
      )}
    </div>
  );
}
