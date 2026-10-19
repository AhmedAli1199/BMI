import Link from "next/link";
import { GitCompare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { backendFetch } from "@/lib/backend";
import type { EditionSummary, SalesMeta } from "@/lib/sales-types";
import { NewEditionDialog } from "@/components/sales/new-edition-dialog";
import { EditionsExplorer } from "@/components/sales/editions-explorer";
import { SalesHeader, YearSwitch } from "@/components/sales/sales-ui";
import { getSession } from "@/lib/session";
import { canUseAutomations } from "@/lib/access";

export default async function EditionsPage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const staff = canUseAutomations(await getSession());
  const sp = await searchParams;
  const meta = await backendFetch<SalesMeta>("/api/sales/meta");
  // A financial year (from the overview's "All editions" in financial-year mode): ?from=2026-07-01&to=2027-06-30.
  // Editions go by their date; an undated one counts from 1 January of its year (the same rule as the overview).
  const iso = /^\d{4}-\d{2}-\d{2}$/;
  const range = sp.from && sp.to && iso.test(sp.from) && iso.test(sp.to) && sp.from <= sp.to ? { from: sp.from, to: sp.to } : null;
  const year = range ? Number(range.from.slice(0, 4)) : Number(sp.year) || new Date().getFullYear();
  const lastYear = range ? Number(range.to.slice(0, 4)) : year;
  // Every edition of the year (or of the financial year's two calendar years) comes down once; the sidebar filters it in the browser.
  const fetched = (
    await Promise.all(
      Array.from({ length: Math.min(lastYear - year, 2) + 1 }, (_, i) => backendFetch<EditionSummary[]>(`/api/sales/editions?year=${year + i}`)),
    )
  ).flat();
  const editions = range
    ? fetched.filter((e) => {
        const d = e.edition_date ?? `${e.year}-01-01`;
        return d >= range.from && d <= range.to;
      })
    : fetched;
  const periodLabel = range ? (lastYear === year + 1 ? `${year}/${String(lastYear).slice(2)}` : `${range.from} to ${range.to}`) : String(year);
  const titleIds = (sp.title ?? "").split(",").filter(Boolean);
  // Keep the other filters when switching year (a calendar year replaces a financial-year view).
  const yearHref = (y: number) => {
    const p = new URLSearchParams(Object.entries(sp).filter(([k, v]) => v && k !== "from" && k !== "to") as [string, string][]);
    p.set("year", String(y));
    return `/sales/editions?${p}`;
  };

  return (
    <div className="mx-auto flex w-full max-w-[90rem] flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="Editions"
        crumbs={[{ label: "Sales Orders", href: "/sales" }]}
        description={
          range
            ? `The financial year ${periodLabel}: editions published or held from ${new Date(range.from).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })} to ${new Date(range.to).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}. Pick a year to see a calendar year instead.`
            : "One row per issue, month of online sales or event - what used to be one sheet in a title's SOR workbook."
        }
        actions={
          <>
            <YearSwitch years={meta.years} current={range ? NaN : year} href={yearHref} />
            <Button size="sm" variant="outline" className="gap-1.5" nativeButton={false} render={<Link href="/sales/compare" />}>
              <GitCompare className="size-3.5" aria-hidden="true" /> Compare editions
            </Button>
            {staff && <NewEditionDialog titles={meta.titles} year={year} defaultTitleId={titleIds.length === 1 ? titleIds[0] : undefined} />}
          </>
        }
      />
      {/* Titles come from the editions themselves, so a retired title's old editions still have a heading. */}
      <EditionsExplorer
        editions={editions}
        titles={[
          ...meta.titles.filter((t) => editions.some((e) => e.title.id === t.id)),
          ...[...new Map(editions.filter((e) => !meta.titles.some((t) => t.id === e.title.id)).map((e) => [e.title.id, e.title])).values()],
        ]}
        year={periodLabel}
      />
    </div>
  );
}
