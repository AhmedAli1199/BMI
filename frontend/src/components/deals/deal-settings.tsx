"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Settings2 } from "lucide-react";
import { toast } from "sonner";
import type { DealSettings } from "@/lib/deals-types";
import { saveDealSettings } from "@/lib/deals-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { friendlyError } from "@/lib/errors";

const labelCls = "flex flex-col gap-1 text-xs font-semibold text-muted-foreground";

/** What every confirmation carries: BMI's address, footer, terms, artwork specification - and the next booking number. */
export function DealSettingsButton({ settings, titles = [] }: { settings: DealSettings; titles?: { id: string; name: string }[] }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [s, setS] = useState(settings);
  const [pending, start] = useTransition();
  const set = (k: keyof DealSettings) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setS({ ...s, [k]: k === "next_number" ? Number(e.target.value) || 0 : e.target.value });
  return (
    <>
      <Button size="sm" variant="outline" className="gap-1.5" onClick={() => { setS(settings); setOpen(true); }}><Settings2 className="size-3.5" /> Confirmation details</Button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-full gap-0 overflow-y-auto p-0 sm:max-w-lg">
          <SheetHeader className="border-b border-border/70">
            <SheetTitle>Confirmation details</SheetTitle>
            <SheetDescription>{settings.can_edit ? "What every order confirmation and schedule of works carries." : "Only administrators can change these."}</SheetDescription>
          </SheetHeader>
          <div className="flex flex-col gap-4 p-4">
            <label className={labelCls}>Next booking number<Input type="number" value={s.next_number} onChange={set("next_number")} disabled={!s.can_edit} className="h-8 w-32 text-sm" /></label>
            <label className={labelCls}>BMI&apos;s name and address (top right)<Textarea rows={6} value={s.company_block} onChange={set("company_block")} disabled={!s.can_edit} className="text-sm" /></label>
            <label className={labelCls}>Terms line (general)<Textarea rows={2} value={s.terms} onChange={set("terms")} disabled={!s.can_edit} className="text-sm" />
              <span className="font-normal text-[11px]">Used for any publication without its own terms below.</span></label>
            {titles.length > 0 && (
              <details className="rounded-lg border border-border/70 p-3" open={Object.keys(s.terms_by_title ?? {}).length > 0}>
                <summary className="cursor-pointer text-xs font-semibold text-muted-foreground">Terms for each publication</summary>
                <p className="mt-1 text-[11px] text-muted-foreground">Each publication&apos;s confirmations print its own terms (e.g. a link to its terms and conditions). Leave one empty to use the general terms.</p>
                <div className="mt-2 flex flex-col gap-2">
                  {titles.map((t) => (
                    <label key={t.id} className={labelCls}>{t.name}
                      <Textarea rows={2} value={s.terms_by_title?.[t.id] ?? ""} disabled={!s.can_edit} className="text-sm"
                        onChange={(e) => setS({ ...s, terms_by_title: { ...(s.terms_by_title ?? {}), [t.id]: e.target.value } })} />
                    </label>
                  ))}
                </div>
              </details>
            )}
            <label className={labelCls}>Artwork specification (printed when the booking asks for it)<Textarea rows={6} value={s.artwork_specs} onChange={set("artwork_specs")} disabled={!s.can_edit} className="text-xs" /></label>
            <label className={labelCls}>Production - always copied on confirmations
              <Input value={s.production_emails} onChange={set("production_emails")} disabled={!s.can_edit} placeholder="production@bmipublishing.co.uk" className="h-8 text-sm" />
              <span className="font-normal text-[11px]">Every confirmation that&apos;s emailed from BMI Brain copies these addresses. Separate several with commas.</span></label>
            <label className={labelCls}>Accounts - always copied on confirmations
              <Input value={s.accounts_emails} onChange={set("accounts_emails")} disabled={!s.can_edit} placeholder="samantha.elmer@bmipublishing.co.uk" className="h-8 text-sm" />
              <span className="font-normal text-[11px]">These addresses also get each new booking by email as soon as it&apos;s created, with its confirmation attached (sent from the automation mailbox).</span></label>
            <div className="flex flex-col gap-3 rounded-lg border border-border/70 bg-muted/20 p-3">
              <p className="text-xs font-semibold">Filled in on every new booking</p>
              <p className="-mt-2 text-[11px] text-muted-foreground">The salesperson can still change these on each booking.</p>
              <label className={labelCls}>Production contact
                <Input value={s.default_production_contact} onChange={set("default_production_contact")} disabled={!s.can_edit} placeholder="e.g. Steve Hunter - production@bmipublishing.co.uk" className="h-8 text-sm" />
                <span className="font-normal text-[11px]">Left empty: the first production address above is used.</span></label>
              <label className={labelCls}>Copy and artwork<Textarea rows={2} value={s.default_copy_instructions} onChange={set("default_copy_instructions")} disabled={!s.can_edit} placeholder="e.g. All insertions proofed and signed off before publication" className="text-sm" /></label>
              <label className={labelCls}>Special instructions<Textarea rows={2} value={s.default_special_instructions} onChange={set("default_special_instructions")} disabled={!s.can_edit} className="text-sm" /></label>
            </div>
            <label className={labelCls}>Footer<Textarea rows={3} value={s.footer} onChange={set("footer")} disabled={!s.can_edit} className="text-sm" /></label>
          </div>
          {s.can_edit && (
            <SheetFooter className="flex-row border-t border-border/70">
              <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
              <Button disabled={pending} onClick={() => start(async () => {
                try { await saveDealSettings(s); toast.success("Saved"); setOpen(false); router.refresh(); }
                catch (e) { toast.error(friendlyError(e, "Couldn't save")); }
              })}>{pending && <Loader2 className="size-3.5 animate-spin" />} Save</Button>
            </SheetFooter>
          )}
        </SheetContent>
      </Sheet>
    </>
  );
}
