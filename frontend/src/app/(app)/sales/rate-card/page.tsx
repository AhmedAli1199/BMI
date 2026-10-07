import Link from "next/link";
import { AlertTriangle, CheckCircle2, ChevronRight, Circle, Download } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { RateOverview } from "@/lib/rate-card-types";
import { Button } from "@/components/ui/button";
import { InfoHint } from "@/components/sales/info-hint";
import { SalesHeader, YearSwitch, fmtDate } from "@/components/sales/sales-ui";
import { brandColor } from "@/components/rate-card/brand-style";

/** The rate card home: BMI's three brands, laid out like their media packs.
 * Proposals and renewal emails quote these prices, so this is the one place to keep them right. */
export default async function RateCardPage({ searchParams }: { searchParams: Promise<{ year?: string }> }) {
  const sp = await searchParams;
  const data = await backendFetch<RateOverview>(`/api/rate-card${sp.year ? `?year=${Number(sp.year)}` : ""}`);
  const { year, brands } = data;
  const steps = [
    { done: brands.every((b) => b.products > 0), label: "Put each brand's prices in", hint: "Load them from the media pack with one click, or add them one by one." },
    { done: brands.every((b) => b.products > 0 && b.needs_check === 0), label: "Check every price marked “Please check”", hint: "Prices we read from the media packs wait for a person to say they're right." },
    { done: brands.some((b) => b.offers > 0), label: "Add your offers and discounts", hint: "e.g. Book 2 adverts save 10% - the proposal builder applies them for you." },
  ];
  const allDone = steps.every((s) => s.done);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="Rate card"
        crumbs={[{ label: "Sales Orders", href: "/sales" }]}
        description="Every brand's prices, laid out like your media packs. Proposals and renewal emails quote these prices - nothing is ever priced from a guess. All prices are before VAT."
        actions={
          <>
            <Button variant="outline" size="sm" className="gap-1.5" nativeButton={false} render={<a href={`/api/files/rate-card/export.xlsx?year=${year}`} download />}>
              <Download className="size-3.5" /> Download all as Excel
            </Button>
            <YearSwitch years={data.years} current={year} href={(y) => `/sales/rate-card?year=${y}`} />
          </>
        }
      />

      {!allDone && (
        <section aria-labelledby="start-h" className="rounded-xl border border-border/80 bg-card p-4 shadow-2xs">
          <h2 id="start-h" className="text-sm font-bold">Getting your {year} rate card ready</h2>
          <ol className="mt-3 grid gap-3 sm:grid-cols-3">
            {steps.map((s, i) => (
              <li key={s.label} className="flex gap-2.5">
                {s.done ? <CheckCircle2 className="mt-0.5 size-4 shrink-0" style={{ color: "var(--ok)" }} aria-hidden="true" /> : <Circle className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />}
                <div>
                  <p className={`text-sm font-semibold ${s.done ? "text-muted-foreground line-through" : ""}`}>{i + 1}. {s.label}<span className="sr-only">{s.done ? " (done)" : " (to do)"}</span></p>
                  <p className="text-xs text-muted-foreground">{s.hint}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>
      )}

      <section aria-label="Brands" className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs">
        <ul className="divide-y divide-border/70">
          {brands.map((b) => (
            <li key={b.key}>
              <Link href={`/sales/rate-card/${b.key}?year=${year}`} className="group flex items-stretch gap-4 px-4 py-4 hover:bg-muted/40 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring">
                <span className="masthead-rule w-1 self-stretch !h-auto" style={{ background: brandColor(b.key) }} aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <p className="text-base font-bold">{b.name}</p>
                  <p className="text-xs text-muted-foreground">{b.website}</p>
                  <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
                    <span><strong className="tabular-nums">{b.products}</strong> price{b.products === 1 ? "" : "s"}{b.on_request ? <span className="text-muted-foreground"> ({b.on_request} on request)</span> : null}</span>
                    <span><strong className="tabular-nums">{b.offers}</strong> offer{b.offers === 1 ? "" : "s"}</span>
                    {b.needs_check > 0 && (
                      <span className="inline-flex items-center gap-1 font-semibold" style={{ color: "var(--warn)" }}>
                        <AlertTriangle className="size-3.5" aria-hidden="true" /> {b.needs_check} to check
                      </span>
                    )}
                    {b.products === 0 && b.seed_available > 0 && <span className="font-semibold text-primary">{b.seed_available} prices ready to load from the media pack</span>}
                    {b.last_updated && <span className="text-muted-foreground">Last changed {fmtDate(b.last_updated.slice(0, 10))}</span>}
                    {!b.can_edit && <span className="text-muted-foreground">View only</span>}
                  </p>
                </div>
                <ChevronRight className="size-5 self-center text-muted-foreground transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ul>
      </section>
      <p className="flex items-center gap-1 text-xs text-muted-foreground">
        Who can change prices
        <InfoHint>Admins and data managers can change every brand. Each brand&apos;s publishers can change their own brand: Sue Williams and Craig McQuinn (Onboard Hospitality), Kirsty Hicks (The Business Travel Magazine), Sally Parker, Steven Thompson and David Wilcox (Selling Travel). Everyone can view.</InfoHint>
      </p>
    </div>
  );
}
