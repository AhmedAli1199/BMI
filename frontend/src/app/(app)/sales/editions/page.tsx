import Link from "next/link";
import { AlertTriangle, ChevronRight, Layers, Lock } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { EditionSummary, SalesMeta } from "@/lib/sales-types";
import { fmtPercent, pctChange } from "@/lib/automation-format";
import { Delta } from "@/components/automations/hub-ui";
import { NewEditionDialog } from "@/components/sales/new-edition-dialog";
import { EmptyState, PRODUCT_LINE_LABEL, SalesHeader, TitleIcon, YearSwitch, fmtDate, fmtGBP } from "@/components/sales/sales-ui";

export default async function EditionsPage({ searchParams }: { searchParams: Promise<{ year?: string; title?: string }> }) {
  const sp = await searchParams;
  const meta = await backendFetch<SalesMeta>("/api/sales/meta");
  const year = Number(sp.year) || new Date().getFullYear();
  const titleFilter = meta.titles.find((t) => t.id === sp.title) ?? null;
  const qs = new URLSearchParams({ year: String(year) });
  if (titleFilter) qs.set("title_id", titleFilter.id);
  const editions = await backendFetch<EditionSummary[]>(`/api/sales/editions?${qs}`);

  const groups = meta.titles
    .map((t) => ({ title: t, editions: editions.filter((e) => e.title.id === t.id) }))
    .filter((g) => g.editions.length > 0);
  const link = (params: { year?: number; title?: string | null }) => {
    const p = new URLSearchParams({ year: String(params.year ?? year) });
    const t = params.title === undefined ? titleFilter?.id : params.title;
    if (t) p.set("title", t);
    return `/sales/editions?${p}`;
  };
  const titlesWithEditions = new Set(editions.map((e) => e.title.id));

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="Editions"
        crumbs={[{ label: "Sales Orders", href: "/sales" }]}
        description="One row per issue, month of online sales or event - what used to be one sheet in a title's SOR workbook."
        actions={
          <>
            <YearSwitch years={meta.years} current={year} href={(y) => link({ year: y })} />
            <NewEditionDialog titles={meta.titles} year={year} defaultTitleId={titleFilter?.id} />
          </>
        }
      />

      <nav aria-label="Filter by title" className="-mt-2 flex flex-wrap gap-1.5">
        <Link
          href={link({ title: null })}
          aria-current={!titleFilter ? "true" : undefined}
          className={`rounded-full border px-3 py-1 text-xs font-semibold transition-colors ${!titleFilter ? "border-primary bg-primary text-primary-foreground" : "border-border text-muted-foreground hover:bg-muted hover:text-foreground"}`}
        >
          All titles
        </Link>
        {meta.titles
          .filter((t) => titleFilter?.id === t.id || titlesWithEditions.has(t.id) || !titleFilter)
          .map((t) => {
            const active = titleFilter?.id === t.id;
            return (
              <Link
                key={t.id}
                href={link({ title: t.id })}
                aria-current={active ? "true" : undefined}
                className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold transition-colors ${active ? "border-primary bg-primary text-primary-foreground" : "border-border text-muted-foreground hover:bg-muted hover:text-foreground"}`}
              >
                <TitleIcon line={t.product_line} className="size-3.5" />
                {t.name.replace(/\s*\(.*\)/, "")}
              </Link>
            );
          })}
      </nav>

      {groups.length === 0 && (
        <EmptyState icon={Layers} title={`No editions for ${titleFilter ? titleFilter.name : "any title"} in ${year}`}>
          Create one with &ldquo;New edition&rdquo; - it takes the place of copying the template sheet in the old workbook.
        </EmptyState>
      )}

      {groups.map(({ title, editions: eds }) => {
        const total = eds.reduce((s, e) => s + e.booked_gbp, 0);
        // Same point last year, so a title still selling isn't compared with last year's finished totals.
        const prevPoint = eds.reduce((s, e) => s + (e.previous_same_point_gbp ?? 0), 0);
        return (
          <details key={title.id} open={groups.length === 1} className="group overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs">
            <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 hover:bg-accent/30 [&::-webkit-details-marker]:hidden">
              <ChevronRight className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-90" aria-hidden="true" />
              <span className="text-muted-foreground">
                <TitleIcon line={title.product_line} />
              </span>
              <span className="text-sm font-bold text-foreground">{title.name}</span>
              <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">{PRODUCT_LINE_LABEL[title.product_line]}</span>
              <span className="ml-auto flex items-center gap-3 text-xs text-muted-foreground">
                <span>{eds.length} edition{eds.length === 1 ? "" : "s"}</span>
                {eds.some((e) => e.uninvoiced > 0) && (
                  <span style={{ color: "var(--warn)" }}>{eds.reduce((n, e) => n + e.uninvoiced, 0)} to invoice</span>
                )}
                <span>
                  <span className="font-semibold text-foreground tabular-nums">{fmtGBP(total)}</span> booked
                </span>
                {prevPoint > 0 && (
                  <span title="vs the same editions last year, at the same point">
                    <Delta change={pctChange(total, prevPoint)} goodWhenUp />
                  </span>
                )}
              </span>
            </summary>
            <div className="overflow-x-auto border-t border-border/70">
              <table className="w-full min-w-[760px] text-sm">
                <caption className="sr-only">{title.name} editions in {year}</caption>
                <thead>
                  <tr className="border-b border-border/70 text-left text-xs font-semibold text-muted-foreground">
                    <th scope="col" className="px-4 py-2.5 font-semibold">Edition</th>
                    <th scope="col" className="px-3 py-2.5 font-semibold">Date</th>
                    <th scope="col" className="px-3 py-2.5 text-right font-semibold">Bookings</th>
                    <th scope="col" className="px-3 py-2.5 text-right font-semibold">Booked</th>
                    <th scope="col" className="px-3 py-2.5 font-semibold">vs last year</th>
                    <th scope="col" className="px-3 py-2.5 text-right font-semibold">Invoiced</th>
                    <th scope="col" className="px-4 py-2.5 font-semibold"><span className="sr-only">Flags</span></th>
                  </tr>
                </thead>
                <tbody>
                  {eds.map((e) => {
                    const cmp = e.previous_same_point_gbp;
                    return (
                      <tr key={e.id} className="relative border-b border-border/60 last:border-0 hover:bg-accent/40">
                        <td className="px-4 py-2.5">
                          <Link href={`/sales/editions/${e.id}`} className="font-semibold text-foreground after:absolute after:inset-0">
                            {e.label}
                          </Link>
                          {e.period_label && e.period_label !== e.name && <div className="max-w-xs truncate text-[11px] text-muted-foreground">{e.period_label}</div>}
                        </td>
                        <td className="px-3 py-2.5 text-xs whitespace-nowrap text-muted-foreground">{fmtDate(e.edition_date)}</td>
                        <td className="px-3 py-2.5 text-right tabular-nums">{e.orders}</td>
                        <td className="px-3 py-2.5 text-right font-semibold tabular-nums">{fmtGBP(e.booked_gbp)}</td>
                        <td className="px-3 py-2.5 text-xs">
                          {e.previous ? (
                            <span className="flex items-center gap-1.5">
                              {cmp ? <Delta change={pctChange(e.booked_gbp, cmp)} goodWhenUp /> : <span className="text-muted-foreground">—</span>}
                              <span className="text-muted-foreground">{fmtGBP(e.previous_booked_gbp, { compact: true })} final</span>
                            </span>
                          ) : (
                            <span className="text-muted-foreground">No match</span>
                          )}
                        </td>
                        <td className="px-3 py-2.5 text-right text-xs tabular-nums">{fmtPercent(e.booked_gbp ? e.invoiced_gbp / e.booked_gbp : null)}</td>
                        <td className="px-4 py-2.5">
                          <div className="flex items-center justify-end gap-2 text-[11px]">
                            {e.uninvoiced > 0 && (
                              <span className="rounded-full px-1.5 py-0.5 font-semibold" style={{ color: "var(--warn)", background: "color-mix(in oklab, var(--warn) 12%, transparent)" }}>
                                {e.uninvoiced} to invoice
                              </span>
                            )}
                            {e.warnings > 0 && (
                              <span className="flex items-center gap-0.5" style={{ color: "var(--warn)" }} title={`${e.warnings} imported row(s) need a check`}>
                                <AlertTriangle className="size-3.5" aria-hidden="true" />
                                <span className="sr-only">{e.warnings} rows need a check</span>
                              </span>
                            )}
                            {e.status === "closed" && (
                              <span className="flex items-center gap-0.5 text-muted-foreground" title="Closed - no longer taking bookings">
                                <Lock className="size-3" aria-hidden="true" /> Closed
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </details>
        );
      })}
    </div>
  );
}
