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

/** What every confirmation carries: BMI's address, footer, terms, artwork specification - and the next order number. */
export function DealSettingsButton({ settings }: { settings: DealSettings }) {
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
            <label className={labelCls}>Next order number<Input type="number" value={s.next_number} onChange={set("next_number")} disabled={!s.can_edit} className="h-8 w-32 text-sm" /></label>
            <label className={labelCls}>BMI&apos;s name and address (top right)<Textarea rows={6} value={s.company_block} onChange={set("company_block")} disabled={!s.can_edit} className="text-sm" /></label>
            <label className={labelCls}>Terms line<Textarea rows={2} value={s.terms} onChange={set("terms")} disabled={!s.can_edit} className="text-sm" /></label>
            <label className={labelCls}>Artwork specification (printed when the order asks for it)<Textarea rows={6} value={s.artwork_specs} onChange={set("artwork_specs")} disabled={!s.can_edit} className="text-xs" /></label>
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
