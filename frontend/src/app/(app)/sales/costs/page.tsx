import Link from "next/link";
import { notFound } from "next/navigation";
import { Download } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import { canUseAutomations } from "@/lib/access";
import type { CostReport, SalesMeta, YearBasis } from "@/lib/sales-types";
import { Button } from "@/components/ui/button";
import { KpiTile } from "@/components/automations/hub-ui";
import { InfoHint } from "@/components/sales/info-hint";
import { CostsReport } from "@/components/sales/costs-report";
import { SalesHeader, SectionTitle, YearBasisSwitch, YearSwitch, fmtGBP, fyLabel } from "@/components/sales/sales-ui";

export default async function CostsPage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const session = await getSession();
  if (!canUseAutomations(session)) notFound();
  const sp = await searchParams;
  const meta = await backendFetch<SalesMeta>("/api/sales/meta");
  const basis: YearBasis = sp.basis === "calendar" || sp.basis === "financial" ? sp.basis : meta.year_basis;
  const all = sp.all === "1";
  const q = new URLSearchParams({ basis, ...(Number(sp.year) ? { year: String(Number(sp.year)) } : {}), ...(all ? { include_all: "true" } : {}) });
  const report = await backendFetch<CostReport>(`/api/sales/costs-report?${q}`);
  const fy = report.basis === "financial";
  const href = (o: { basis?: YearBasis; year?: number; all?: boolean }) => {
    const p = new URLSearchParams({ basis: o.basis ?? report.basis });
    const y = o.year ?? (o.basis && o.basis !== report.basis ? undefined : report.year);
    if (y) p.set("year", String(y));
    if (o.all ?? all) p.set("all", "1");
    return `/sales/costs?${p}`;
  };
  const margin = report.booked_gbp ? report.profit_gbp / report.booked_gbp : null;
  const catTotal = Object.values(report.by_category).reduce((a, b) => a + b, 0);

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="Costs & profit"
        description="What every issue, event and awards cost to produce, against what it sold. Costs are added on each edition's page; profit is what was sold minus the costs."
        actions={
          <>
            <YearBasisSwitch current={report.basis} startMonth={meta.fy_start_month} href={(b) => href({ basis: b })} />
            <YearSwitch years={fy ? meta.financial_years : meta.years} current={report.year} href={(y) => href({ year: y })} label={fy ? fyLabel : String} />
            <Button size="sm" variant="outline" className="gap-1.5" nativeButton={false} render={<a href={`/api/files/sales/costs-report/export.xlsx?${q}`} download />}>
              <Download className="size-3.5" aria-hidden="true" /> Excel
            </Button>
          </>
        }
      />

      <section aria-label="Key figures" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile label={`Sold, editions with costs`} value={fmtGBP(report.booked_gbp, { compact: true })} footer={`${report.rows.filter((r) => r.cost_lines).length} editions in ${report.label}`} />
        <KpiTile label="Costs" value={fmtGBP(report.costs_gbp, { compact: true })} footer="Every cost line on those editions" />
        <KpiTile label="Profit" value={fmtGBP(report.profit_gbp, { compact: true })} footer={margin !== null ? `${Math.round(margin * 100)}% of what was sold` : "Nothing sold yet"} />
        <KpiTile
          label="No costs recorded"
          value={report.without_costs.toLocaleString("en-GB")}
          footer={
            <span className="flex items-center gap-1">
              <Link href={href({ all: !all })} className="font-medium text-primary hover:underline">
                {all ? "Show only editions with costs" : "Show them in the list →"}
              </Link>
              <InfoHint>Editions in {report.label} that have bookings but no costs yet, so their profit can&apos;t be worked out.</InfoHint>
            </span>
          }
        />
      </section>

      {catTotal > 0 && (
        <section aria-labelledby="cats-heading" className="rounded-xl border border-border/80 bg-card p-5 shadow-2xs">
          <SectionTitle id="cats-heading" hint="Every cost line in the year, by what it was for. Lines without a type count as Other.">
            Where the money went
          </SectionTitle>
          <ul className="grid gap-x-8 gap-y-2 sm:grid-cols-2">
            {Object.entries(report.by_category).map(([k, v]) => (
              <li key={k} className="flex flex-col gap-1">
                <div className="flex items-baseline justify-between text-xs">
                  <span className="font-semibold text-foreground">{report.categories[k] ?? k}</span>
                  <span className="tabular-nums text-muted-foreground">{fmtGBP(v)} · {Math.round((v / catTotal) * 100)}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-muted" aria-hidden="true">
                  <div className="h-full rounded-full" style={{ width: `${(v / catTotal) * 100}%`, background: "var(--chart-1)" }} />
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      <CostsReport report={report} titles={meta.titles} />
    </div>
  );
}
