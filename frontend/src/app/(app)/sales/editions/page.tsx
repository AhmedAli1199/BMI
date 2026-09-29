import { backendFetch } from "@/lib/backend";
import type { EditionSummary, SalesMeta } from "@/lib/sales-types";
import { NewEditionDialog } from "@/components/sales/new-edition-dialog";
import { EditionsExplorer } from "@/components/sales/editions-explorer";
import { SalesHeader, YearSwitch } from "@/components/sales/sales-ui";

export default async function EditionsPage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const sp = await searchParams;
  const meta = await backendFetch<SalesMeta>("/api/sales/meta");
  const year = Number(sp.year) || new Date().getFullYear();
  // Every edition of the year comes down once; the sidebar filters it in the browser.
  const editions = await backendFetch<EditionSummary[]>(`/api/sales/editions?year=${year}`);
  const titleIds = (sp.title ?? "").split(",").filter(Boolean);
  // Keep the other filters when switching year.
  const yearHref = (y: number) => {
    const p = new URLSearchParams(Object.entries(sp).filter(([, v]) => v) as [string, string][]);
    p.set("year", String(y));
    return `/sales/editions?${p}`;
  };

  return (
    <div className="mx-auto flex w-full max-w-[90rem] flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="Editions"
        crumbs={[{ label: "Sales Orders", href: "/sales" }]}
        description="One row per issue, month of online sales or event - what used to be one sheet in a title's SOR workbook."
        actions={
          <>
            <YearSwitch years={meta.years} current={year} href={yearHref} />
            <NewEditionDialog titles={meta.titles} year={year} defaultTitleId={titleIds.length === 1 ? titleIds[0] : undefined} />
          </>
        }
      />
      <EditionsExplorer editions={editions} titles={meta.titles.filter((t) => editions.some((e) => e.title.id === t.id))} year={year} />
    </div>
  );
}
