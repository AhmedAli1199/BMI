import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { DealDocument } from "@/lib/deals-types";
import { PrintButton } from "@/components/deals/print-button";

const gbp = (v: number) => `£${v.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const longDate = (iso: string) => new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "2-digit" }).replace(/ /g, "-");
const box = "border border-foreground";

/** The order confirmation / schedule of works in BMI's own layout - print it or save it as a PDF from the browser. */
export default async function DealPrintPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let doc: DealDocument;
  try {
    doc = await backendFetch<DealDocument>(`/api/sales/deals/${id}/document`);
  } catch {
    notFound();
  }
  const company = doc.company_block.split("\n");
  const showTotal = !!(doc.discount || doc.agency || doc.package || doc.rows.length > 1);
  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-4 p-4 sm:p-6">
      <div className="print-hide flex items-center justify-between gap-2">
        <Link href={`/sales/deals/${id}`} className="inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline"><ChevronLeft className="size-4" /> Back to order {doc.number}</Link>
        <div className="flex items-center gap-2">
          {doc.status === "pencilled" && <span className="text-xs" style={{ color: "var(--warn)" }}>This order is still pencilled - confirm it before sending.</span>}
          <PrintButton />
        </div>
      </div>

      <article className="bg-card px-8 py-10 text-[13px] leading-snug text-foreground shadow-sm print:px-0 print:py-0 print:shadow-none" style={{ fontFamily: "Arial, Helvetica, sans-serif" }}>
        <header className="flex items-start justify-between gap-6">
          <div>
            <h1 className="text-[28px] font-bold leading-none tracking-tight">{doc.heading}</h1>
            {doc.subheading && <p className="mt-1 pl-14 text-base font-bold">{doc.subheading}</p>}
            <p className="mt-8"><span className="mr-8">Date.</span>{longDate(doc.date)}</p>
          </div>
          <address className="text-[13px] not-italic">
            <strong className="text-sm font-black uppercase">{company[0]}</strong>
            {company.slice(1).map((l, i) => <div key={i}>{l}</div>)}
          </address>
        </header>

        <div className="mt-6 grid grid-cols-2 gap-10">
          {[["Confirmation address", doc.confirmation_address], ["Invoice to:", doc.invoice_to]].map(([label, text]) => (
            <div key={label} className={`${box} min-h-36 px-2 py-1`}>
              <div className="text-xs underline">{label}</div>
              {(text || "").split("\n").map((l, i) => <div key={i} className="font-bold">{l}</div>)}
            </div>
          ))}
        </div>

        <div className="mt-3 grid grid-cols-2 gap-10">
          <div className="flex flex-col gap-2">
            <div className={`${box} flex px-2 py-0.5`}><span className="w-28 text-xs">Your contact.</span><span className="flex-1 text-center">{doc.your_contact}</span></div>
            <div className={`${box} flex px-2 py-0.5`}><span className="w-28 text-xs">Our contact.</span><span className="flex-1 text-center">{doc.our_contact}</span></div>
          </div>
          <div className="flex flex-col gap-2">
            <div className={`${box} flex px-2 py-0.5`}><span className="w-28 text-xs">Email.</span><span className="flex-1 truncate text-center text-primary underline">{doc.your_email}</span></div>
            <div className={`${box} flex px-2 py-0.5`}><span className="w-28 text-xs">Order no.</span><span className="flex-1 text-center">{doc.number}{doc.order_ref ? ` · your ref ${doc.order_ref}` : ""}</span></div>
          </div>
        </div>

        <p className="mt-5">{doc.intro}</p>
        <p className="mt-4"><span className="mr-12">{doc.document === "schedule" ? "Product" : "Publication"}</span><strong>{doc.publication}</strong></p>

        <div className={`${box} mt-3 min-h-16 px-2 py-1`}>
          <div className="text-xs underline">Insertions booked</div>
          <div className="mt-1 font-bold">{doc.insertions}</div>
        </div>

        <table className={`mt-4 w-full border-collapse ${box}`}>
          <thead>
            <tr>
              <th className={`${box} px-2 py-1 text-center font-normal`}>Description</th>
              <th className={`${box} w-24 px-1 py-1 text-center text-[11px] font-normal`}>Cost per insertion</th>
              <th className={`${box} w-20 px-1 py-1 text-center text-[11px] font-normal`}>Insertions booked</th>
              <th className={`${box} w-28 px-1 py-1 text-center text-[11px] font-normal`}>Total amount</th>
            </tr>
          </thead>
          <tbody className="align-top">
            {doc.package && (
              <tr>
                <td className="border-x border-foreground px-2 pt-3 font-semibold">{doc.package.label}</td>
                <td className="border-x border-foreground px-1 pt-3 text-right tabular-nums">{gbp(doc.package.price)}</td>
                <td className="border-x border-foreground px-1 pt-3 text-center">1</td>
                <td className="border-x border-foreground px-1 pt-3 text-right tabular-nums">{gbp(doc.package.price)}</td>
              </tr>
            )}
            {doc.rows.map((r, i) => (
              <tr key={i}>
                <td className="border-x border-foreground px-2 pt-3">
                  <div>{r.description}{r.when.length > 0 && (r.added_value || doc.package || r.insertions === 1) ? ` - ${r.when.join(", ")}` : ""}</div>
                  {r.insertions > 1 && !doc.package && !r.added_value && r.when.length > 0 && <div className="text-xs">{r.when.join(", ")}</div>}
                  {r.detail && <div className="whitespace-pre-line text-xs">{r.detail}</div>}
                  {r.note && <div className="text-xs italic">{r.note}</div>}
                </td>
                <td className="border-x border-foreground px-1 pt-3 text-right tabular-nums">{r.each != null ? gbp(r.each) : ""}</td>
                <td className="border-x border-foreground px-1 pt-3 text-center">{r.total != null ? r.insertions : ""}</td>
                <td className="border-x border-foreground px-1 pt-3 text-right tabular-nums">{r.total != null ? gbp(r.total) : ""}</td>
              </tr>
            ))}
            <tr><td className="border-x border-foreground py-3" /><td className="border-x border-foreground" /><td className="border-x border-foreground" /><td className="border-x border-foreground" /></tr>
            {doc.discount > 0 && (
              <tr className="border-t border-foreground">
                <td className="px-2 py-1">Less discount {Math.round(doc.discount_pct * 1000) / 10}%</td><td /><td />
                <td className="border-l border-foreground px-1 py-1 text-right tabular-nums">({gbp(doc.discount)})</td>
              </tr>
            )}
            {doc.agency > 0 && (
              <tr className="border-t border-foreground">
                <td className="px-2 py-1 font-bold">Less agency commission<span className="float-right font-bold">{Math.round(doc.agency_pct * 1000) / 10}%</span></td><td /><td />
                <td className="border-l border-foreground px-1 py-1 text-right tabular-nums" style={{ color: "var(--bad)" }}>({gbp(doc.agency)})</td>
              </tr>
            )}
            {showTotal && (
              <tr className="border-t border-foreground font-bold">
                <td className="px-2 py-1">Total</td><td /><td />
                <td className="border-l border-foreground px-1 py-1 text-right tabular-nums">{gbp(doc.payable)}</td>
              </tr>
            )}
          </tbody>
        </table>
        <p className="mt-1 text-right text-xs font-bold underline">VAT is not included</p>

        <div className={`${box} mt-6 min-h-20 px-2 py-1`}>
          <div className="text-xs underline">Special Instructions</div>
          {[doc.special_instructions, doc.copy_instructions, doc.invoice_email ? `Please email the invoice to ${doc.invoice_email}` : null].filter(Boolean).map((t, i) => (
            <p key={i} className="mt-1 whitespace-pre-line">{t}</p>
          ))}
          {doc.copy_dates.length > 0 && <p className="mt-1">Copy due: {doc.copy_dates.map((c) => (doc.copy_dates.length > 1 ? `${c.dates} (${c.item})` : c.dates)).join("; ")}</p>}
        </div>

        {doc.production_contact && <p className="mt-4 font-bold" style={{ color: "var(--bad)" }}>Production contact {doc.production_contact}</p>}
        {doc.artwork_specs && <p className="mt-4 text-justify text-[10.5px] leading-tight">{doc.artwork_specs}</p>}
        {doc.terms && <p className="mt-3 text-[11px]">{doc.terms}</p>}
        <footer className="mt-10 text-center text-[11px]">
          {doc.footer.split("\n").map((l, i) => <div key={i} className={i === 0 ? "font-semibold" : ""}>{l}</div>)}
        </footer>
      </article>
    </div>
  );
}
