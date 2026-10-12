"use client";

import { useState, useTransition } from "react";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";
import type { BrandTitle, RateSection } from "@/lib/rate-card-types";
import { addRateSection, deleteRateSection, editRateSection } from "@/lib/rate-card-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { InfoHint } from "@/components/sales/info-hint";
import { friendlyError } from "@/lib/errors";

const selectCls = "h-9 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";

export type SectionSheetTarget = { mode: "add" } | { mode: "edit"; section: RateSection } | null;

/** Add, rename or remove one of the brand's own rate-card sections (cover wraps, belly bands, special formats). */
export function SectionSheet({ target, brand, brandName, titles, onClose, onSaved }: {
  target: SectionSheetTarget; brand: string; brandName: string; titles: BrandTitle[]; onClose: () => void; onSaved: () => void;
}) {
  return (
    <Sheet open={target !== null} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right" className="w-full gap-0 p-0 sm:max-w-md">
        {target && (
          <Form key={target.mode === "edit" ? target.section.key : "add"} target={target} brand={brand} brandName={brandName} titles={titles} onClose={onClose} onSaved={onSaved} />
        )}
      </SheetContent>
    </Sheet>
  );
}

function Form({ target, brand, brandName, titles, onClose, onSaved }: {
  target: NonNullable<SectionSheetTarget>; brand: string; brandName: string; titles: BrandTitle[]; onClose: () => void; onSaved: () => void;
}) {
  const sec = target.mode === "edit" ? target.section : null;
  const [label, setLabel] = useState(sec?.label ?? "");
  const [hint, setHint] = useState(sec?.hint ?? "");
  const [titleId, setTitleId] = useState(sec?.default_title_id ?? titles[0]?.id ?? "");
  const [pending, start] = useTransition();

  function save() {
    if (!label.trim()) return toast.error("Give the section a name.");
    start(async () => {
      try {
        const input = { label: label.trim(), hint: hint.trim() || null, title_id: titleId || null };
        if (sec?.id) await editRateSection(sec.id, input);
        else await addRateSection(brand, input);
        toast.success(sec ? "Section saved" : `Added “${input.label}”`);
        onSaved();
        onClose();
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't save the section"));
      }
    });
  }

  function remove() {
    if (!sec?.id) return;
    start(async () => {
      try {
        await deleteRateSection(sec.id!);
        toast.success(`Removed “${sec.label}”`);
        onSaved();
        onClose();
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't remove the section"));
      }
    });
  }

  return (
    <>
      <SheetHeader className="border-b border-border/70 px-5 py-4">
        <SheetTitle className="pr-8 text-base font-bold">{sec ? `Change “${sec.label}”` : "Add a section"}</SheetTitle>
        <SheetDescription className="text-xs">
          {brandName}&apos;s own heading on the rate card, for things the standard sections don&apos;t cover - cover wraps, belly bands, gatefolds,
          sampling. It appears in every year.
        </SheetDescription>
      </SheetHeader>
      <div className="flex flex-1 flex-col gap-5 overflow-y-auto px-5 py-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="ss-label" className="text-xs font-semibold text-muted-foreground">What is it called?</Label>
          <Input id="ss-label" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="e.g. Cover wraps & belly bands" maxLength={80} autoFocus />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="ss-hint" className="text-xs font-semibold text-muted-foreground">Short description (optional)</Label>
          <Input id="ss-hint" value={hint} onChange={(e) => setHint(e.target.value)} placeholder="e.g. Special formats wrapped around or inside the magazine" maxLength={300} />
        </div>
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-1">
            <Label htmlFor="ss-title" className="text-xs font-semibold text-muted-foreground">Booked under</Label>
            <InfoHint>The part of the order register these bookings go into. Each price can still be changed on its own.</InfoHint>
          </div>
          <select id="ss-title" className={selectCls} value={titleId} onChange={(e) => setTitleId(e.target.value)}>
            {titles.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </div>
      </div>
      <SheetFooter className="flex-row items-center justify-between gap-2 border-t border-border/70 px-5 py-3">
        <div>
          {sec && (
            <Button type="button" variant="ghost" size="sm" className="gap-1.5 text-destructive hover:text-destructive" onClick={remove} disabled={pending}
              title={sec.items.length ? "Move or remove its prices first" : undefined}>
              <Trash2 className="size-3.5" aria-hidden="true" /> Remove section
            </Button>
          )}
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="outline" size="sm" onClick={onClose}>Cancel</Button>
          <Button type="button" size="sm" onClick={save} disabled={pending || !label.trim()}>{pending ? "Saving…" : sec ? "Save" : "Add section"}</Button>
        </div>
      </SheetFooter>
    </>
  );
}
