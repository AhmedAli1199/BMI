"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { FileQuestion, Loader2 } from "lucide-react";
import { toast } from "sonner";
import type { SalesRep } from "@/lib/sales-types";
import { reportUnbookedAd } from "@/lib/deals-actions";
import { searchCompanies } from "@/lib/actions";
import { friendlyError } from "@/lib/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { EntityPicker } from "@/components/entity-picker";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";

const labelCls = "flex flex-col gap-1 text-xs font-semibold text-muted-foreground";
const selectCls = "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";

/** Accounts' check after an issue is out: an advert in the magazine that has no booking behind it. */
export function UnbookedAdButton({ editionId, editionLabel, reps }: { editionId: string; editionLabel: string; reps: SalesRep[] }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [company, setCompany] = useState<{ id: string; label: string } | null>(null);
  const [name, setName] = useState("");
  const [page, setPage] = useState("");
  const [outcome, setOutcome] = useState<"filler" | "needs_booking">("needs_booking");
  const [rep, setRep] = useState("");
  const [note, setNote] = useState("");
  const [pending, start] = useTransition();
  const client = company?.label || name.trim();
  // only someone who can sign in can be asked to make the booking (they get a notification); a filler can name anyone
  const choices = reps.filter((r) => r.active && (outcome === "filler" || r.has_login));
  const hidden = outcome === "needs_booking" ? reps.filter((r) => r.active && !r.has_login).length : 0;

  const reset = () => { setCompany(null); setName(""); setPage(""); setOutcome("needs_booking"); setRep(""); setNote(""); };

  return (
    <>
      <Button size="sm" variant="outline" className="gap-1.5" onClick={() => setOpen(true)}><FileQuestion className="size-3.5" /> Advert with no booking</Button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-full gap-0 overflow-y-auto p-0 sm:max-w-md">
          <SheetHeader className="border-b border-border/70">
            <SheetTitle>An advert with no booking</SheetTitle>
            <SheetDescription>Found in {editionLabel} but not on the order register? Record it as a filler, or ask the salesperson to make the booking so it can be invoiced.</SheetDescription>
          </SheetHeader>
          <div className="flex flex-col gap-4 p-4">
            <EntityPicker label="Client company" placeholder="Search the CRM…" value={company} onChange={setCompany} viewHref={(id) => `/companies/${id}`}
              search={async (q) => (await searchCompanies(q)).map((c) => ({ id: c.id, label: c.name, sublabel: c.industry }))} />
            {!company && <label className={labelCls}>Or type the name<Input value={name} onChange={(e) => setName(e.target.value)} className="h-8 text-sm" /></label>}
            <label className={labelCls}>Page<Input value={page} onChange={(e) => setPage(e.target.value)} placeholder="e.g. 34" className="h-8 w-28 text-sm" /></label>
            <fieldset className="flex flex-col gap-1.5 text-sm">
              <legend className="mb-1 text-xs font-semibold text-muted-foreground">What is it?</legend>
              <label className="flex items-start gap-2"><input type="radio" className="mt-1" checked={outcome === "needs_booking"} onChange={() => setOutcome("needs_booking")} />
                <span>Someone forgot the booking<span className="block text-xs text-muted-foreground">The salesperson is asked to make it. It can be dated back.</span></span></label>
              <label className="flex items-start gap-2"><input type="radio" className="mt-1" checked={outcome === "filler"} onChange={() => setOutcome("filler")} />
                <span>A filler<span className="block text-xs text-muted-foreground">Space given to fill a page, no charge. Recorded on this issue as a filler.</span></span></label>
            </fieldset>
            <label className={labelCls}>Salesperson{outcome === "needs_booking" ? "" : " (optional)"}
              <select className={selectCls} value={choices.some((r) => r.id === rep) ? rep : ""} onChange={(e) => setRep(e.target.value)}>
                <option value="">Choose…</option>
                {choices.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
              </select>
              {hidden > 0 && (
                <span className="font-normal">Only people who can sign in to the Brain are listed, as they&apos;re sent a notification. Tell anyone else yourself.</span>
              )}
            </label>
            <label className={labelCls}>Note (optional)<Textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} className="text-sm" /></label>
          </div>
          <SheetFooter className="flex-row border-t border-border/70">
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button disabled={pending || !client || (outcome === "needs_booking" && !choices.some((r) => r.id === rep))} onClick={() => start(async () => {
              try {
                const chosen = choices.some((r) => r.id === rep) ? rep : "";
                const r = await reportUnbookedAd({ edition_id: editionId, client_name: client, company_id: company?.id ?? null, rep_id: chosen || null,
                  page: page || null, outcome, note: note || null });
                toast.success(r.message);
                reset(); setOpen(false); router.refresh();
              } catch (e) { toast.error(friendlyError(e, "Couldn't record it")); }
            })}>{pending && <Loader2 className="size-3.5 animate-spin" />} {outcome === "filler" ? "Record the filler" : "Ask them to book it"}</Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </>
  );
}
