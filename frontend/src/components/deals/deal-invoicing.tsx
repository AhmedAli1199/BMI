"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { CalendarClock, Loader2, Lock, LockOpen } from "lucide-react";
import { toast } from "sonner";
import type { Deal, DealScheduleRow } from "@/lib/deals-types";
import { relockDeal, setInvoiceDate, unlockDeal } from "@/lib/deals-actions";
import { friendlyError } from "@/lib/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { fmtDate } from "@/components/sales/sales-ui";

/** The invoice column: when it's due, and for accounts a way to set their own date ("remind me on"). */
export function InvoiceDue({ deal, row }: { deal: Deal; row: DealScheduleRow }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [when, setWhen] = useState(row.invoice_due ?? "");
  const [pending, start] = useTransition();
  const save = (due: string | null) => start(async () => {
    try { await setInvoiceDate(deal.id, [row.order_id!], due); toast.success(due ? `Reminder set for ${fmtDate(due)}` : "Back to the booking's rule"); setOpen(false); router.refresh(); }
    catch (e) { toast.error(friendlyError(e, "Couldn't change the date")); }
  });
  const label = row.invoice_due ? `Due ${fmtDate(row.invoice_due)}` : "Date not known yet";
  if (!deal.can_approve || !row.order_id) return <span className="text-muted-foreground">{label}{row.invoice_due_set ? " (set by accounts)" : ""}</span>;
  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)} className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground hover:underline" title="Set your own date to invoice it">
        <CalendarClock className="size-3" aria-hidden="true" />{label}{row.invoice_due_set ? " · yours" : ""}
      </button>
    );
  }
  return (
    <div className="flex w-56 flex-col gap-1.5">
      <span className="font-semibold">Remind me to invoice on</span>
      <Input type="date" value={when} onChange={(e) => setWhen(e.target.value)} className="h-7 text-xs" aria-label="Remind me to invoice on" />
      <div className="flex flex-wrap gap-1">
        <Button size="sm" className="h-7 px-2 text-xs" disabled={pending || !when} onClick={() => save(when)}>{pending && <Loader2 className="size-3 animate-spin" />} Save</Button>
        {row.invoice_due_set && <Button size="sm" variant="ghost" className="h-7 px-2 text-xs" disabled={pending} onClick={() => save(null)}>Booking&apos;s rule</Button>}
        <Button size="sm" variant="ghost" className="h-7 px-2 text-xs" onClick={() => setOpen(false)}>Cancel</Button>
      </div>
      <span className="text-[11px] text-muted-foreground">The salesperson is told.</span>
    </div>
  );
}

/** Accounts: unlock a locked booking for the salesperson, or lock it again. */
export function LockControls({ deal }: { deal: Deal }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  if (!deal.can_approve) return null;
  const run = (fn: () => Promise<unknown>, ok: string) => start(async () => {
    try { await fn(); toast.success(ok); router.refresh(); } catch (e) { toast.error(friendlyError(e, "Couldn't change the lock")); }
  });
  if (deal.unlocked) {
    return <Button size="sm" variant="outline" className="gap-1.5" disabled={pending} onClick={() => run(() => relockDeal(deal.id), "Locked again")}><Lock className="size-3.5" /> Lock it again</Button>;
  }
  if (!deal.locked) return null;
  return (
    <Button size="sm" variant="outline" className="gap-1.5" disabled={pending}
      onClick={() => { const note = window.prompt("Unlock it so the salesperson can change it. A note for them (optional):", ""); if (note !== null) run(() => unlockDeal(deal.id, note || null), "Unlocked. It locks again when they save."); }}>
      <LockOpen className="size-3.5" /> Unlock for the salesperson
    </Button>
  );
}
