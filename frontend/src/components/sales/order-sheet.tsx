"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { AlertTriangle, History, Plus, Split, Trash2, X } from "lucide-react";
import type { EditionSummary, OrderInput, OrderStatus, SalesOrder, SalesRep, ClientSuggestion } from "@/lib/sales-types";
import type { FieldChange } from "@/lib/types";
import {
  createOrder,
  deleteOrder,
  getOrderChanges,
  listEditionsForTitle,
  searchCompaniesForOrder,
  suggestClients,
  updateOrder,
} from "@/lib/sales-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { EntityPicker } from "@/components/entity-picker";
import { InfoHint } from "@/components/sales/info-hint";
import { UndoInvoiceLinkButton } from "@/components/sales/invoice-match-panel";
import { FindInXeroButton } from "@/components/sales/xero-link-dialogs";
import { BookingNewBusinessRow } from "@/components/commission/booking-new-business";
import { fmtGBP } from "@/components/sales/sales-ui";
import { friendlyError } from "@/lib/errors";

const SIZES = ["FP", "1/2", "1/4", "DPS", "Banner", "Listing", "Advertorial", "Insert", "Partner", "Sponsor", "One ticket", "Table"];
const STATUSES: { value: OrderStatus; label: string; hint: string }[] = [
  { value: "booked", label: "Booked", hint: "A live booking - counts towards the edition's total." },
  { value: "cancelled", label: "Cancelled", hint: "The sheet's CANX. Kept on record, not counted." },
  { value: "contra", label: "Contra", hint: "A free swap with a partner - no money changes hands, not counted." },
  { value: "moved", label: "Moved", hint: "Carried to another edition. Re-enter it there so it counts once." },
];

const selectCls = "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";

const FIELD_LABELS: Record<string, string> = {
  client_name: "client", company_id: "CRM company", rep_id: "salesperson", booked_on: "booking date",
  value_gbp: "value", rate_usd: "US$ rate", agency_commission_gbp: "agency commission", commission_rate: "commission rate",
  invoice_number: "invoice number", invoice_value_gbp: "invoiced amount", invoiced_on: "invoice date", xero_link: "Xero invoice link",
  invoice_note: "reason for difference", moved_to_edition_id: "moved-to edition",
};

function showValue(field: string, v: string, reps: SalesRep[]): string {
  if (field === "rep_id") return reps.find((r) => r.id === v)?.name ?? "another salesperson";
  if (field === "company_id") return "a CRM company";
  if (field === "moved_to_edition_id") return "another edition";
  if (field.endsWith("_gbp")) return fmtGBP(Number(v));
  return v;
}

type CreditRow = { rep_id: string; amount: string };

export type OrderSheetTarget =
  | { mode: "create"; editionId: string; titleId: string; year: number; editionLabel: string; defaults?: Partial<SalesOrder> }
  | { mode: "edit"; order: SalesOrder; year: number };

function num(v: string): number | null {
  const s = v.replace(/[£$,\s]/g, "");
  if (!s) return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : NaN;
}

function Field({ label, htmlFor, hint, children, className = "" }: { label: string; htmlFor?: string; hint?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <div className="flex items-center gap-1">
        <Label htmlFor={htmlFor} className="text-xs font-semibold text-muted-foreground">
          {label}
        </Label>
        {hint && <InfoHint>{hint}</InfoHint>}
      </div>
      {children}
    </div>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset className="flex flex-col gap-3 border-t border-border/70 pt-4 first:border-0 first:pt-0">
      <legend className="mb-1 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">{title}</legend>
      {children}
    </fieldset>
  );
}

export function OrderSheet({
  target,
  reps,
  canDelete,
  onClose,
}: {
  target: OrderSheetTarget | null;
  reps: SalesRep[];
  canDelete: boolean;
  onClose: () => void;
}) {
  return (
    <Sheet open={target !== null} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right" className="w-full gap-0 p-0 sm:max-w-xl">
        {target && <OrderForm key={target.mode === "edit" ? target.order.id : target.editionId} target={target} reps={reps} canDelete={canDelete} onClose={onClose} />}
      </SheetContent>
    </Sheet>
  );
}

function OrderForm({ target, reps, canDelete, onClose }: { target: OrderSheetTarget; reps: SalesRep[]; canDelete: boolean; onClose: () => void }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const existing = target.mode === "edit" ? target.order : null;
  const d = existing ?? (target.mode === "create" ? target.defaults : undefined) ?? {};
  const titleId = existing ? existing.title_id : (target as { titleId: string }).titleId;

  const [client, setClient] = useState(d.client_name ?? "");
  const [company, setCompany] = useState<{ id: string; label: string } | null>(d.company ?? null);
  const [suggestions, setSuggestions] = useState<ClientSuggestion[]>([]);
  const [showSuggest, setShowSuggest] = useState(false);
  const [repId, setRepId] = useState(d.rep?.id ?? "");
  const [bookedOn, setBookedOn] = useState(d.booked_on ?? (existing ? "" : new Date().toISOString().slice(0, 10)));
  const [size, setSize] = useState(d.size ?? "");
  const [series, setSeries] = useState(d.series ?? "");
  const [position, setPosition] = useState(d.position ?? "");
  const [value, setValue] = useState(d.value_gbp != null ? String(d.value_gbp) : "");
  const [rateUsd, setRateUsd] = useState(d.rate_usd != null ? String(d.rate_usd) : "");
  const [agency, setAgency] = useState(d.agency_commission_gbp != null ? String(d.agency_commission_gbp) : "");
  const [invNo, setInvNo] = useState(d.invoice_number ?? "");
  const [invValue, setInvValue] = useState(d.invoice_value_gbp != null ? String(d.invoice_value_gbp) : "");
  const [invOn, setInvOn] = useState(d.invoiced_on ?? "");
  const [invNote, setInvNote] = useState(d.invoice_note ?? "");
  const [status, setStatus] = useState<OrderStatus>(d.status ?? "booked");
  const [movedTo, setMovedTo] = useState(d.moved_to?.id ?? "");
  const [notes, setNotes] = useState(d.notes ?? "");
  const initialSplit = (existing?.credits.length ?? 0) > 1;
  const [split, setSplit] = useState(initialSplit);
  const [credits, setCredits] = useState<CreditRow[]>(
    initialSplit ? existing!.credits.map((c) => ({ rep_id: c.rep_id, amount: String(c.amount_gbp) })) : []
  );
  const [moveOptions, setMoveOptions] = useState<EditionSummary[]>([]);
  const [changes, setChanges] = useState<FieldChange[] | null>(null);

  // Linked to Xero (and the number not being changed): the amount and date are Xero's, not typed.
  const linked = !!existing?.xero && invNo.trim() === (existing.invoice_number ?? "");
  const activeReps = useMemo(() => reps.filter((r) => r.active || r.id === repId), [reps, repId]);
  const valueNum = num(value);
  const creditTotal = credits.reduce((s, c) => s + (num(c.amount) || 0), 0);

  useEffect(() => {
    if (!showSuggest || client.trim().length < 2) return;
    const t = setTimeout(() => suggestClients(client).then(setSuggestions).catch(() => setSuggestions([])), 200);
    return () => clearTimeout(t);
  }, [client, showSuggest]);

  useEffect(() => {
    if (status !== "moved" || moveOptions.length) return;
    Promise.all([listEditionsForTitle(titleId, target.year), listEditionsForTitle(titleId, target.year + 1)])
      .then(([a, b]) => setMoveOptions([...a, ...b].filter((e) => e.id !== (existing?.edition_id ?? ""))))
      .catch(() => undefined);
  }, [status, moveOptions.length, titleId, target.year, existing?.edition_id]);

  function startSplit() {
    const total = valueNum && !Number.isNaN(valueNum) ? valueNum : 0;
    const first = repId || activeReps[0]?.id || "";
    setCredits([
      { rep_id: first, amount: String(Math.round((total / 2) * 100) / 100) },
      { rep_id: activeReps.find((r) => r.id !== first)?.id ?? "", amount: String(Math.round((total / 2) * 100) / 100) },
    ]);
    setSplit(true);
  }

  function submit() {
    if (!client.trim()) return toast.error("Enter the client's name.");
    const numbers = { value: valueNum, rateUsd: num(rateUsd), agency: num(agency), invValue: num(invValue) };
    if (Object.values(numbers).some((n) => Number.isNaN(n))) return toast.error("Amounts must be numbers, e.g. 1250 or 1250.50.");
    if (split && credits.some((c) => !c.rep_id)) return toast.error("Choose a salesperson for every share of the split.");

    const input: OrderInput = {
      client_name: client.trim(),
      rep_id: repId || null,
      booked_on: bookedOn || null,
      size: size.trim() || null,
      series: series.trim() || null,
      position: position.trim() || null,
      value_gbp: numbers.value ?? 0,
      rate_usd: numbers.rateUsd,
      agency_commission_gbp: numbers.agency,
      invoice_number: invNo.trim() || null,
      invoice_value_gbp: numbers.invValue,
      invoiced_on: invOn || null,
      invoice_note: invNote.trim() || null,
      status,
      moved_to_edition_id: status === "moved" ? movedTo || null : null,
      notes: notes.trim() || null,
    };
    if (company) input.company_id = company.id;
    else if (existing?.company) input.clear_company = true;
    if (split) input.credits = credits.map((c) => ({ rep_id: c.rep_id, amount_gbp: num(c.amount) || 0 }));
    else if (initialSplit) input.credits = repId && numbers.value ? [{ rep_id: repId, amount_gbp: numbers.value }] : [];

    startTransition(async () => {
      try {
        const saved = existing ? await updateOrder(existing.id, input) : await createOrder((target as { editionId: string }).editionId, input);
        const what = existing ? "Booking saved" : `Booking added for ${client.trim()}`;
        if (saved.invoice_number && saved.invoice_number !== (existing?.invoice_number ?? null)) {
          if (saved.xero) {
            const state = { paid: "paid", part_paid: "part paid", unpaid: "awaiting payment", overdue: "overdue", voided: "voided" }[saved.xero.state] ?? saved.xero.state;
            toast.success(`${what} · linked to Xero invoice ${saved.xero.invoice_number ?? saved.invoice_number} · ${fmtGBP(saved.invoice_value_gbp ?? 0)} before VAT · ${state}`);
          } else {
            toast.warning(`${what}. ${saved.invoice_number} isn't in Xero yet - it will link by itself when it shows up in Xero.`);
          }
        } else {
          toast.success(what);
        }
        onClose();
        router.refresh();
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't save the booking"));
      }
    });
  }

  function markChecked() {
    if (!existing) return;
    startTransition(async () => {
      try {
        await updateOrder(existing.id, { clear_warning: true });
        toast.success("Marked as checked");
        onClose();
        router.refresh();
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't update"));
      }
    });
  }

  function remove() {
    if (!existing || !confirm(`Delete the booking for ${existing.client_name}? This can't be undone - use "Cancelled" to keep it on record instead.`)) return;
    startTransition(async () => {
      try {
        await deleteOrder(existing.id, existing.edition_id);
        toast.success("Booking deleted");
        onClose();
        router.refresh();
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't delete"));
      }
    });
  }

  const title = existing ? existing.client_name : "Add a booking";
  const subtitle = existing ? existing.edition_label : (target as { editionLabel: string }).editionLabel;

  return (
    <>
      <SheetHeader className="border-b border-border/70 px-5 py-4">
        <SheetTitle className="pr-8 text-base font-bold">{title}</SheetTitle>
        <SheetDescription className="text-xs">{subtitle}</SheetDescription>
      </SheetHeader>

      <div className="flex flex-1 flex-col gap-5 overflow-y-auto px-5 py-4">
        {existing?.import_warning && (
          <div className="flex items-start gap-2.5 rounded-lg border px-3 py-2.5 text-xs" style={{ borderColor: "color-mix(in oklab, var(--warn) 40%, transparent)", background: "color-mix(in oklab, var(--warn) 8%, transparent)" }}>
            <AlertTriangle className="mt-0.5 size-4 shrink-0" style={{ color: "var(--warn)" }} aria-hidden="true" />
            <div className="flex-1">
              <div className="font-semibold text-foreground">Check this row from the spreadsheet</div>
              <div className="mt-0.5 text-muted-foreground">{existing.import_warning}</div>
            </div>
            <Button size="xs" variant="outline" onClick={markChecked} disabled={pending}>
              Mark checked
            </Button>
          </div>
        )}

        <Group title="Client">
          <Field label="Client (as it should appear on the order)" htmlFor="os-client" hint="Start typing to reuse a name already in the register - it keeps one advertiser from appearing under three spellings.">
            <div className="relative">
              <Input
                id="os-client"
                value={client}
                autoComplete="off"
                onChange={(e) => {
                  setClient(e.target.value);
                  setShowSuggest(true);
                }}
                onBlur={() => setTimeout(() => setShowSuggest(false), 150)}
                placeholder="e.g. Air Canada"
              />
              {showSuggest && suggestions.length > 0 && client.trim().length >= 2 && (
                <ul role="listbox" className="absolute inset-x-0 top-full z-20 mt-1 max-h-60 overflow-y-auto rounded-lg border border-border bg-popover p-1 shadow-md">
                  {suggestions.map((s) => (
                    <li key={s.client_name + (s.company?.id ?? "")}>
                      <button
                        type="button"
                        className="flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent"
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => {
                          setClient(s.client_name);
                          if (s.company) setCompany(s.company);
                          setShowSuggest(false);
                        }}
                      >
                        <span className="truncate">{s.client_name}</span>
                        <span className="shrink-0 text-[11px] text-muted-foreground">
                          {s.orders} booking{s.orders === 1 ? "" : "s"}
                          {s.company ? " · linked" : ""}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </Field>
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-1">
              <span className="text-xs font-semibold text-muted-foreground">CRM company</span>
              <InfoHint>Linking the booking to its CRM company shows it on the company&apos;s Bookings tab and lets renewals reach the right record. Optional.</InfoHint>
            </div>
            <EntityPicker label="company" placeholder="Search CRM companies…" search={searchCompaniesForOrder} value={company} onChange={setCompany} viewHref={(id) => `/companies/${id}`} />
          </div>
        </Group>

        <Group title="What was sold">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Field label="Size / product" htmlFor="os-size" hint="As on the sheet: FP (full page), 1/2, DPS (double-page spread), Banner… Page-equivalents for print are worked out from this.">
              <Input id="os-size" list="os-sizes" value={size} onChange={(e) => setSize(e.target.value)} placeholder="FP" />
              <datalist id="os-sizes">
                {SIZES.map((s) => (
                  <option key={s} value={s} />
                ))}
              </datalist>
            </Field>
            <Field label="Series" htmlFor="os-series" hint="For a multi-issue deal, which one this is - e.g. 2 of 3.">
              <Input id="os-series" value={series} onChange={(e) => setSeries(e.target.value)} placeholder="1 of 3" />
            </Field>
            <Field label="Page / position" htmlFor="os-pos">
              <Input id="os-pos" value={position} onChange={(e) => setPosition(e.target.value)} placeholder="43" />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Field label="Value (£)" htmlFor="os-value" hint="The £ value of the booking - what counts towards the edition's total and commission.">
              <Input id="os-value" inputMode="decimal" value={value} onChange={(e) => setValue(e.target.value)} placeholder="1250" />
            </Field>
            <Field label="Rate (US$)" htmlFor="os-usd" hint="Only for bookings quoted in dollars - the £ value is still what's counted.">
              <Input id="os-usd" inputMode="decimal" value={rateUsd} onChange={(e) => setRateUsd(e.target.value)} placeholder="Optional" />
            </Field>
            <Field label="Booked on" htmlFor="os-date">
              <Input id="os-date" type="date" value={bookedOn} onChange={(e) => setBookedOn(e.target.value)} />
            </Field>
          </div>
        </Group>

        <Group title="Salesperson">
          {!split ? (
            <div className="flex items-end gap-2">
              <Field label="Credited to" htmlFor="os-rep" className="flex-1">
                <select id="os-rep" className={selectCls} value={repId} onChange={(e) => setRepId(e.target.value)}>
                  <option value="">Not assigned</option>
                  {activeReps.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} ({r.code}){r.active ? "" : " - former"}
                    </option>
                  ))}
                </select>
              </Field>
              <Button type="button" size="sm" variant="outline" onClick={startSplit} className="gap-1.5">
                <Split className="size-3.5" aria-hidden="true" />
                Split
              </Button>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-1 text-xs font-semibold text-muted-foreground">
                Shared between salespeople
                <InfoHint>Each person&apos;s share is what their commission is worked out on - like the sheet&apos;s per-rep columns.</InfoHint>
              </div>
              {credits.map((c, i) => (
                <div key={i} className="flex items-center gap-2">
                  <select
                    aria-label={`Salesperson ${i + 1}`}
                    className={`${selectCls} flex-1`}
                    value={c.rep_id}
                    onChange={(e) => setCredits(credits.map((x, j) => (j === i ? { ...x, rep_id: e.target.value } : x)))}
                  >
                    <option value="">Choose…</option>
                    {activeReps.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name} ({r.code})
                      </option>
                    ))}
                  </select>
                  <Input
                    aria-label={`Share for salesperson ${i + 1} (£)`}
                    inputMode="decimal"
                    className="w-28"
                    value={c.amount}
                    onChange={(e) => setCredits(credits.map((x, j) => (j === i ? { ...x, amount: e.target.value } : x)))}
                  />
                  <Button type="button" size="icon-sm" variant="ghost" aria-label="Remove this share" onClick={() => setCredits(credits.filter((_, j) => j !== i))} disabled={credits.length <= 1}>
                    <X className="size-3.5" />
                  </Button>
                </div>
              ))}
              <div className="flex items-center justify-between text-xs">
                <Button type="button" size="xs" variant="ghost" className="gap-1" onClick={() => setCredits([...credits, { rep_id: "", amount: "" }])}>
                  <Plus className="size-3" aria-hidden="true" /> Add person
                </Button>
                <span className="tabular-nums" style={{ color: valueNum && Math.abs(creditTotal - valueNum) > 0.5 ? "var(--warn)" : "var(--muted-foreground)" }}>
                  Shares total {fmtGBP(creditTotal)}
                  {valueNum ? ` of ${fmtGBP(valueNum)}` : ""}
                </span>
              </div>
              <button type="button" className="self-start text-xs font-semibold text-primary hover:underline" onClick={() => { setSplit(false); setCredits([]); }}>
                Go back to one salesperson
              </button>
            </div>
          )}
        </Group>

        {existing && existing.status === "booked" && (
          <Group title="Commission">
            <BookingNewBusinessRow orderId={existing.id} />
          </Group>
        )}

        <Group title="Invoice">
          {existing?.xero && (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border/70 bg-muted/20 px-3 py-2 text-xs">
              <span className="text-muted-foreground">
                <span className="font-semibold text-foreground">Linked to Xero invoice {existing.xero.invoice_number ?? existing.invoice_number}</span>
                {existing.xero.link === "auto" && " · matched automatically"}
                {existing.xero.link === "confirmed" && " · matched, confirmed by a person"}
                {existing.xero.link === "typed" && " · from the number typed here"}
              </span>
              <span className="flex items-center gap-2">
                {existing.xero.url && (
                  <a href={existing.xero.url} target="_blank" rel="noreferrer" className="font-semibold text-primary hover:underline">
                    Open in Xero
                  </a>
                )}
                {(existing.xero.link === "auto" || existing.xero.link === "confirmed") && <UndoInvoiceLinkButton orderIds={[existing.id]} />}
              </span>
            </div>
          )}
          {existing && !existing.xero && (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-dashed border-border/80 px-3 py-2 text-xs text-muted-foreground">
              <span>{existing.invoice_number ? `${existing.invoice_number} isn't in Xero yet - check the number, or pick the invoice.` : "Not linked to a Xero invoice yet. Type the number below, or pick it from Xero."}</span>
              <FindInXeroButton order={existing} onLinked={() => { onClose(); router.refresh(); }} />
            </div>
          )}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Field label="Invoice number" htmlFor="os-inv">
              <Input id="os-inv" value={invNo} onChange={(e) => setInvNo(e.target.value)} placeholder="INV-3050" />
            </Field>
            <Field label="Invoiced (£)" htmlFor="os-invv" hint={linked ? "Taken from the Xero invoice (before VAT) and kept in step with it." : "Filled in from Xero once the invoice number is linked. Until then, blank means the booking value."}>
              <Input id="os-invv" inputMode="decimal" value={invValue} disabled={linked} onChange={(e) => setInvValue(e.target.value)} placeholder={value || "Same as value"} />
            </Field>
            <Field label="Invoiced on" htmlFor="os-invon" hint={linked ? "The invoice date in Xero." : undefined}>
              <Input id="os-invon" type="date" value={invOn} disabled={linked} onChange={(e) => setInvOn(e.target.value)} />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Field label="Agency cut (£)" htmlFor="os-agency" hint="What an agency kept (e.g. 10%), so the invoice is lower than the booking. Stops it showing as a mismatch.">
              <Input id="os-agency" inputMode="decimal" value={agency} onChange={(e) => setAgency(e.target.value)} placeholder="Optional" />
            </Field>
            <Field label="Reason for difference" htmlFor="os-invnote" className="col-span-1 sm:col-span-2" hint="Why the invoice differs from the booking, or when the rest will be invoiced - the sheet's own column. A difference with a reason shows as part-invoiced, not as a problem.">
              <Input id="os-invnote" value={invNote} onChange={(e) => setInvNote(e.target.value)} placeholder="e.g. to be on next quarter invoice" />
            </Field>
          </div>
        </Group>

        <Group title="Status">
          <div role="radiogroup" aria-label="Booking status" className="grid grid-cols-2 gap-1.5 sm:grid-cols-4">
            {STATUSES.map((s) => (
              <button
                key={s.value}
                type="button"
                role="radio"
                aria-checked={status === s.value}
                title={s.hint}
                onClick={() => setStatus(s.value)}
                className={`rounded-lg border px-2 py-1.5 text-xs font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-ring ${
                  status === s.value ? "border-primary bg-primary/10 text-foreground" : "border-border text-muted-foreground hover:bg-accent/50"
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">{STATUSES.find((s) => s.value === status)?.hint}</p>
          {existing?.status_reason && status === existing.status && status !== "booked" && (
            <p className="rounded-md bg-muted/60 px-2.5 py-1.5 text-xs text-muted-foreground">
              Marked {existing.status} on import because the sheet said: <span className="font-semibold text-foreground">&ldquo;{existing.status_reason}&rdquo;</span>
            </p>
          )}
          {status === "moved" && (
            <Field label="Moved to" htmlFor="os-moved">
              <select id="os-moved" className={selectCls} value={movedTo} onChange={(e) => setMovedTo(e.target.value)}>
                <option value="">Choose the edition…</option>
                {moveOptions.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.label} ({e.year})
                  </option>
                ))}
              </select>
            </Field>
          )}
          <Field label="Notes" htmlFor="os-notes">
            <Textarea id="os-notes" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </Field>
        </Group>

        {existing && (existing.order_ref || Object.keys(existing.extra ?? {}).length > 0) && (
          <Group title="Other details from the sheet">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs sm:grid-cols-3">
              {existing.order_ref && (
                <div>
                  <dt className="text-muted-foreground">Order ref</dt>
                  <dd className="font-medium text-foreground">{existing.order_ref}</dd>
                </div>
              )}
              {Object.entries(existing.extra ?? {}).map(([k, v]) => (
                <div key={k}>
                  <dt className="text-muted-foreground">{k}</dt>
                  <dd className="font-medium break-words text-foreground">{v}</dd>
                </div>
              ))}
            </dl>
          </Group>
        )}

        {existing && (
          <div className="flex flex-col gap-2 border-t border-border/70 pt-4 text-xs text-muted-foreground">
            {existing.source && <div>Imported from {existing.source}</div>}
            {changes === null ? (
              <button type="button" className="flex items-center gap-1 self-start font-semibold text-primary hover:underline" onClick={() => getOrderChanges(existing.id).then(setChanges).catch(() => setChanges([]))}>
                <History className="size-3.5" aria-hidden="true" /> Show change history
              </button>
            ) : changes.length === 0 ? (
              <div>No edits since this booking was {existing.source ? "imported" : "added"}.</div>
            ) : (
              <ul className="flex flex-col gap-1">
                {changes.map((c) => (
                  <li key={c.id}>
                    <span className="font-semibold text-foreground">{c.changed_by?.name ?? "Someone"}</span> changed{" "}
                    <span className="font-medium text-foreground">{FIELD_LABELS[c.field] ?? c.field.replace(/_/g, " ")}</span>
                    {c.old_value ? ` from ${showValue(c.field, c.old_value, reps)}` : ""} to {c.new_value ? showValue(c.field, c.new_value, reps) : "(blank)"} ·{" "}
                    {new Date(c.changed_at).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      <SheetFooter className="flex-row items-center justify-between gap-2 border-t border-border/70 px-5 py-3">
        <div>
          {existing && canDelete && (
            <Button type="button" variant="ghost" size="sm" className="gap-1.5 text-destructive hover:text-destructive" onClick={remove} disabled={pending}>
              <Trash2 className="size-3.5" aria-hidden="true" /> Delete
            </Button>
          )}
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button type="button" size="sm" onClick={submit} disabled={pending || !client.trim()}>
            {pending ? "Saving…" : existing ? "Save changes" : "Add booking"}
          </Button>
        </div>
      </SheetFooter>
    </>
  );
}
