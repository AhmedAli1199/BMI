import Link from "next/link";
import { CheckCircle2, Sparkles } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import { canUseAutomations } from "@/lib/access";
import type { OrdersPage, SalesMeta } from "@/lib/sales-types";
import { KpiTile } from "@/components/automations/hub-ui";
import { InfoHint } from "@/components/sales/info-hint";
import { OrdersTable } from "@/components/sales/orders-table";
import { EmptyState, SalesHeader, fmtGBP } from "@/components/sales/sales-ui";

const VIEWS = [
  {
    key: "overdue",
    label: "Overdue",
    query: "overdue=true",
    hint: "Booked, has a value, no invoice number - and the issue has already published or the event has already run.",
    empty: "Nothing overdue - every published edition's bookings have an invoice number.",
  },
  {
    key: "uninvoiced",
    label: "All awaiting invoice",
    query: "uninvoiced=true",
    hint: "Every live booking with a value and no invoice number yet, including editions still to come.",
    empty: "Every booking with a value has been invoiced.",
  },
  {
    key: "mismatched",
    label: "Unexplained difference",
    query: "mismatched=true",
    hint: "Invoiced for a different amount than the booking value (after any agency cut), with no reason recorded - the sheet's 'Invoice difference' column with its 'Reason for difference' left blank.",
    empty: "Every invoice matches its booking, or has a reason recorded for the difference.",
  },
  {
    key: "part",
    label: "Difference explained",
    query: "part_invoiced=true",
    hint: "The invoice differs from the booking and a reason is recorded (e.g. agency commission, a credit note, \"to be on next quarter invoice\"). Nothing to worry about - the reason is shown on each booking.",
    empty: "No invoice differences with a recorded reason.",
  },
  {
    key: "check",
    label: "Needs a check",
    query: "warnings=true",
    hint: "Rows the spreadsheet import couldn't read with certainty - a missing client name, an unknown salesperson, an unreadable amount. Open one and mark it checked once it's right.",
    empty: "No imported rows are waiting for a check.",
  },
  {
    key: "unlinked",
    label: "Not linked to CRM",
    query: "unlinked=true",
    hint: "Bookings whose client isn't linked to a CRM company yet. Linking shows the booking on the company's page and lets renewals reach the right record.",
    empty: "Every booking is linked to a CRM company (or confirmed as not in the CRM).",
  },
] as const;

export default async function InvoicingPage({ searchParams }: { searchParams: Promise<{ view?: string; year?: string }> }) {
  const sp = await searchParams;
  const view = VIEWS.find((v) => v.key === sp.view) ?? VIEWS[0];
  const [meta, session, current, overdue, mismatched, part] = await Promise.all([
    backendFetch<SalesMeta>("/api/sales/meta"),
    getSession(),
    backendFetch<OrdersPage>(`/api/sales/orders?${view.query}&limit=300`),
    backendFetch<OrdersPage>("/api/sales/orders?overdue=true&limit=1"),
    backendFetch<OrdersPage>("/api/sales/orders?mismatched=true&limit=1"),
    backendFetch<OrdersPage>("/api/sales/orders?part_invoiced=true&limit=1"),
  ]);
  const uninvoiced = view.key === "uninvoiced" ? current : await backendFetch<OrdersPage>("/api/sales/orders?uninvoiced=true&limit=1");

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
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
            const active = v.key === view.key;
            return (
              <Link
                key={v.key}
                href={`/sales/invoicing?view=${v.key}`}
                aria-current={active ? "page" : undefined}
                scroll={false}
                className={`rounded-lg px-2.5 py-1.5 text-xs font-semibold transition-colors ${active ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}
              >
                {v.label}
              </Link>
            );
          })}
          <InfoHint>{view.hint}</InfoHint>
        </nav>

        {current.total === 0 ? (
          <EmptyState icon={CheckCircle2} title="All clear">{view.empty}</EmptyState>
        ) : (
          <>
            {current.total > current.items.length && (
              <p className="mb-2 text-xs text-muted-foreground">Showing the {current.items.length} most recent of {current.total}.</p>
            )}
            <OrdersTable
              orders={current.items}
              reps={meta.reps}
              canDelete={canUseAutomations(session)}
              year={new Date().getFullYear()}
              showEdition
              showFilters={false}
            />
          </>
        )}
      </div>
    </div>
  );
}
