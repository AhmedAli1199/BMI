import Link from "next/link";
import { GitCompare } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { CompareClient, CompareSide, EditionCompare, EditionSummary, SalesMeta } from "@/lib/sales-types";
import { pctChange } from "@/lib/automation-format";
import { Delta } from "@/components/automations/hub-ui";
import { ComparePicker } from "@/components/sales/compare-picker";
import { CompareChart, CompareLegend } from "@/components/sales/compare-chart";
import { EmptyState, SalesHeader, SectionTitle, fmtDate, fmtGBP } from "@/components/sales/sales-ui";

export default async function ComparePage({ searchParams }: { searchParams: Promise<{ a?: string; b?: string }> }) {
  const { a, b } = await searchParams;
  const meta = await backendFetch<SalesMeta>("/api/sales/meta");
  // The last few years' editions to pick from.
  const years = meta.years.slice(0, 4);
  const editions = (await Promise.all(years.map((y) => backendFetch<EditionSummary[]>(`/api/sales/editions?year=${y}`).catch(() => [])))).flat();
  const data = a && b ? await backendFetch<EditionCompare>(`/api/sales/editions/compare?a=${a}&b=${b}`).catch(() => null) : null;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="Compare editions"
        crumbs={[{ label: "Sales Orders", href: "/sales" }, { label: "Editions", href: "/sales/editions" }]}
        description="Any two issues or events side by side - this year's against last year's, or one event against another: what each sold, how fast it sold before it came out, and who was in one but not the other."
      />
      <ComparePicker editions={editions} a={a ?? null} b={b ?? null} />

      {!data ? (
        <EmptyState icon={GitCompare} title={a && b ? "Those editions couldn't be compared" : "Choose two editions"}>
          {a && b ? "One of them may have been removed. Pick them again above." : "Pick an edition on each side to see them next to each other."}
        </EmptyState>
      ) : (
        <>
          <section aria-label="Side by side" className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
            <table className="w-full min-w-[36rem] text-sm">
              <caption className="sr-only">The two editions compared</caption>
              <thead>
                <tr className="border-b border-border/70 text-left text-xs font-semibold text-muted-foreground">
                  <th scope="col" className="px-4 py-2.5 font-semibold"><span className="sr-only">Figure</span></th>
                  <Head s={data.a} />
                  <Head s={data.b} />
                  <th scope="col" className="px-4 py-2.5 text-right font-semibold">Difference</th>
                </tr>
              </thead>
              <tbody>
                <Row label="Booked" a={data.a.booked_gbp} b={data.b.booked_gbp} money />
                <Row label="Bookings" a={data.a.orders} b={data.b.orders} />
                <Row label="Advertisers" a={data.a.advertisers} b={data.b.advertisers} />
                <Row label="Average booking" a={data.a.average_gbp} b={data.b.average_gbp} money />
                {(data.a.pages > 0 || data.b.pages > 0) && <Row label="Pages sold" a={data.a.pages} b={data.b.pages} />}
                <Row label="Invoiced so far" a={data.a.invoiced_gbp} b={data.b.invoiced_gbp} money />
              </tbody>
            </table>
          </section>

          <section aria-labelledby="pace-h" className="rounded-xl border border-border/80 bg-card p-5 shadow-2xs">
            <SectionTitle
              id="pace-h"
              hint="Running total booked, lined up on each edition's own publication date, so two editions months apart are compared fairly. Bookings with no date count from the publication date."
              aside={<CompareLegend a={data.a.edition.label} b={data.b.edition.label} />}
            >
              How fast each sold
            </SectionTitle>
            <p className="sr-only">
              Eight weeks before publication: {fmtGBP(data.a.pace[data.weeks.indexOf(-8)])} for {data.a.edition.label} against{" "}
              {fmtGBP(data.b.pace[data.weeks.indexOf(-8)])} for {data.b.edition.label}.
            </p>
            <CompareChart weeks={data.weeks} a={data.a.pace} b={data.b.pace} />
          </section>

          <div className="grid gap-4 lg:grid-cols-3">
            <ClientList title={`In ${data.b.edition.label}, not in ${data.a.edition.label}`} hint="Advertised in the edition you're comparing with but not in this one - the ones to win back." rows={data.only_b} side="b" />
            <ClientList title={`New in ${data.a.edition.label}`} hint={`In this edition but not in ${data.b.edition.label}.`} rows={data.only_a} side="a" />
            <ClientList title="In both" hint="Advertised in both, with what they spent in each." rows={data.in_both} side="both" />
          </div>
        </>
      )}
    </div>
  );
}

function Head({ s }: { s: CompareSide }) {
  return (
    <th scope="col" className="px-3 py-2.5 text-right font-semibold">
      <Link href={`/sales/editions/${s.edition.id}`} className="text-foreground hover:text-primary hover:underline">{s.edition.label}</Link>
      <span className="block text-[11px] font-normal">{s.edition_date ? fmtDate(s.edition_date) : "No date"}</span>
    </th>
  );
}

function Row({ label, a, b, money = false }: { label: string; a: number | null; b: number | null; money?: boolean }) {
  const f = (v: number | null) => (v === null ? "—" : money ? fmtGBP(v) : v.toLocaleString("en-GB"));
  return (
    <tr className="border-b border-border/60 last:border-0">
      <th scope="row" className="px-4 py-2.5 text-left font-medium text-foreground">{label}</th>
      <td className="px-3 py-2.5 text-right font-semibold tabular-nums">{f(a)}</td>
      <td className="px-3 py-2.5 text-right tabular-nums text-muted-foreground">{f(b)}</td>
      <td className="px-4 py-2.5 text-right">{a !== null && b ? <Delta change={pctChange(a, b)} goodWhenUp /> : <span className="text-xs text-muted-foreground">—</span>}</td>
    </tr>
  );
}

function ClientList({ title, hint, rows, side }: { title: string; hint: string; rows: CompareClient[]; side: "a" | "b" | "both" }) {
  const total = rows.reduce((t, r) => t + (side === "b" ? r.b_gbp : r.a_gbp), 0);
  return (
    <section className="rounded-xl border border-border/80 bg-card shadow-2xs">
      <header className="border-b border-border/70 px-4 py-3">
        <h2 className="text-sm font-bold">{title}</h2>
        <p className="text-[11px] text-muted-foreground">{hint} {rows.length} · {fmtGBP(total)}</p>
      </header>
      {rows.length === 0 ? (
        <p className="px-4 py-4 text-sm text-muted-foreground">Nobody.</p>
      ) : (
        <ul className="max-h-96 divide-y divide-border/60 overflow-y-auto">
          {rows.map((r) => (
            <li key={r.client} className="flex items-baseline justify-between gap-3 px-4 py-2 text-sm">
              <span className="min-w-0 truncate font-medium text-foreground">{r.client}</span>
              <span className="shrink-0 tabular-nums text-muted-foreground">
                {side === "both" ? `${fmtGBP(r.a_gbp)} · was ${fmtGBP(r.b_gbp)}` : fmtGBP(side === "a" ? r.a_gbp : r.b_gbp)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
