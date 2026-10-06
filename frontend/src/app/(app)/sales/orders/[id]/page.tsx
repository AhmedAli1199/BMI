import Link from "next/link";
import { notFound } from "next/navigation";
import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import { canUseAutomations } from "@/lib/access";
import type { SalesMeta, SalesOrder } from "@/lib/sales-types";
import { BookingEditor } from "@/components/sales/booking-editor";
import { XeroPayment } from "@/components/sales/orders-table";
import { OrderStatusPill, SalesHeader, fmtDate, fmtGBP } from "@/components/sales/sales-ui";

/** One booking on its own page - what the review queue's "Open booking" links
 * to, so a booking can be checked in a new tab without losing your place. */
export default async function BookingPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let o: SalesOrder;
  try {
    o = await backendFetch<SalesOrder>(`/api/sales/orders/${id}`);
  } catch {
    notFound();
  }
  const [meta, session] = await Promise.all([backendFetch<SalesMeta>("/api/sales/meta"), getSession()]);
  const year = o.edition_date ? new Date(o.edition_date).getFullYear() : new Date().getFullYear();

  const rows: [string, React.ReactNode][] = [
    ["Edition", <Link key="e" href={`/sales/editions/${o.edition_id}`} className="font-semibold text-primary hover:underline">{o.edition_label}</Link>],
    ["Published or held", fmtDate(o.edition_date)],
    ["What was sold", [o.size, o.series, o.position].filter(Boolean).join(" · ") || "—"],
    ["Booked on", fmtDate(o.booked_on)],
    ["Salesperson", o.rep ? o.rep.name : "—"],
    ["Value", <span key="v" className="font-semibold tabular-nums">{fmtGBP(o.value_gbp)}</span>],
    [
      "Invoice",
      o.invoice_number ? (
        <span key="i" className="flex flex-wrap items-center gap-x-2">
          <span className="font-semibold">{o.invoice_number}</span>
          {o.invoiced_on && <span className="text-muted-foreground">dated {fmtDate(o.invoiced_on)}</span>}
          <XeroPayment o={o} />
          {o.xero?.url && (
            <a href={o.xero.url} target="_blank" rel="noreferrer" className="font-semibold text-primary hover:underline">
              Open in Xero
            </a>
          )}
        </span>
      ) : (
        "Not invoiced yet"
      ),
    ],
  ];

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <SalesHeader
        title={o.client_name}
        crumbs={[
          { label: "Sales Orders", href: "/sales" },
          { label: o.edition_label, href: `/sales/editions/${o.edition_id}` },
        ]}
        eyebrow={<OrderStatusPill status={o.status} />}
        description={o.company ? <>CRM company: <Link href={`/companies/${o.company.id}`} className="font-semibold text-primary hover:underline">{o.company.label}</Link></> : "Not linked to a CRM company."}
        actions={<BookingEditor order={o} reps={meta.reps} canDelete={canUseAutomations(session)} year={year} />}
      />
      <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2.5 rounded-xl border border-border/80 bg-card p-5 text-sm shadow-2xs">
        {rows.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-muted-foreground">{label}</dt>
            <dd className="text-foreground">{value}</dd>
          </div>
        ))}
        {o.notes && (
          <div className="contents">
            <dt className="text-muted-foreground">Notes</dt>
            <dd className="whitespace-pre-wrap text-foreground">{o.notes}</dd>
          </div>
        )}
      </dl>
    </div>
  );
}
