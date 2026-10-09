"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Ban, CheckCircle2, Download, FileText, Loader2, Mail, MoreHorizontal, Pencil, Printer, Repeat, Send, Trash2, Undo2 } from "lucide-react";
import { toast } from "sonner";
import type { Deal, DealEmailDraft } from "@/lib/deals-types";
import { deleteDeal, getDealEmailDraft, markDealSent, rebookDeal, sendDeal, setDealStatus } from "@/lib/deals-actions";
import { downloadFile } from "@/lib/download";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { friendlyError } from "@/lib/errors";

const labelCls = "flex flex-col gap-1 text-xs font-semibold text-muted-foreground";

export function DealActions({ d }: { d: Deal }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [cancelOpen, setCancelOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [keepRun, setKeepRun] = useState(true);
  const [send, setSend] = useState<DealEmailDraft | null>(null);
  const [to, setTo] = useState("");
  const [cc, setCc] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const kind = d.document === "schedule" ? "schedule of works" : "confirmation";
  const anyInvoiced = d.schedule.some((s) => s.invoice_number);

  const run = (fn: () => Promise<unknown>, ok: string, fail: string) => start(async () => {
    try { await fn(); toast.success(ok); router.refresh(); } catch (e) { toast.error(friendlyError(e, fail)); }
  });

  function openSend() {
    start(async () => {
      try {
        const dr = await getDealEmailDraft(d.id);
        setSend(dr); setTo(dr.to.join(", ")); setCc(""); setSubject(dr.subject); setBody(dr.body);
      } catch (e) { toast.error(friendlyError(e, "Couldn't start the email")); }
    });
  }

  function rebook() {
    start(async () => {
      try {
        const r = await rebookDeal(d.id);
        r.notes.forEach((n) => toast.info(n));
        if (!r.id) { toast.info(`Next year's issues aren't all in the editorial plan yet. Plan ${"year" in r ? r.year : "next year"} there first, then try again.`); return; }
        toast.success(`Order ${(r as Deal).number} pencilled in for next year`);
        router.push(`/sales/deals/${r.id}`);
      } catch (e) { toast.error(friendlyError(e, "Couldn't rebook it")); }
    });
  }

  return (
    <div className="print-hide flex flex-wrap items-center gap-2">
      {d.can_edit && d.status !== "cancelled" && (
        <Button size="sm" variant="outline" className="gap-1.5" nativeButton={false} render={<Link href={`/sales/deals/${d.id}/edit`} />}><Pencil className="size-3.5" /> Change</Button>
      )}
      {d.can_edit && d.status === "pencilled" && (
        <Button size="sm" className="gap-1.5" disabled={pending} onClick={() => run(() => setDealStatus(d.id, "confirmed"), "Order confirmed", "Couldn't confirm it")}><CheckCircle2 className="size-3.5" /> Confirm</Button>
      )}
      {d.status !== "cancelled" && (
        <Button size="sm" variant={d.status === "confirmed" && !d.sent_at ? "default" : "outline"} className="gap-1.5" disabled={pending || !d.can_edit} onClick={openSend}>
          <Mail className="size-3.5" /> Email the {kind}
        </Button>
      )}
      <Button size="sm" variant="outline" className="gap-1.5" nativeButton={false} render={<Link href={`/sales/deals/${d.id}/print`} target="_blank" rel="noreferrer" />}><Printer className="size-3.5" /> Print or PDF</Button>
      <DropdownMenu>
        <DropdownMenuTrigger render={<Button size="sm" variant="ghost" aria-label="More" disabled={pending}>{pending ? <Loader2 className="size-3.5 animate-spin" /> : <MoreHorizontal className="size-4" />}</Button>} />
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={() => downloadFile(`/api/files/sales/deals/${d.id}/document.docx`, `Order ${d.number}.docx`).catch((e) => toast.error(friendlyError(e, "Couldn't download it")))}>
            <Download className="size-3.5" /> Download as Word
          </DropdownMenuItem>
          {d.can_edit && d.status !== "cancelled" && (
            <DropdownMenuItem onClick={() => run(() => markDealSent(d.id, d.contact_email), "Noted as sent", "Couldn't save that")}><FileText className="size-3.5" /> I sent it another way</DropdownMenuItem>
          )}
          <DropdownMenuItem onClick={rebook}><Repeat className="size-3.5" /> Rebook for next year</DropdownMenuItem>
          {d.can_edit && d.status === "confirmed" && !anyInvoiced && (
            <DropdownMenuItem onClick={() => run(() => setDealStatus(d.id, "pencilled"), "Back to pencilled", "Couldn't change it")}><Undo2 className="size-3.5" /> Back to pencilled</DropdownMenuItem>
          )}
          {d.can_edit && d.status === "cancelled" && (
            <DropdownMenuItem onClick={() => run(() => setDealStatus(d.id, "pencilled"), "Reopened as pencilled", "Couldn't reopen it")}><Undo2 className="size-3.5" /> Reopen</DropdownMenuItem>
          )}
          {d.can_edit && d.status !== "cancelled" && <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => { setReason(""); setKeepRun(true); setCancelOpen(true); }}><Ban className="size-3.5" /> Cancel the order</DropdownMenuItem>
          </>}
          {d.can_edit && d.status === "pencilled" && !anyInvoiced && (
            <DropdownMenuItem onClick={() => {
              if (!window.confirm(`Delete order ${d.number}? Its pencilled bookings go too.`)) return;
              start(async () => { try { await deleteDeal(d.id); toast.success("Deleted"); router.push("/sales/deals"); } catch (e) { toast.error(friendlyError(e, "Couldn't delete it")); } });
            }}><Trash2 className="size-3.5" /> Delete</DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={cancelOpen} onOpenChange={setCancelOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancel order {d.number}?</DialogTitle>
            <DialogDescription>The bookings stay on record as cancelled, with your reason, so the issue figures and commission are right.</DialogDescription>
          </DialogHeader>
          <label className={labelCls}>Why<Input autoFocus value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Budget cut, moved to next year" className="h-8 text-sm" /></label>
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-1" checked={keepRun} onChange={(e) => setKeepRun(e.target.checked)} />
            <span>Keep items that have already run or been invoiced <span className="block text-xs text-muted-foreground">Usually right: they were delivered, so they stay booked.</span></span>
          </label>
          <DialogFooter>
            <DialogClose render={<Button variant="ghost" />}>Keep the order</DialogClose>
            <Button variant="destructive" disabled={pending || !reason.trim()} onClick={() => start(async () => {
              try {
                const r = await setDealStatus(d.id, "cancelled", reason.trim(), keepRun);
                r.notes?.forEach((n) => toast.info(n));
                toast.success("Order cancelled"); setCancelOpen(false); router.refresh();
              } catch (e) { toast.error(friendlyError(e, "Couldn't cancel it")); }
            })}>Cancel the order</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!send} onOpenChange={(o) => !o && setSend(null)}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Email the {kind}</DialogTitle>
            <DialogDescription>
              {send?.outlook_connected
                ? <>Sent from your Outlook ({send.outlook_email}) with the {kind} attached as a Word file, and noted on the client.{d.status === "pencilled" ? " Sending it confirms the order." : ""}</>
                : <>Connect your Outlook in Settings &gt; Email to send from here. Until then, download it as Word or print to PDF and attach it yourself, then use &quot;I sent it another way&quot;.</>}
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <label className={labelCls}>To<Input value={to} onChange={(e) => setTo(e.target.value)} placeholder="name@company.com, another@company.com" className="h-8 text-sm" /></label>
            <label className={labelCls}>Copy to (optional)<Input value={cc} onChange={(e) => setCc(e.target.value)} placeholder={d.invoice_email ?? ""} className="h-8 text-sm" /></label>
            <label className={labelCls}>Subject<Input value={subject} onChange={(e) => setSubject(e.target.value)} className="h-8 text-sm" /></label>
            <label className={labelCls}>Message<Textarea rows={8} value={body} onChange={(e) => setBody(e.target.value)} className="text-sm" /></label>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="ghost" />}>Close</DialogClose>
            <Button className="gap-1.5" disabled={pending || !send?.outlook_connected || !to.trim()} onClick={() => start(async () => {
              const split = (s: string) => s.split(/[,;]/).map((x) => x.trim()).filter(Boolean);
              try {
                await sendDeal(d.id, { to: split(to), cc: split(cc), subject, body });
                toast.success("Sent and noted on the client"); setSend(null); router.refresh();
              } catch (e) { toast.error(friendlyError(e, "Couldn't send it")); }
            })}>{pending ? <Loader2 className="size-3.5 animate-spin" /> : <Send className="size-3.5" />} Send</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
