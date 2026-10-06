"use client";

import Link from "next/link";
import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { AlertTriangle, CheckCircle2, ExternalLink, HelpCircle, Undo2 } from "lucide-react";
import type { InvoiceMatch, InvoiceMatchBooking, InvoiceMatchCandidate, InvoiceMatchReason } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { fmtDate, fmtGBP } from "@/components/sales/sales-ui";
import { unlinkXeroInvoice } from "@/lib/sales-actions";

const STATE: Record<string, [string, string]> = {
  paid: ["Paid", "var(--ok)"],
  part_paid: ["Part paid", "var(--warn)"],
  unpaid: ["Awaiting payment", "var(--muted-foreground)"],
  overdue: ["Overdue", "var(--bad)"],
  voided: ["Voided", "var(--muted-foreground)"],
};

const STRENGTH: Record<string, [string, string]> = {
  strong: ["Strong match", "var(--ok)"],
  likely: ["Likely match", "var(--warn)"],
  possible: ["Possible match", "var(--muted-foreground)"],
};

const money = (cur: string, n: number) => (cur === "GBP" ? fmtGBP(n) : `${cur} ${n.toLocaleString("en-GB", { maximumFractionDigits: 2 })}`);

function ReasonRow({ r }: { r: InvoiceMatchReason }) {
  const Icon = r.ok === true ? CheckCircle2 : r.ok === false ? AlertTriangle : HelpCircle;
  const color = r.ok === true ? "var(--ok)" : r.ok === false ? "var(--warn)" : "var(--muted-foreground)";
  return (
    <li className="flex items-start gap-2 text-xs">
      <Icon className="mt-0.5 size-3.5 shrink-0" style={{ color }} aria-hidden="true" />
      <span>
        <span className="font-semibold text-foreground">{r.label}: </span>
        <span className="text-muted-foreground">{r.detail}</span>
        <span className="sr-only">{r.ok === true ? " (matches)" : r.ok === false ? " (doesn't match - check)" : " (unclear)"}</span>
      </span>
    </li>
  );
}

function BookingRow({ b, warn }: { b: InvoiceMatchBooking; warn: boolean }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-md bg-muted/30 px-3 py-2 text-xs">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3">
        <span className="text-sm font-bold text-foreground">{b.client}</span>
        <span className="font-semibold tabular-nums text-foreground">{fmtGBP(b.value_gbp)}</span>
      </div>
      <div className="text-muted-foreground">
        <Link href={`/sales/editions/${b.edition_id}`} className="font-medium text-primary hover:underline">
          {b.edition}
        </Link>
        {b.edition_date && <> · {fmtDate(b.edition_date)}</>}
        {b.size && <> · {b.size}</>}
      </div>
      <div className="text-muted-foreground">
        {b.booked_on ? `Booked ${fmtDate(b.booked_on)}` : "No booking date"}
        {b.rep && <> · {b.rep}</>}
      </div>
      {warn && b.typed_number && (
        <div className="font-medium" style={{ color: "var(--warn)" }}>
          Has invoice number {b.typed_number} typed in, but Xero has no such invoice - linking will replace it.
        </div>
      )}
    </div>
  );
}

export function UndoInvoiceLinkButton({ orderIds }: { orderIds: string[] }) {
  const [pending, start] = useTransition();
  const router = useRouter();
  return (
    <Button
      type="button"
      size="sm"
      variant="outline"
      disabled={pending}
      onClick={() =>
        start(async () => {
          try {
            for (const id of orderIds) await unlinkXeroInvoice(id);
            toast.success("Link removed - the invoice number is cleared from the booking");
          } catch (e) {
            toast.error(e instanceof Error ? e.message : "Couldn't undo the link");
          }
          router.refresh();
        })
      }
    >
      <Undo2 className="size-3.5" aria-hidden="true" />
      Undo this link
    </Button>
  );
}

/** One look is enough: the Xero invoice on the left, the booking(s) it
 * probably belongs to on the right - each with a plain-English checklist of
 * why (client, amount, issue, timing). Pick a booking if there's more than one, then
 * confirm with the card's button. Read-only (no picking) in the resolved lists. */
export function InvoiceMatchPanel({
  match,
  chosen,
  onChoose,
  linked,
}: {
  match: InvoiceMatch;
  chosen?: string | null;
  onChoose?: (key: string) => void;
  linked?: { candidate: string; booking_ids: string[]; auto: boolean };
}) {
  const inv = match.invoice;
  const [stateLabel, stateColor] = STATE[inv.state] ?? [inv.status, "var(--muted-foreground)"];
  const candidates: InvoiceMatchCandidate[] = linked ? match.candidates.filter((c) => c.key === linked.candidate) : match.candidates;
  const picking = !linked && !!onChoose && candidates.length > 1;

  return (
    <div className="flex flex-col gap-3">
      {match.reason && !linked && (
        <p
          role="note"
          className="flex items-start gap-2 rounded-lg bg-[color-mix(in_oklab,var(--warn)_12%,transparent)] px-3 py-2 text-xs font-medium text-foreground"
        >
          <AlertTriangle className="mt-0.5 size-3.5 shrink-0" style={{ color: "var(--warn)" }} aria-hidden="true" />
          <span>
            <span className="font-bold">Why this needs you: </span>
            {match.reason}
          </span>
        </p>
      )}

      <div className="grid gap-3 lg:grid-cols-5">
        <section aria-label="The invoice in Xero" className="flex flex-col gap-2 rounded-lg border border-border/70 p-3 lg:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">Invoice in Xero</h3>
            <a
              href={inv.url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
            >
              Open in Xero
              <ExternalLink className="size-3" aria-hidden="true" />
            </a>
          </div>
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <span className="text-base font-bold tabular-nums text-foreground">{inv.number}</span>
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold" style={{ color: stateColor }}>
              <span aria-hidden="true" className="size-1.5 rounded-full" style={{ background: stateColor }} />
              {stateLabel}
            </span>
          </div>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
            <dt className="text-muted-foreground">Customer</dt>
            <dd className="font-medium text-foreground">{inv.contact ?? "—"}</dd>
            {inv.reference && (
              <>
                <dt className="text-muted-foreground">Reference</dt>
                <dd className="font-medium text-foreground">{inv.reference}</dd>
              </>
            )}
            {inv.lines && (
              <>
                <dt className="text-muted-foreground">For</dt>
                <dd className="whitespace-pre-wrap break-words text-foreground">{inv.lines}</dd>
              </>
            )}
            <dt className="text-muted-foreground">Dated</dt>
            <dd className="text-foreground">{fmtDate(inv.issued_on)}{inv.due_on && <span className="text-muted-foreground"> · due {fmtDate(inv.due_on)}</span>}</dd>
            <dt className="text-muted-foreground">Before VAT</dt>
            <dd className="font-semibold tabular-nums text-foreground">{money(inv.currency, inv.net)}</dd>
            <dt className="text-muted-foreground">Total</dt>
            <dd className="tabular-nums text-foreground">
              {money(inv.currency, inv.total)}
              {inv.state !== "paid" && inv.amount_due > 0 && <span className="text-muted-foreground"> · {money(inv.currency, inv.amount_due)} owed</span>}
            </dd>
          </dl>
        </section>

        <section aria-label="Which booking it is for" className="flex flex-col gap-2 lg:col-span-3">
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-1 text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
              {linked ? (linked.auto ? "Linked automatically to" : "Linked to") : candidates.length > 1 ? "Which booking is it for?" : "The booking it looks like it's for"}
            </legend>
            {candidates.map((c) => {
              const [label, color] = STRENGTH[c.strength] ?? STRENGTH.possible;
              const selected = chosen === c.key;
              const body = (
                <div
                  className={`flex flex-col gap-2 rounded-lg border p-3 transition-colors ${
                    picking
                      ? "border-border/70 peer-checked:border-primary peer-checked:bg-[color-mix(in_oklab,var(--primary)_6%,transparent)] peer-focus-visible:ring-2 peer-focus-visible:ring-ring"
                      : "border-border/70"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="inline-flex items-center gap-1.5 text-xs font-semibold" style={{ color }}>
                      <span aria-hidden="true" className="size-1.5 rounded-full" style={{ background: color }} />
                      {label}
                    </span>
                    {picking && (
                      <span className="text-[11px] font-medium text-muted-foreground">{selected ? "Selected" : "Click to choose"}</span>
                    )}
                  </div>
                  {c.bookings.map((b) => (
                    <BookingRow key={b.id} b={b} warn={!linked} />
                  ))}
                  {c.kind === "sum" && (
                    <p className="text-xs text-muted-foreground">
                      One invoice for {c.bookings.length} bookings - together {fmtGBP(c.total_gbp)}.
                    </p>
                  )}
                  <ul className="flex flex-col gap-1">
                    {c.reasons.map((r) => (
                      <ReasonRow key={r.key} r={r} />
                    ))}
                  </ul>
                  {linked && (
                    <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border/60 pt-2">
                      <span className="text-xs font-semibold" style={{ color: "var(--ok)" }}>
                        {linked.auto ? "Linked on its own - the number, amount and date were filled in." : "Linked after someone confirmed it."}
                      </span>
                      {linked.booking_ids.length > 0 && <UndoInvoiceLinkButton orderIds={linked.booking_ids} />}
                    </div>
                  )}
                </div>
              );
              return picking ? (
                <label key={c.key} className="relative block cursor-pointer">
                  <input
                    type="radio"
                    name="invoice-match-candidate"
                    className="peer sr-only"
                    checked={selected}
                    onChange={() => onChoose?.(c.key)}
                  />
                  {body}
                </label>
              ) : (
                <div key={c.key}>{body}</div>
              );
            })}
          </fieldset>
        </section>
      </div>

      {!linked && (
        <p className="text-[11px] text-muted-foreground">
          Linking puts the invoice number, amount and date on the booking and shows its payment status from Xero. Nothing is changed in Xero, and you can undo a link from the booking.
        </p>
      )}
    </div>
  );
}
