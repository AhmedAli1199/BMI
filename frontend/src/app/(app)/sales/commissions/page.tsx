import Link from "next/link";
import { AlertTriangle, CheckCircle2, Settings2, UserX } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { SalesMeta } from "@/lib/sales-types";
import type { CommissionOverview } from "@/lib/commission-types";
import { Button } from "@/components/ui/button";
import { InfoHint } from "@/components/sales/info-hint";
import { EmptyState, SalesHeader, YearSwitch, fmtGBP } from "@/components/sales/sales-ui";
import { LoadStructureButton } from "@/components/commission/commission-ui";
import { monthLabel } from "@/lib/commission-format";

export default async function CommissionsPage({ searchParams }: { searchParams: Promise<{ year?: string }> }) {
  const sp = await searchParams;
  const year = Number(sp.year) || new Date().getFullYear();
  const [meta, data] = await Promise.all([
    backendFetch<SalesMeta>("/api/sales/meta"),
    backendFetch<CommissionOverview>(`/api/commission/overview?year=${year}`),
  ]);
  const months = data.reps[0]?.months.map((m) => m.period) ?? [];
  const checks = data.reps.reduce((s, r) => s + r.checks, 0);

  return (
    <div className="mx-auto flex w-full max-w-[90rem] flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title={data.scoped_to_me ? "My commission" : "Commissions"}
        crumbs={[{ label: "Sales Orders", href: "/sales" }]}
        description={data.scoped_to_me
          ? "Your commission month by month. Open a month to see every booking, the rate it earned, and why."
          : "Each salesperson's commission month by month, worked out from the order register and their plan. Open a month to check it and approve it."}
        actions={<>
          {!data.scoped_to_me && <Button size="sm" variant="outline" className="gap-1.5" nativeButton={false} render={<Link href="/sales/commissions/plans" />}><Settings2 className="size-3.5" /> Commission plans</Button>}
          <YearSwitch years={meta.years} current={year} href={(y) => `/sales/commissions?year=${y}`} />
        </>}
      />

      {!data.has_plans && !data.scoped_to_me && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-primary/30 bg-primary/5 px-4 py-3 text-sm">
          <p className="min-w-0 flex-1"><strong>No commission plans yet.</strong> <span className="text-muted-foreground">Load BMI&apos;s structure (the rates, new business top-ups and bonuses Matt sent) and every figure below is worked out from it. Until then everyone is on the standard 2%.</span></p>
          {data.can_manage && <LoadStructureButton />}
        </div>
      )}

      {checks > 0 && !data.scoped_to_me && (
        <div className="flex items-start gap-2 rounded-xl border px-4 py-3 text-sm" style={{ borderColor: "color-mix(in oklab, var(--warn) 40%, transparent)", background: "color-mix(in oklab, var(--warn) 8%, transparent)" }}>
          <AlertTriangle className="mt-0.5 size-4 shrink-0" style={{ color: "var(--warn)" }} aria-hidden="true" />
          <p><strong>{checks === 1 ? "1 booking needs" : `${checks} bookings need`} a decision on new business.</strong> <span className="text-muted-foreground">A similar name has spent with BMI recently, so it isn&apos;t decided automatically. The months marked with a dot have them.</span></p>
        </div>
      )}

      {data.reps.length === 0 ? (
        data.scoped_to_me ? (
          <EmptyState icon={UserX} title="Your login isn't linked to a salesperson yet">
            Once an administrator links your account to your initials in the order register (Settings, Users), your commission shows here.
          </EmptyState>
        ) : (
          <EmptyState icon={UserX} title={`No commission for ${year} yet`} />
        )
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
          <table className="w-full min-w-[56rem] text-sm">
            <caption className="sr-only">Commission by salesperson and month</caption>
            <thead>
              <tr className="border-b border-border/70 text-left text-xs text-muted-foreground">
                <th scope="col" className="px-4 py-2.5 font-semibold">Salesperson</th>
                {months.map((p) => <th key={p} scope="col" className="px-2 py-2.5 text-right font-semibold">{monthLabel(p, true)}</th>)}
                <th scope="col" className="px-4 py-2.5 text-right font-semibold">
                  <span className="inline-flex items-center gap-1">{year} <InfoHint>Approved months show what was paid; the rest show the figure as it stands today.</InfoHint></span>
                </th>
              </tr>
            </thead>
            <tbody>
              {data.reps.map((r) => (
                <tr key={r.rep.id} className="border-b border-border/60 last:border-0">
                  <th scope="row" className="px-4 py-2 text-left font-semibold">
                    {r.rep.name}
                    {!r.has_plan && <span className="ml-1.5 text-[10px] font-normal" style={{ color: "var(--warn)" }}>no plan, on 2%</span>}
                  </th>
                  {r.months.map((m) => (
                    <td key={m.period} className="px-1 py-1 text-right">
                      <Link href={`/sales/commissions/${r.rep.id}/${m.period}`}
                        className="flex items-center justify-end gap-1 rounded-md px-1.5 py-1.5 tabular-nums hover:bg-muted"
                        title={`${monthLabel(m.period)}: ${m.bookings} booking${m.bookings === 1 ? "" : "s"}${m.approved ? ", approved" : ""}`}>
                        {m.checks > 0 && <span className="size-1.5 rounded-full" style={{ background: "var(--warn)" }} aria-label={`${m.checks} to decide`} />}
                        {m.approved && <CheckCircle2 className="size-3" style={{ color: "var(--ok)" }} aria-label="Approved" />}
                        <span className={m.total_gbp ? "font-medium" : "text-muted-foreground"}>{m.total_gbp ? fmtGBP(m.total_gbp) : "-"}</span>
                      </Link>
                    </td>
                  ))}
                  <td className="px-4 py-2 text-right font-bold tabular-nums">{fmtGBP(r.year_total_gbp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-xs text-muted-foreground">
        <CheckCircle2 className="mr-1 inline size-3" style={{ color: "var(--ok)" }} aria-hidden="true" />approved and locked ·
        <span className="mx-1 inline-block size-1.5 rounded-full align-middle" style={{ background: "var(--warn)" }} aria-hidden="true" />has bookings to decide ·
        A booking counts in the month its issue publishes or its event runs.
      </p>
    </div>
  );
}
