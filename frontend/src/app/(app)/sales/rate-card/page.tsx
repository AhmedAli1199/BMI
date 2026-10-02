import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import { canUseAutomations } from "@/lib/access";
import type { SalesMeta, SalesRate } from "@/lib/sales-types";
import { RateCardEditor } from "@/components/sales/rate-card-editor";
import { SalesHeader, YearSwitch } from "@/components/sales/sales-ui";

/** The rate card: what each product costs this year, per title, and where
 * each title's digital edition lives. Renewal emails (SALES-021) quote
 * these prices and link to last year's ad - and say nothing rather than
 * guess when either is missing. */
export default async function RateCardPage({ searchParams }: { searchParams: Promise<{ year?: string }> }) {
  const sp = await searchParams;
  const [meta, session] = await Promise.all([backendFetch<SalesMeta>("/api/sales/meta"), getSession()]);
  const thisYear = new Date().getFullYear();
  const year = Number(sp.year) || thisYear;
  const rates = await backendFetch<SalesRate[]>(`/api/sales/rates?year=${year}`).catch(() => [] as SalesRate[]);
  const years = [...new Set([thisYear + 1, ...meta.years])].sort((a, b) => b - a);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="Rate card"
        crumbs={[{ label: "Sales Orders", href: "/sales" }]}
        description="This year's price for each product, per title, and where each title can be read online. Renewal emails quote these prices and link advertisers back to last year's ad."
        actions={<YearSwitch years={years} current={year} href={(y) => `/sales/rate-card?year=${y}`} />}
      />
      {!canUseAutomations(session) && (
        <p className="-mt-2 text-xs text-muted-foreground">Only admins and data managers can change the rate card.</p>
      )}
      {meta.titles.map((t) => (
        <RateCardEditor key={t.id} title={t} rates={rates.filter((r) => r.title_id === t.id)} year={year} canEdit={canUseAutomations(session)} />
      ))}
    </div>
  );
}
