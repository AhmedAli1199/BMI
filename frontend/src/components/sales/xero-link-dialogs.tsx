"use client";

import { useEffect, useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { ExternalLink, Link2, Loader2, Search } from "lucide-react";
import type { BookingChoice, SalesOrder, UnmatchedInvoice, XeroChoice } from "@/lib/sales-types";
import { getInvoiceBookingChoices, getXeroChoices, linkInvoiceToBookings, linkXeroInvoice } from "@/lib/sales-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { fmtDate, fmtGBP } from "@/components/sales/sales-ui";

const STATE_LABEL: Record<string, string> = { paid: "Paid", part_paid: "Part paid", unpaid: "Awaiting payment", overdue: "Overdue", voided: "Voided" };

function money(currency: string, n: number) {
  return currency === "GBP" ? fmtGBP(n) : `${currency} ${n.toLocaleString("en-GB", { maximumFractionDigits: 2 })}`;
}

/** Loads `load(q)` 250ms after the search box stops changing (and once on open). */
function useSearch<T>(open: boolean, load: (q: string) => Promise<T[]>) {
  const [q, setQ] = useState("");
  const [state, setState] = useState<{ key: string; rows: T[] } | null>(null);
  const key = `${open}:${q}`;
  useEffect(() => {
    if (!open) return;
    let live = true;
    const t = setTimeout(() => {
      load(q).then((rows) => live && setState({ key, rows })).catch(() => live && setState({ key, rows: [] }));
    }, q ? 250 : 0);
    return () => { live = false; clearTimeout(t); };
  }, [open, q, key, load]);
  return { q, setQ, rows: state?.rows ?? [], loading: state?.key !== key };
}

/** "Find in Xero" on a booking: pick the invoice instead of typing its number. */
export function FindInXeroButton({ order, onLinked }: { order: SalesOrder; onLinked: () => void }) {
  const [open, setOpen] = useState(false);
  const [pending, start] = useTransition();
  const { q, setQ, rows, loading } = useSearch<XeroChoice>(open, (s) => getXeroChoices(order.id, s));

  function link(inv: XeroChoice) {
    start(async () => {
      try {
        const o = await linkXeroInvoice(order.id, inv.id);
        toast.success(`Linked to Xero invoice ${o.invoice_number} · ${fmtGBP(o.invoice_value_gbp ?? 0)} before VAT · ${STATE_LABEL[inv.state] ?? inv.state}`);
        setOpen(false);
        onLinked();
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Couldn't link the invoice");
      }
    });
  }

  return (
    <>
      <Button type="button" size="sm" variant="outline" className="gap-1.5" onClick={() => setOpen(true)}>
        <Search className="size-3.5" aria-hidden="true" /> Find in Xero
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Find the invoice in Xero</DialogTitle>
            <DialogDescription>
              Invoices no booking has yet, most likely first for {order.client_name} ({fmtGBP(order.value_gbp)}). Linking fills in the number, the invoiced amount and the date from Xero.
            </DialogDescription>
          </DialogHeader>
          <Input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by invoice number, customer or reference" className="h-8 text-sm" aria-label="Search Xero invoices" />
          <div className="max-h-[55vh] overflow-y-auto rounded-lg border border-border/70">
            {loading ? (
              <p className="flex items-center gap-2 p-4 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" /> Looking in Xero…</p>
            ) : rows.length === 0 ? (
              <p className="p-4 text-sm text-muted-foreground">{q ? "No invoice matches that search." : "No likely invoices. Search by number or customer to see the rest."}</p>
            ) : (
              <ul className="divide-y divide-border/60">
                {rows.map((inv) => (
                  <li key={inv.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2.5 text-sm">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-x-2">
                        <a href={inv.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold text-primary hover:underline">
                          {inv.number ?? "No number"} <ExternalLink className="size-3" aria-hidden="true" />
                        </a>
                        <span className="font-medium">{inv.contact}</span>
                        {inv.fit.map((f) => (
                          <span key={f} className="rounded-full px-1.5 py-0.5 text-[10px] font-semibold" style={{ background: "color-mix(in oklab, var(--ok) 14%, transparent)", color: "var(--ok)" }}>{f}</span>
                        ))}
                      </div>
                      <p className="truncate text-xs text-muted-foreground">
                        {money(inv.currency, inv.net)} before VAT · {fmtDate(inv.issued_on)} · {STATE_LABEL[inv.state] ?? inv.state}
                        {inv.reference || inv.lines ? ` · ${[...new Set([inv.reference, inv.lines].filter(Boolean))].join(" · ")}` : ""}
                      </p>
                    </div>
                    <Button type="button" size="sm" disabled={pending} onClick={() => link(inv)} className="gap-1.5"><Link2 className="size-3.5" /> Link</Button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

/** "Link to a booking" on an invoice that's in Xero but not in the register. */
export function LinkInvoiceButton({ invoice }: { invoice: UnmatchedInvoice }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [pending, start] = useTransition();
  const { q, setQ, rows, loading } = useSearch<BookingChoice>(open, (s) => getInvoiceBookingChoices(invoice.id, s));

  function link(c: BookingChoice) {
    start(async () => {
      try {
        await linkInvoiceToBookings(invoice.id, c.bookings.map((b) => b.id));
        toast.success(`Invoice ${invoice.number} linked to ${c.bookings[0].client}${c.bookings.length > 1 ? ` (${c.bookings.length} bookings)` : ""}`);
        setOpen(false);
        router.refresh();
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Couldn't link the invoice");
      }
    });
  }

  return (
    <>
      <Button type="button" size="xs" variant="outline" className="gap-1" onClick={() => setOpen(true)}>
        <Link2 className="size-3" aria-hidden="true" /> Link to a booking
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Which booking is invoice {invoice.number} for?</DialogTitle>
            <DialogDescription>
              {invoice.contact} · {money(invoice.currency, invoice.net)} before VAT · {fmtDate(invoice.issued_on)}. Bookings still waiting for an invoice; suggestions first, or search by client.
            </DialogDescription>
          </DialogHeader>
          <Input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search bookings by client name" className="h-8 text-sm" aria-label="Search bookings" />
          <div className="max-h-[55vh] overflow-y-auto rounded-lg border border-border/70">
            {loading ? (
              <p className="flex items-center gap-2 p-4 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" /> Looking for bookings…</p>
            ) : rows.length === 0 ? (
              <p className="p-4 text-sm text-muted-foreground">{q ? "No booking waiting for an invoice matches that name." : "No booking matches the amount. Search by the client's name."}</p>
            ) : (
              <ul className="divide-y divide-border/60">
                {rows.map((c) => (
                  <li key={c.key} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2.5 text-sm">
                    <div className="min-w-0 flex-1">
                      {c.bookings.map((b) => (
                        <div key={b.id} className="flex flex-wrap items-baseline gap-x-2">
                          <span className="font-semibold">{b.client}</span>
                          <Link href={`/sales/editions/${b.edition_id}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline">
                            {b.edition} <ExternalLink className="size-3" aria-hidden="true" />
                          </Link>
                          <span className="text-xs text-muted-foreground">
                            {[b.size, fmtGBP(b.value_gbp), b.booked_on ? `booked ${fmtDate(b.booked_on)}` : null, b.rep].filter(Boolean).join(" · ")}
                          </span>
                        </div>
                      ))}
                      {c.bookings.length > 1 && <p className="text-xs text-muted-foreground">Together {fmtGBP(c.total_gbp)}</p>}
                      {c.suggested && c.reasons.length > 0 && <p className="text-xs" style={{ color: "var(--ok)" }}>{c.reasons.join(" · ")}</p>}
                    </div>
                    <Button type="button" size="sm" disabled={pending} onClick={() => link(c)} className="gap-1.5"><Link2 className="size-3.5" /> Link</Button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
