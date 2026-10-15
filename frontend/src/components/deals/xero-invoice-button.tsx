"use client";

import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, CheckCircle2, ExternalLink, FileText, Loader2, Search } from "lucide-react";
import { toast } from "sonner";
import {
  createXeroInvoice, getXeroReference, searchXeroContacts,
  type XeroContact, type XeroCreateInput, type XeroDraft, type XeroInvoiceSummary, type XeroProblem, type XeroReference, type XeroTracking,
} from "@/lib/xero-invoicing";
import { friendlyError } from "@/lib/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { fmtDate } from "@/components/sales/sales-ui";

const selectCls = "h-8 w-full min-w-0 rounded-md border border-input bg-transparent px-2 text-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";
const money = (v: number | null | undefined, cur = "GBP") =>
  v == null ? "—" : new Intl.NumberFormat("en-GB", { style: "currency", currency: cur || "GBP" }).format(v);

type LineEdit = { account_code?: string | null; item_code?: string | null; unit_amount?: number | null; description?: string | null; tracking?: XeroTracking[] };

/** One click: make the draft invoice in Xero for what's due (or the items given). Then a final check, or what needs fixing. */
export function XeroInvoiceButton({ dealId, orderIds, label = "Create the invoice in Xero", size = "sm", variant = "default" }: {
  dealId: string; orderIds?: string[]; label?: string; size?: "sm" | "default"; variant?: "default" | "outline" | "ghost";
}) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [made, setMade] = useState<XeroInvoiceSummary | null>(null);
  const [fix, setFix] = useState<{ draft: XeroDraft; problems: XeroProblem[] } | null>(null);

  const run = (input: XeroCreateInput) => start(async () => {
    try {
      const r = await createXeroInvoice(dealId, { order_ids: orderIds, ...input });
      if (r.ok) { setFix(null); setMade(r.invoice); }   // the page refreshes when the check dialog is closed
      else setFix({ draft: r.draft, problems: r.problems });
    } catch (e) { toast.error(friendlyError(e, "Couldn't reach Xero just now. Try again in a minute.")); }
  });

  return (
    <>
      <Button size={size} variant={variant} className="gap-1.5" disabled={pending} onClick={() => run({})}>
        {pending && !fix ? <Loader2 className="size-3.5 animate-spin" /> : <FileText className="size-3.5" />} {label}
      </Button>
      {made && <MadeDialog invoice={made} onClose={() => { setMade(null); router.refresh(); }} />}
      {fix && <FixDialog key={JSON.stringify(fix.problems)} draft={fix.draft} problems={fix.problems} pending={pending} onClose={() => setFix(null)} onRetry={run} />}
    </>
  );
}

function MadeDialog({ invoice, onClose }: { invoice: XeroInvoiceSummary; onClose: () => void }) {
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><CheckCircle2 className="size-5 text-[var(--ok)]" aria-hidden="true" /> Draft invoice {invoice.number} is in Xero</DialogTitle>
          <DialogDescription>Check it below. It&apos;s a draft: nothing has gone to the client. Open it in Xero to make any change, then approve and send it from there.</DialogDescription>
        </DialogHeader>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 rounded-lg border border-border/70 bg-muted/20 p-3 text-sm sm:grid-cols-4">
          <div><dt className="text-xs text-muted-foreground">Invoice number</dt><dd className="font-bold">{invoice.number}</dd></div>
          <div><dt className="text-xs text-muted-foreground">To</dt><dd className="font-medium">{invoice.contact}</dd></div>
          <div><dt className="text-xs text-muted-foreground">Date</dt><dd>{fmtDate(invoice.date)}{invoice.due_date ? ` · due ${fmtDate(invoice.due_date)}` : ""}</dd></div>
          <div><dt className="text-xs text-muted-foreground">Reference</dt><dd>{invoice.reference || "—"}</dd></div>
        </dl>
        <div className="overflow-x-auto rounded-lg border border-border/70">
          <table className="w-full min-w-[40rem] text-xs">
            <thead><tr className="border-b border-border/70 text-left text-muted-foreground">
              <th className="px-3 py-2 font-semibold">Description</th><th className="px-2 py-2 text-right font-semibold">Qty</th>
              <th className="px-2 py-2 text-right font-semibold">Price</th><th className="px-2 py-2 text-right font-semibold">Disc.</th>
              <th className="px-2 py-2 font-semibold">Account</th><th className="px-2 py-2 font-semibold">Tax</th><th className="px-3 py-2 text-right font-semibold">Amount</th>
            </tr></thead>
            <tbody>
              {invoice.lines.map((l, i) => (
                <tr key={i} className="border-b border-border/60 last:border-0 align-top">
                  <td className="px-3 py-2">{l.description}{l.item_code ? <div className="text-muted-foreground">Item {l.item_code}</div> : null}{l.tracking.length ? <div className="text-muted-foreground">{l.tracking.join(" · ")}</div> : null}</td>
                  <td className="px-2 py-2 text-right tabular-nums">{l.quantity}</td>
                  <td className="px-2 py-2 text-right tabular-nums">{money(l.unit_amount, invoice.currency)}</td>
                  <td className="px-2 py-2 text-right tabular-nums">{l.discount_rate ? `${l.discount_rate}%` : "—"}</td>
                  <td className="px-2 py-2">{l.account_code || "—"}</td>
                  <td className="px-2 py-2">{l.tax_type || "—"}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{money(l.amount, invoice.currency)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot className="text-sm">
              <tr><td colSpan={6} className="px-3 pt-2 text-right text-muted-foreground">Subtotal</td><td className="px-3 pt-2 text-right tabular-nums">{money(invoice.sub_total, invoice.currency)}</td></tr>
              <tr><td colSpan={6} className="px-3 text-right text-muted-foreground">VAT</td><td className="px-3 text-right tabular-nums">{money(invoice.tax, invoice.currency)}</td></tr>
              <tr><td colSpan={6} className="px-3 pb-2 text-right font-bold">Total</td><td className="px-3 pb-2 text-right font-bold tabular-nums">{money(invoice.total, invoice.currency)}</td></tr>
            </tfoot>
          </table>
        </div>
        <p className="text-xs text-muted-foreground">Xero has dated it today. If you send it on another day, change the date in Xero so it&apos;s the day it goes out. The booking is now locked; changes go through you.</p>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>Done</Button>
          <a href={invoice.url} target="_blank" rel="noreferrer"><Button className="gap-1.5">Open it in Xero <ExternalLink className="size-3.5" /></Button></a>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function FixDialog({ draft, problems, pending, onClose, onRetry }: {
  draft: XeroDraft; problems: XeroProblem[]; pending: boolean; onClose: () => void; onRetry: (input: XeroCreateInput) => void;
}) {
  const has = (k: XeroProblem["key"]) => problems.some((p) => p.key === k);
  const blocking = has("connection") || has("nothing");
  const [contact, setContact] = useState<XeroContact | null>(draft.contact);
  const [q, setQ] = useState("");
  const [found, setFound] = useState<XeroContact[]>(draft.contact_candidates);
  const [searching, setSearching] = useState(false);
  const [ref, setRef] = useState<XeroReference | null>(null);
  const [refError, setRefError] = useState<string | null>(null);
  const [reference, setReference] = useState(draft.reference);
  const [lines, setLines] = useState<Record<string, LineEdit>>({});

  useEffect(() => {
    if (blocking) return;
    getXeroReference().then(setRef).catch((e) => setRefError(friendlyError(e, "Couldn't load Xero's account codes.")));
  }, [blocking]);

  async function search() {
    if (q.trim().length < 2) return;
    setSearching(true);
    try { setFound(await searchXeroContacts(q.trim())); } catch (e) { toast.error(friendlyError(e, "Couldn't search Xero")); }
    finally { setSearching(false); }
  }

  const setLine = (id: string, patch: LineEdit) => setLines((x) => ({ ...x, [id]: { ...x[id], ...patch } }));
  const value = (l: XeroDraft["lines"][number], k: keyof LineEdit) => (lines[l.order_id]?.[k] !== undefined ? lines[l.order_id]?.[k] : (l as unknown as Record<string, unknown>)[k]);
  const missingAmount = has("currency") && draft.lines.some((l) => !l.amount_given && !(lines[l.order_id]?.unit_amount));
  const missingAccount = draft.lines.some((l) => !(value(l, "account_code") || value(l, "item_code")));

  function retry() {
    const out: XeroCreateInput["lines"] = {};
    for (const [id, e] of Object.entries(lines)) {
      const clean = Object.fromEntries(Object.entries(e).filter(([, v]) => v !== undefined && v !== ""));
      if (Object.keys(clean).length) out[id] = clean;
    }
    onRetry({ contact_id: contact?.id ?? null, contact_name: contact?.name ?? null, reference, lines: out });
  }

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><AlertTriangle className="size-5 text-[var(--warn)]" aria-hidden="true" /> {blocking ? "The invoice can't be made yet" : "A few things to sort before the invoice is made"}</DialogTitle>
          <DialogDescription>Booking {draft.deal_number}, {draft.client_name}. Nothing has been made in Xero yet.</DialogDescription>
        </DialogHeader>
        <ul className="flex flex-col gap-1.5 rounded-lg border px-3 py-2.5 text-sm" style={{ borderColor: "color-mix(in oklab, var(--warn) 40%, transparent)", background: "color-mix(in oklab, var(--warn) 8%, transparent)" }}>
          {problems.map((p, i) => <li key={i} className="flex gap-2"><AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-[var(--warn)]" aria-hidden="true" />{p.message}</li>)}
        </ul>

        {!blocking && (
          <>
            <section className="flex flex-col gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Who it goes to in Xero</h3>
              {(draft.invoice_to || draft.invoice_email) && <p className="text-xs text-muted-foreground">The booking says invoice to: {[draft.invoice_to?.split("\n")[0], draft.invoice_email].filter(Boolean).join(" · ")}{draft.agency ? ` (agency ${draft.agency.name}, ${draft.agency.pct}% commission)` : ""}</p>}
              {found.length > 0 && (
                <div className="flex flex-col gap-1">
                  {found.map((c) => (
                    <label key={c.id} className={`flex cursor-pointer items-center gap-2 rounded-md border px-2.5 py-1.5 text-sm ${contact?.id === c.id ? "border-primary bg-primary/5" : "border-border/70"}`}>
                      <input type="radio" name="xero-contact" checked={contact?.id === c.id} onChange={() => setContact(c)} />
                      <span className="font-medium">{c.name}</span>{c.email && <span className="text-xs text-muted-foreground">{c.email}</span>}
                    </label>
                  ))}
                </div>
              )}
              <div className="flex gap-2">
                <Input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), search())} placeholder="Search Xero contacts by name or email" className="h-8 text-sm" aria-label="Search Xero contacts" />
                <Button size="sm" variant="outline" className="gap-1.5" disabled={searching || q.trim().length < 2} onClick={search}>{searching ? <Loader2 className="size-3.5 animate-spin" /> : <Search className="size-3.5" />} Search</Button>
              </div>
              {contact && <p className="text-xs">Using <span className="font-semibold">{contact.name}</span>. It&apos;s remembered for this booking and client.</p>}
              {!contact && <p className="text-xs text-muted-foreground">Not in Xero at all? Add the contact in Xero first, then search for it here.</p>}
            </section>

            <section className="flex flex-col gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Lines</h3>
              {refError && <p className="text-xs text-[var(--warn)]">{refError}</p>}
              {draft.lines.map((l) => (
                <div key={l.order_id} className="grid gap-2 rounded-lg border border-border/70 p-2.5 sm:grid-cols-6">
                  <label className="flex flex-col gap-1 text-[11px] font-semibold text-muted-foreground sm:col-span-6">Description
                    <Input value={String(value(l, "description") ?? "")} onChange={(e) => setLine(l.order_id, { description: e.target.value })} className="h-8 text-sm" /></label>
                  <label className="flex flex-col gap-1 text-[11px] font-semibold text-muted-foreground sm:col-span-2">Amount ({draft.currency}){l.discount_rate ? ` less ${l.discount_rate}%` : ""}
                    <Input type="number" min={0} step="0.01" value={String(value(l, "unit_amount") ?? "")} onChange={(e) => setLine(l.order_id, { unit_amount: e.target.value === "" ? null : Number(e.target.value) })} className="h-8 text-sm" />
                    {draft.currency !== "GBP" && <span className="font-normal">Booked at {money(l.value_gbp)}</span>}</label>
                  <label className="flex flex-col gap-1 text-[11px] font-semibold text-muted-foreground sm:col-span-2">Account
                    <select className={selectCls} value={String(value(l, "account_code") ?? "")} onChange={(e) => setLine(l.order_id, { account_code: e.target.value || null })}>
                      <option value="">{ref ? "Choose…" : "Loading…"}</option>
                      {ref?.accounts.map((a) => <option key={a.code} value={a.code}>{a.code} · {a.name}</option>)}
                    </select></label>
                  <label className="flex flex-col gap-1 text-[11px] font-semibold text-muted-foreground sm:col-span-2">Item (optional)
                    <select className={selectCls} value={String(value(l, "item_code") ?? "")} onChange={(e) => setLine(l.order_id, { item_code: e.target.value || null })}>
                      <option value="">None</option>
                      {ref?.items.map((it) => <option key={it.code} value={it.code}>{it.code} · {it.name}</option>)}
                    </select></label>
                  {ref && ref.tracking.map((t) => {
                    const cur = ((value(l, "tracking") as XeroTracking[] | undefined) ?? []).find((x) => x.name === t.name)?.option ?? "";
                    return (
                      <label key={t.name} className="flex flex-col gap-1 text-[11px] font-semibold text-muted-foreground sm:col-span-3">{t.name}
                        <select className={selectCls} value={cur} onChange={(e) => {
                          const others = ((value(l, "tracking") as XeroTracking[] | undefined) ?? []).filter((x) => x.name !== t.name);
                          setLine(l.order_id, { tracking: e.target.value ? [...others, { name: t.name, option: e.target.value }] : others });
                        }}>
                          <option value="">None</option>
                          {t.options.map((o) => <option key={o} value={o}>{o}</option>)}
                        </select></label>
                    );
                  })}
                  <p className="text-[11px] text-muted-foreground sm:col-span-6">{l.title}: codes you choose here are remembered for {l.title}.</p>
                </div>
              ))}
              <label className="flex flex-col gap-1 text-[11px] font-semibold text-muted-foreground">Reference
                <Input value={reference} onChange={(e) => setReference(e.target.value)} className="h-8 text-sm" /></label>
              {draft.instructions && <p className="rounded-md bg-muted/40 p-2 text-xs"><span className="font-semibold">Invoice instructions on the booking:</span> {draft.instructions}</p>}
            </section>
          </>
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>{blocking ? "Close" : "Cancel"}</Button>
          {!blocking && (
            <Button disabled={pending || !contact || missingAmount || missingAccount} onClick={retry} className="gap-1.5">
              {pending && <Loader2 className="size-3.5 animate-spin" />} Make the draft invoice
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
