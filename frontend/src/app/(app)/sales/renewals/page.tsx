import Link from "next/link";
import { PartyPopper, Sparkles } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { EditionSummary, Renewals, SalesMeta } from "@/lib/sales-types";
import { fmtPercent } from "@/lib/automation-format";
import { KpiTile } from "@/components/automations/hub-ui";
import { InfoHint } from "@/components/sales/info-hint";
import { RenewalsTable } from "@/components/sales/renewals-table";
import { EmptyState, SalesHeader, TitleIcon, YearSwitch, fmtGBP } from "@/components/sales/sales-ui";

export default async function RenewalsPage({ searchParams }: { searchParams: Promise<{ title?: string; year?: string }> }) {
  const sp = await searchParams;
  const meta = await backendFetch<SalesMeta>("/api/sales/meta");
  const year = Number(sp.year) || new Date().getFullYear();
  const title = meta.titles.find((t) => t.id === sp.title) ?? meta.titles[0];
  const [data, editions] = await Promise.all([
    backendFetch<Renewals>(`/api/sales/renewals?title_id=${title.id}&year=${year}`),
    backendFetch<EditionSummary[]>(`/api/sales/editions?title_id=${title.id}&year=${year}`),
  ]);
  const href = (p: { title?: string; year?: number }) => `/sales/renewals?title=${p.title ?? title.id}&year=${p.year ?? year}`;

  return (
    <div className="mx-auto flex w-full max-w-[90rem] flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="Renewals"
        crumbs={[{ label: "Sales Orders", href: "/sales" }]}
        description={`Who advertised with a title in ${year - 1} but hasn't booked it yet in ${year} - largest spend first.`}
        actions={<YearSwitch years={meta.years} current={year} href={(y) => href({ year: y })} />}
      />

      <nav aria-label="Choose a title" className="-mt-2 flex flex-wrap gap-1.5">
        {meta.titles.map((t) => {
          const active = t.id === title.id;
          return (
            <Link
              key={t.id}
              href={href({ title: t.id })}
              aria-current={active ? "true" : undefined}
              className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold transition-colors ${active ? "border-primary bg-primary text-primary-foreground" : "border-border text-muted-foreground hover:bg-muted hover:text-foreground"}`}
            >
              <TitleIcon line={t.product_line} className="size-3.5" />
              {t.name.replace(/\s*\(.*\)/, "")}
            </Link>
          );
        })}
      </nav>

      <section aria-label="Key figures" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile label={`${year - 1} advertisers`} value={data.previous_advertisers.toLocaleString("en-GB")} footer={`booked ${title.name} last year`} />
        <KpiTile label={`Back in ${year}`} value={data.rebooked.toLocaleString("en-GB")} footer="have booked again this year" />
        <KpiTile
          label="Retention so far"
          value={fmtPercent(data.retention_rate)}
          footer={
            <span className="flex items-center gap-1">
              of last year&apos;s advertisers
              <InfoHint>Matched on the client name, or the linked CRM company when there is one - so &ldquo;Air Canada&rdquo; and &ldquo;Air Canada Ltd&rdquo; count once when both are linked.</InfoHint>
            </span>
          }
        />
        <KpiTile label="Not back yet" value={fmtGBP(data.not_rebooked_value_gbp, { compact: true })} footer="their spend with this title last year" />
      </section>

      <div className="flex items-start gap-2.5 rounded-lg border border-primary/25 bg-primary/5 px-3.5 py-2.5 text-xs text-muted-foreground">
        <Sparkles className="mt-0.5 size-3.5 shrink-0 text-primary" aria-hidden="true" />
        <span>
          The <span className="font-semibold text-foreground">Renewal outreach</span> automation drafts a personal renewal email for each of
          these as the anniversary of their booking approaches, quoting what they booked - ready for the rep in the Review Queue.{" "}
          <Link href="/automations/revenue" className="font-semibold text-primary hover:underline">
            Revenue &amp; Orders automations →
          </Link>
        </span>
      </div>

      {data.items.length === 0 ? (
        <EmptyState icon={PartyPopper} title={data.previous_advertisers ? "Everyone's back" : `No ${year - 1} bookings for this title`}>
          {data.previous_advertisers
            ? `Every advertiser from ${year - 1} has booked ${title.name} again in ${year}.`
            : "There's nothing to compare against yet."}
        </EmptyState>
      ) : (
        <RenewalsTable data={data} editions={editions} reps={meta.reps} />
      )}
    </div>
  );
}
