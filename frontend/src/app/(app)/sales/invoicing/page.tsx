import Link from "next/link";
import { CheckCircle2, Sparkles } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import { canUseAutomations } from "@/lib/access";
import type { OrdersPage, SalesMeta, UnmatchedInvoices } from "@/lib/sales-types";
import { LinkInvoiceButton } from "@/components/sales/xero-link-dialogs";
import type { OrderFilterKey } from "@/lib/sales-filters";
import { KpiTile } from "@/components/automations/hub-ui";
import { InfoHint } from "@/components/sales/info-hint";
import { OrdersExplorer } from "@/components/sales/orders-explorer";
import { EmptyState, SalesHeader, fmtDate, fmtGBP } from "@/components/sales/sales-ui";
import { ExternalLink } from "lucide-react";

const VIEWS = [
  {
    key: "overdue",
    label: "Overdue",
    query: "overdue=true",
    scope: { overdue: "true" },
    hide: ["invoiced"] as OrderFilterKey[],
    hint: "Booked, has a value, no invoice number - and the issue has already published or the event has already run.",
    empty: "Nothing overdue - every published edition's bookings have an invoice number.",
  },
  {
    key: "uninvoiced",
    label: "All awaiting invoice",
    query: "uninvoiced=true",
    scope: { uninvoiced: "true" },
    hide: ["invoiced"] as OrderFilterKey[],
    hint: "Every live booking with a value and no invoice number yet, including editions still to come.",
    empty: "Every booking with a value has been invoiced.",
  },
  {
    key: "mismatched",
    label: "Unexplained difference",
    query: "mismatched=true",
    scope: { mismatched: "true" },
    hide: ["invoiced", "status"] as OrderFilterKey[],
    hint: "Invoiced for a different amount than the booking value (after any agency cut), with no reason recorded - the sheet's 'Invoice difference' column with its 'Reason for difference' left blank.",
    empty: "Every invoice matches its booking, or has a reason recorded for the difference.",
  },
  {
    key: "part",
    label: "Difference explained",
    query: "part_invoiced=true",
    scope: { part_invoiced: "true" },
    hide: ["invoiced", "status"] as OrderFilterKey[],
    hint: "The invoice differs from the booking and a reason is recorded (e.g. agency commission, a credit note, \"to be on next quarter invoice\"). Nothing to worry about - the reason is shown on each booking.",
    empty: "No invoice differences with a recorded reason.",
  },
  {
    key: "check",
    label: "Needs a check",
    query: "warnings=true",
    scope: { has_warning: "true" },
    hide: ["check"] as OrderFilterKey[],
    hint: "Rows the spreadsheet import couldn't read with certainty - a missing client name, an unknown salesperson, an unreadable amount. Open one and mark it checked once it's right.",
    empty: "No imported rows are waiting for a check.",
  },
  {
    key: "unlinked",
    label: "Not linked to CRM",
    query: "unlinked=true",
    scope: { unlinked: "true" },
    hide: ["linked"] as OrderFilterKey[],
    hint: "Every booking whose client isn't linked to a CRM company yet - one row per booking, so a client with 12 bookings appears 12 times. Only clients that closely resemble an existing CRM company get a “Is this the same company?” item in the Review Queue (one item per client, up to 200 at a time); clients with no likely match in the CRM are listed here but never queued. Linking shows the booking on the company's page and lets renewals reach the right record.",
    empty: "Every booking is linked to a CRM company (or confirmed as not in the CRM).",
  },
] as const;

export default async function InvoicingPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const sp = await searchParams;
  const xeroOnly = sp.view === "xero_only";
  const view = VIEWS.find((v) => v.key === sp.view) ?? VIEWS[0];
  const [meta, session, current, overdue, mismatched, part, unmatched] = await Promise.all([
    backendFetch<SalesMeta>("/api/sales/meta"),
    getSession(),
    backendFetch<OrdersPage>(`/api/sales/orders?${view.query}&limit=1`),
    backendFetch<OrdersPage>("/api/sales/orders?overdue=true&limit=1"),
    backendFetch<OrdersPage>("/api/sales/orders?mismatched=true&limit=1"),
    backendFetch<OrdersPage>("/api/sales/orders?part_invoiced=true&limit=1"),
    backendFetch<UnmatchedInvoices>("/api/sales/xero/unmatched").catch(() => ({ as_of: null, items: [] }) as UnmatchedInvoices),
  ]);
  const uninvoiced = view.key === "uninvoiced" ? current : await backendFetch<OrdersPage>("/api/sales/orders?uninvoiced=true&limit=1");
  // Switching view keeps the sidebar filters (e.g. one title, one person) but starts at page 1.
  const viewHref = (key: string) => {
    const p = new URLSearchParams();
    for (const [k, v] of Object.entries(sp)) if (typeof v === "string" && v && k !== "view" && k !== "page") p.set(k, v);
    p.set("view", key);
    return `/sales/invoicing?${p}`;
  };

  return (
    <div className="mx-auto flex w-full max-w-[90rem] flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title="Invoicing"
        crumbs={[{ label: "Sales Orders", href: "/sales" }]}
        description="Bookings that still need an invoice, invoices that don't match their booking, and imported rows to double-check."
      />

      <section aria-label="Key figures" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile label="Overdue" value={overdue.total.toLocaleString("en-GB")} footer={`${fmtGBP(overdue.total_value_gbp, { compact: true })} published or held, not yet invoiced`} />
        <KpiTile label="Awaiting invoice" value={uninvoiced.total.toLocaleString("en-GB")} footer={`${fmtGBP(uninvoiced.total_value_gbp, { compact: true })} across all editions`} />
        <KpiTile label="Difference explained" value={part.total.toLocaleString("en-GB")} footer="Invoice differs, reason recorded" />
        <KpiTile label="Unexplained difference" value={mismatched.total.toLocaleString("en-GB")} footer="Invoice differs, no reason given" />
      </section>

      <div className="flex items-start gap-2.5 rounded-lg border border-primary/25 bg-primary/5 px-3.5 py-2.5 text-xs text-muted-foreground">
        <Sparkles className="mt-0.5 size-3.5 shrink-0 text-primary" aria-hidden="true" />
        <span>
          The <span className="font-semibold text-foreground">Uninvoiced booking scan</span> can put overdue bookings straight into the
          Review Queue, where recording the invoice number takes one click.{" "}
          <Link href="/automations/revenue" className="font-semibold text-primary hover:underline">
            Revenue &amp; Orders automations →
          </Link>
        </span>
      </div>

      <div>
        <nav aria-label="Invoicing views" className="mb-3 flex flex-wrap items-center gap-1">
          {VIEWS.map((v) => {
            const active = !xeroOnly && v.key === view.key;
            return (
              <Link
                key={v.key}
                href={viewHref(v.key)}
                aria-current={active ? "page" : undefined}
                scroll={false}
                className={`rounded-lg px-2.5 py-1.5 text-xs font-semibold transition-colors ${active ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}
              >
                {v.label}
              </Link>
            );
          })}
          <Link
            href={viewHref("xero_only")}
            aria-current={xeroOnly ? "page" : undefined}
            scroll={false}
            className={`rounded-lg px-2.5 py-1.5 text-xs font-semibold transition-colors ${xeroOnly ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}
          >
            In Xero, not in the register{unmatched.items.length > 0 ? ` (${unmatched.items.length})` : ""}
          </Link>
          <InfoHint>
            {xeroOnly
              ? "Sales invoices in Xero that don't fit any booking in the register - billed but never entered, or the amount doesn't line up with a booking. Updated each time invoices are matched."
              : view.hint}
          </InfoHint>
        </nav>

        {xeroOnly ? (
          unmatched.items.length === 0 ? (
            <EmptyState icon={CheckCircle2} title="Every invoice has a booking">
              {unmatched.as_of ? "Every sales invoice in Xero is linked to a booking, or waiting in the Review Queue." : "Invoices are matched once the Xero matching has run - switch it on in the Automations settings, or use Run now."}
            </EmptyState>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-border/80 bg-card shadow-2xs">
              <table className="w-full min-w-[52rem] text-sm">
                <caption className="sr-only">Invoices in Xero with no matching booking</caption>
                <thead>
                  <tr className="border-b border-border/70 text-left text-xs font-semibold text-muted-foreground">
                    <th scope="col" className="px-4 py-2.5 font-semibold">Invoice</th>
                    <th scope="col" className="px-3 py-2.5 font-semibold">Customer</th>
                    <th scope="col" className="px-3 py-2.5 font-semibold">What it says it&apos;s for</th>
                    <th scope="col" className="px-3 py-2.5 text-right font-semibold">Before VAT</th>
                    <th scope="col" className="px-3 py-2.5 font-semibold">Dated</th>
                    <th scope="col" className="px-4 py-2.5"><span className="sr-only">Link</span></th>
                  </tr>
                </thead>
                <tbody>
                  {unmatched.items.map((i) => (
                    <tr key={i.id} className="border-b border-border/60 align-top last:border-0 hover:bg-accent/40">
                      <td className="px-4 py-2.5">
                        <a href={i.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold text-primary hover:underline">
                          {i.number}
                          <ExternalLink className="size-3" aria-hidden="true" />
                        </a>
                      </td>
                      <td className="px-3 py-2.5 font-medium text-foreground">{i.contact ?? "—"}</td>
                      <td className="max-w-md px-3 py-2.5 text-xs text-muted-foreground">{[i.reference, i.lines].filter(Boolean).join(" · ") || "—"}</td>
                      <td className="px-3 py-2.5 text-right font-semibold tabular-nums">
                        {i.currency === "GBP" ? fmtGBP(i.net) : `${i.currency} ${i.net.toLocaleString("en-GB")}`}
                      </td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">{fmtDate(i.issued_on)}</td>
                      <td className="px-4 py-2 text-right"><LinkInvoiceButton invoice={i} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : current.total === 0 ? (
          <EmptyState icon={CheckCircle2} title="All clear">{view.empty}</EmptyState>
        ) : (
          <OrdersExplorer
            searchParams={sp}
            meta={meta}
            canDelete={canUseAutomations(session)}
            scope={view.scope}
            hide={view.hide}
            year={new Date().getFullYear()}
            emptyText="No bookings in this view match these filters."
          />
        )}
      </div>
    </div>
  );
}
