import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronLeft, ChevronRight, Download, Info } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import { canUseAutomations } from "@/lib/access";
import type { EditionDetail, SalesMeta } from "@/lib/sales-types";
import { fmtPercent, pctChange } from "@/lib/automation-format";
import { Button } from "@/components/ui/button";
import { KpiTile } from "@/components/automations/hub-ui";
import { EditionStatusButton } from "@/components/sales/edition-actions";
import { InfoHint } from "@/components/sales/info-hint";
import { OrdersExplorer } from "@/components/sales/orders-explorer";
import { AddBookingButton } from "@/components/sales/add-booking-button";
import { RenewalPassButton } from "@/components/sales/renewal-pass-button";
import { EditionLinkButton } from "@/components/sales/edition-link-button";
import { PRODUCT_LINE_LABEL, SalesHeader, TitleIcon, fmtDate, fmtGBP } from "@/components/sales/sales-ui";

function ChangeValue({ change }: { change: number | null }) {
  if (change === null) return <>—</>;
  const pctv = Math.round(change * 100);
  return (
    <span style={{ color: pctv > 0 ? "var(--ok)" : pctv < 0 ? "var(--warn)" : undefined }}>
      {pctv > 0 ? "+" : ""}
      {pctv}%
    </span>
  );
}

export default async function EditionPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const [{ id }, sp] = await Promise.all([params, searchParams]);
  let ed: EditionDetail;
  try {
    ed = await backendFetch<EditionDetail>(`/api/sales/editions/${id}`);
  } catch {
    notFound();
  }
  const [meta, session] = await Promise.all([backendFetch<SalesMeta>("/api/sales/meta"), getSession()]);
  const staff = canUseAutomations(session);
  const isPrint = ed.title.product_line === "print";
  const cmp = ed.previous_same_point_gbp;
  const sheetDiff = ed.sheet_total_gbp !== null ? ed.booked_gbp - ed.sheet_total_gbp : 0;
  const repTotal = ed.by_rep.reduce((s, r) => s + r.amount_gbp, 0);

  return (
    <div className="mx-auto flex w-full max-w-[90rem] flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title={ed.label}
        crumbs={[
          { label: "Sales Orders", href: "/sales" },
          { label: `Editions ${ed.year}`, href: `/sales/editions?year=${ed.year}&title=${ed.title.id}` },
        ]}
        eyebrow={
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
            <span className="flex items-center gap-1 font-semibold text-foreground">
              <TitleIcon line={ed.title.product_line} className="size-3.5" />
              {ed.title.name}
            </span>
            <span aria-hidden="true">·</span>
            <span>{PRODUCT_LINE_LABEL[ed.title.product_line]}</span>
            {ed.period_label && ed.period_label !== ed.name && (
              <>
                <span aria-hidden="true">·</span>
                <span>{ed.period_label}</span>
              </>
            )}
            {ed.edition_date && (
              <>
                <span aria-hidden="true">·</span>
                <span>{fmtDate(ed.edition_date)}</span>
              </>
            )}
            {ed.exchange_rate && (
              <>
                <span aria-hidden="true">·</span>
                <span>US$ {ed.exchange_rate} to £1</span>
              </>
            )}
            {ed.status === "closed" && <span className="rounded-full bg-muted px-2 py-0.5 font-semibold">Closed</span>}
          </div>
        }
        actions={
          <>
            <div className="flex items-center rounded-lg border border-border/80 bg-card">
              {ed.prev_in_year ? (
                <Link href={`/sales/editions/${ed.prev_in_year.id}`} className="rounded-l-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground" aria-label={`Previous edition: ${ed.prev_in_year.label}`} title={ed.prev_in_year.label}>
                  <ChevronLeft className="size-4" />
                </Link>
              ) : (
                <span className="p-1.5 text-muted-foreground/40" aria-hidden="true"><ChevronLeft className="size-4" /></span>
              )}
              {ed.next_in_year ? (
                <Link href={`/sales/editions/${ed.next_in_year.id}`} className="rounded-r-lg border-l border-border/80 p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground" aria-label={`Next edition: ${ed.next_in_year.label}`} title={ed.next_in_year.label}>
                  <ChevronRight className="size-4" />
                </Link>
              ) : (
                <span className="border-l border-border/80 p-1.5 text-muted-foreground/40" aria-hidden="true"><ChevronRight className="size-4" /></span>
              )}
            </div>
            <Button size="sm" variant="outline" className="gap-1.5 font-semibold" nativeButton={false} render={<a href={`/api/sales/editions/${ed.id}/export`} download />}>
              <Download className="size-3.5" aria-hidden="true" /> Export .xlsx
            </Button>
            {staff && <EditionLinkButton editionId={ed.id} url={ed.digital_url} />}
            {staff && ed.renews_from && ed.status === "open" && (
              <RenewalPassButton editionId={ed.id} editionLabel={ed.label} renewsFrom={ed.renews_from.label} />
            )}
            <EditionStatusButton editionId={ed.id} status={ed.status} />
          </>
        }
      />

      <section aria-label="Key figures" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile
          label="Booked"
          value={fmtGBP(ed.booked_gbp, { compact: true })}
          footer={
            ed.target_gbp ? (
              <span className="flex flex-col gap-1">
                <span>{fmtPercent(ed.booked_gbp / ed.target_gbp)} of the {fmtGBP(ed.target_gbp, { compact: true })} target</span>
                <span className="h-1.5 rounded-full bg-muted" aria-hidden="true">
                  <span className="block h-full rounded-full" style={{ width: `${Math.min(100, (ed.booked_gbp / ed.target_gbp) * 100)}%`, background: "var(--chart-2)" }} />
                </span>
              </span>
            ) : (
              `${ed.orders} live bookings${ed.cancelled_or_moved ? ` · ${ed.cancelled_or_moved} cancelled or moved` : ""}`
            )
          }
        />
        <KpiTile
          label="vs last year's edition"
          value={<ChangeValue change={ed.previous && cmp ? pctChange(ed.booked_gbp, cmp) : null} />}
          footer={
            ed.previous ? (
              <span className="flex items-center gap-1">
                <Link href={`/sales/editions/${ed.previous.id}`} className="font-medium text-primary hover:underline">
                  {ed.previous.label}
                </Link>
                : {fmtGBP(cmp, { compact: true })} by now, {fmtGBP(ed.previous_booked_gbp, { compact: true })} final
                <InfoHint>
                  Last year&apos;s equivalent edition, counting only bookings it had taken by today&apos;s date a year ago - a fair
                  comparison while this one is still selling.
                </InfoHint>
              </span>
            ) : (
              "No equivalent edition last year"
            )
          }
        />
        <KpiTile
          label="Invoiced"
          value={fmtPercent(ed.booked_gbp ? ed.invoiced_gbp / ed.booked_gbp : null)}
          footer={
            <span className="flex items-center gap-1">
              {ed.invoiced_orders} of {ed.paid_orders} paid booking{ed.paid_orders === 1 ? "" : "s"} invoiced
              <InfoHint>
                The percentage is by value: £ invoiced out of £ booked - the same as the sheet&apos;s &ldquo;Total invoiced&rdquo;
                against its total. Bookings worth £0 (tickets, judges&apos; and guests&apos; seats, contra) have nothing to
                invoice, so they aren&apos;t counted either way.
              </InfoHint>
            </span>
          }
        />
        {isPrint ? (
          <KpiTile
            label="Pages sold"
            value={ed.pages.toLocaleString("en-GB", { maximumFractionDigits: 2 })}
            footer={ed.pages ? `Average ${fmtGBP(ed.booked_gbp / ed.pages, { compact: true })} a page` : "Worked out from each booking's size"}
          />
        ) : (
          <KpiTile label="Average booking" value={fmtGBP(ed.orders ? ed.booked_gbp / ed.orders : null, { compact: true })} footer={`${ed.orders} live bookings`} />
        )}
      </section>

      {ed.by_rep.length > 0 && (
        <section aria-label="Split by salesperson" className="flex flex-col gap-2 rounded-xl border border-border/80 bg-card px-4 py-3 shadow-2xs">
          <div className="flex items-center gap-1 text-xs font-semibold text-muted-foreground">
            By salesperson
            <InfoHint>Each person&apos;s credited share of this edition&apos;s live bookings - what the sheet&apos;s per-rep commission columns showed. Commission itself is on the Commissions page.</InfoHint>
          </div>
          <div className="flex h-2 overflow-hidden rounded-full bg-muted" aria-hidden="true">
            {ed.by_rep.map((r, i) => (
              <div key={r.rep_id} style={{ width: `${(r.amount_gbp / repTotal) * 100}%`, background: `var(--chart-${(i % 5) + 1})` }} />
            ))}
          </div>
          <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
            {ed.by_rep.map((r, i) => (
              <li key={r.rep_id} className="flex items-center gap-1.5">
                <span className="size-2 rounded-sm" style={{ background: `var(--chart-${(i % 5) + 1})` }} aria-hidden="true" />
                <span className="font-semibold text-foreground">{r.name}</span>
                <span className="tabular-nums text-muted-foreground">{fmtGBP(r.amount_gbp)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {ed.source && Math.abs(sheetDiff) > 1 && (
        <div className="flex items-start gap-2 rounded-lg border border-border/80 bg-muted/30 px-3 py-2.5 text-xs text-muted-foreground">
          <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
          <span>
            The original sheet&apos;s own total was {fmtGBP(ed.sheet_total_gbp)}; the bookings imported from it add up to{" "}
            {fmtGBP(ed.booked_gbp)}. This usually means the sheet&apos;s running-total formula stopped short - the bookings below are the complete list.
          </span>
        </div>
      )}

      <section aria-labelledby="bookings-heading" className="flex flex-col gap-2">
        <h2 id="bookings-heading" className="sr-only">Bookings</h2>
        <OrdersExplorer
          searchParams={sp}
          meta={meta}
          canDelete={staff}
          scope={{ edition_id: ed.id }}
          hide={["year", "title", "line", "edition"]}
          year={ed.year}
          showEdition={false}
          emptyText={ed.orders_list.length ? "No bookings in this edition match these filters." : "No bookings yet - add the first one."}
          actions={<AddBookingButton edition={{ editionId: ed.id, titleId: ed.title.id, editionLabel: ed.label, year: ed.year }} reps={meta.reps} />}
        />
        {ed.source && <p className="text-[11px] text-muted-foreground">Imported from {ed.source}.</p>}
      </section>
    </div>
  );
}
