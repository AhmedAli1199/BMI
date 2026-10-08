"use client";

import { useState, useTransition } from "react";
import { AlertTriangle, Check, Plus, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import type { BrandTitle, PriceType, PriceUnit, RateItem, RateSection } from "@/lib/rate-card-types";
import { PRICE_TYPE_LABELS, UNIT_LABELS } from "@/lib/rate-card-types";
import { addRateItem, archiveRateItem, editRateItem } from "@/lib/rate-card-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { InfoHint } from "@/components/sales/info-hint";
import { friendlyError } from "@/lib/errors";

const selectCls = "h-9 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";

const EXAMPLES: Record<string, { name: string; unit: PriceUnit; specs: string }> = {
  print: { name: "e.g. Full page, Half page, Inside front cover", unit: "each", specs: "e.g. 210mm x 297mm" },
  sponsored: { name: "e.g. Sponsored full page, Ask the Expert", unit: "each", specs: "e.g. Double page" },
  website: { name: "e.g. Leaderboard, Fireplace, Banner", unit: "month", specs: "e.g. 728px x 90px" },
  newsletter: { name: "e.g. Newsletter banner, Dedicated email", unit: "each", specs: "e.g. 600px x 150px" },
  events: { name: "e.g. Dinner sponsorship, Connect event place", unit: "event", specs: "" },
  awards: { name: "e.g. Award entry, Gold sponsorship", unit: "entry", specs: "" },
  listings: { name: "e.g. Standard listing, Enhanced listing", unit: "year", specs: "" },
  other: { name: "e.g. Design service, Contract publishing", unit: "each", specs: "" },
};

export type PriceSheetTarget = { mode: "add"; section: string } | { mode: "edit"; item: RateItem } | null;

function Field({ label, hint, htmlFor, children }: { label: string; hint?: React.ReactNode; htmlFor?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-1">
        <Label htmlFor={htmlFor} className="text-xs font-semibold text-muted-foreground">{label}</Label>
        {hint && <InfoHint>{hint}</InfoHint>}
      </div>
      {children}
    </div>
  );
}

/** Add or change one price - the side panel. Plain questions, an example under every box. */
export function PriceSheet({ target, brand, brandName, year, sections, titles, onClose, onSaved }: {
  target: PriceSheetTarget; brand: string; brandName: string; year: number; sections: RateSection[]; titles: BrandTitle[];
  onClose: () => void; onSaved: () => void;
}) {
  return (
    <Sheet open={target !== null} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right" className="w-full gap-0 p-0 sm:max-w-lg">
        {target && <Form key={target.mode === "edit" ? target.item.id : `add-${target.section}`} target={target} brand={brand} brandName={brandName} year={year} sections={sections} titles={titles} onClose={onClose} onSaved={onSaved} />}
      </SheetContent>
    </Sheet>
  );
}

function Form({ target, brand, brandName, year, sections, titles, onClose, onSaved }: {
  target: NonNullable<PriceSheetTarget>; brand: string; brandName: string; year: number; sections: RateSection[]; titles: BrandTitle[];
  onClose: () => void; onSaved: () => void;
}) {
  const item = target.mode === "edit" ? target.item : null;
  const [pending, start] = useTransition();
  const [section, setSection] = useState(item?.section ?? (target.mode === "add" ? target.section : "print"));
  const ex = EXAMPLES[section] ?? EXAMPLES.other;
  const [product, setProduct] = useState(item?.product ?? "");
  const [priceType, setPriceType] = useState<PriceType>(item?.price_type ?? "fixed");
  const [price, setPrice] = useState(item?.price_gbp != null ? String(item.price_gbp) : "");
  const [unit, setUnit] = useState<PriceUnit>(item?.unit ?? ex.unit);
  const [specs, setSpecs] = useState(item?.specs ?? "");
  const [aliases, setAliases] = useState<string[]>(item?.aliases ?? []);
  const [alias, setAlias] = useState("");
  const [notes, setNotes] = useState(item?.notes ?? "");
  const [validUntil, setValidUntil] = useState(item?.valid_until ?? "");
  const sectionDefault = sections.find((s) => s.key === section)?.default_title_id ?? null;
  const [titleId, setTitleId] = useState<string | null>(item?.title_id ?? null);
  const [showMore, setShowMore] = useState(!!item && (item.title_id !== sectionDefault));

  const priceNum = Number(price.replace(/[£,\s]/g, ""));
  const priceOk = priceType === "poa" || (price.trim() !== "" && !Number.isNaN(priceNum) && priceNum >= 0);
  const ready = product.trim() && priceOk;

  function addAlias() {
    const a = alias.trim();
    if (a && !aliases.includes(a)) setAliases([...aliases, a]);
    setAlias("");
  }

  function save(extra: { needs_check?: boolean } = {}) {
    if (!ready) return toast.error(product.trim() ? "Type the price, or choose “Price on request”." : "Give the product a name.");
    const input = {
      section, product: product.trim(), price_type: priceType, price_gbp: priceType === "poa" ? null : priceNum, unit,
      specs: specs.trim() || null, aliases: alias.trim() ? [...aliases, alias.trim()] : aliases, notes: notes.trim() || null,
      valid_until: validUntil || null, title_id: titleId ?? sectionDefault, ...extra,
    };
    start(async () => {
      try {
        if (item) await editRateItem(item.id, input);
        else await addRateItem(brand, year, input);
        toast.success(item ? "Price saved" : `Added ${input.product}`);
        onSaved();
        onClose();
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't save the price"));
      }
    });
  }

  function remove() {
    if (!item) return;
    start(async () => {
      try {
        await archiveRateItem(item.id);
        toast.success(`Removed ${item.product}`, {
          action: { label: "Undo", onClick: () => archiveRateItem(item.id, true).then(onSaved).catch(() => toast.error("Couldn't put it back")) },
        });
        onSaved();
        onClose();
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't remove it"));
      }
    });
  }

  return (
    <>
      <SheetHeader className="border-b border-border/70 px-5 py-4">
        <SheetTitle className="pr-8 text-base font-bold">{item ? `Change ${item.product}` : "Add a price"}</SheetTitle>
        <SheetDescription className="text-xs">{brandName} · {year} prices · before VAT</SheetDescription>
      </SheetHeader>

      <div className="flex flex-1 flex-col gap-5 overflow-y-auto px-5 py-4">
        {item?.needs_check && (
          <div className="flex items-start gap-2.5 rounded-lg border px-3 py-2.5 text-xs" style={{ borderColor: "color-mix(in oklab, var(--warn) 40%, transparent)", background: "color-mix(in oklab, var(--warn) 8%, transparent)" }}>
            <AlertTriangle className="mt-0.5 size-4 shrink-0" style={{ color: "var(--warn)" }} aria-hidden="true" />
            <div className="flex-1">
              <p className="font-semibold text-foreground">Please check this price</p>
              <p className="mt-0.5 text-muted-foreground">{item.source ? `It was read from the ${item.source}.` : "It was added automatically."} If it&apos;s right, say so - or correct it below.</p>
            </div>
            <Button size="xs" variant="outline" disabled={pending} onClick={() => save({ needs_check: false })}><Check className="size-3" /> It&apos;s right</Button>
          </div>
        )}

        <Field label="Section" htmlFor="ps-section" hint="Where it appears on the rate card - the same headings as your media pack.">
          <select id="ps-section" className={selectCls} value={section} onChange={(e) => { setSection(e.target.value); if (!item) setUnit((EXAMPLES[e.target.value] ?? EXAMPLES.other).unit); }}>
            {sections.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
          </select>
        </Field>

        <Field label="What is it called?" htmlFor="ps-name">
          <Input id="ps-name" value={product} onChange={(e) => setProduct(e.target.value)} placeholder={ex.name} autoFocus={!item} />
        </Field>

        <fieldset className="flex flex-col gap-1.5">
          <legend className="mb-1.5 text-xs font-semibold text-muted-foreground">How is it priced?</legend>
          <div className="grid gap-1.5">
            {(Object.keys(PRICE_TYPE_LABELS) as PriceType[]).map((k) => (
              <label key={k} className={`flex cursor-pointer items-start gap-2.5 rounded-lg border px-3 py-2 text-xs ${priceType === k ? "border-primary bg-primary/5" : "border-border/80 hover:bg-muted/40"}`}>
                <input type="radio" name="ps-type" checked={priceType === k} onChange={() => setPriceType(k)} className="mt-0.5 size-3.5 accent-[var(--primary)]" />
                <span><span className="font-semibold text-foreground">{PRICE_TYPE_LABELS[k].label}</span> <span className="text-muted-foreground">- {PRICE_TYPE_LABELS[k].hint}</span></span>
              </label>
            ))}
          </div>
        </fieldset>

        {priceType !== "poa" && (
          <div className="grid grid-cols-2 gap-3">
            <Field label={priceType === "from" ? "Starting price (£)" : "Price (£)"} htmlFor="ps-price" hint="Before VAT, in pounds. Leave out the £ sign and commas if you like.">
              <Input id="ps-price" inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="e.g. 2990" className="tabular-nums" aria-invalid={price !== "" && !priceOk} />
            </Field>
            <Field label="The price is" htmlFor="ps-unit">
              <select id="ps-unit" className={selectCls} value={unit} onChange={(e) => setUnit(e.target.value as PriceUnit)}>
                {(Object.keys(UNIT_LABELS) as PriceUnit[]).map((u) => <option key={u} value={u}>{UNIT_LABELS[u]}</option>)}
              </select>
            </Field>
          </div>
        )}

        <Field label="Size or specs (optional)" htmlFor="ps-specs">
          <Input id="ps-specs" value={specs} onChange={(e) => setSpecs(e.target.value)} placeholder={ex.specs || "e.g. 4 pages"} />
        </Field>

        <Field label="Also called (optional)" hint="The shorthand used on the order register for the same thing - e.g. FP for Full page, 1/2 for Half page. It's how a booking finds this price for renewal emails.">
          <div className="flex flex-wrap items-center gap-1.5">
            {aliases.map((a) => (
              <span key={a} className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/50 py-0.5 pl-2 pr-1 text-xs">
                {a}
                <button type="button" onClick={() => setAliases(aliases.filter((x) => x !== a))} aria-label={`Remove ${a}`} className="rounded-full p-0.5 hover:bg-muted"><X className="size-3" /></button>
              </span>
            ))}
            <Input value={alias} onChange={(e) => setAlias(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); addAlias(); } }}
              placeholder="Type and press Enter" aria-label="Add another name" className="h-8 w-40 text-sm" />
            {alias.trim() && <Button type="button" size="xs" variant="ghost" onClick={addAlias}><Plus className="size-3" /> Add</Button>}
          </div>
        </Field>

        <Field label="Notes for the sales team (optional)" htmlFor="ps-notes">
          <Textarea id="ps-notes" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="e.g. Includes a free Finder listing" maxLength={300} />
        </Field>

        <Field label="Price ends on (optional)" htmlFor="ps-until" hint="For early-bird or limited-time prices. After this date the price is shown as ended.">
          <Input id="ps-until" type="date" value={validUntil ?? ""} onChange={(e) => setValidUntil(e.target.value)} className="w-48" />
        </Field>

        <div>
          <button type="button" className="text-xs font-semibold text-primary hover:underline" aria-expanded={showMore} onClick={() => setShowMore(!showMore)}>
            {showMore ? "Hide" : "Show"} where it&apos;s booked
          </button>
          {showMore && (
            <div className="mt-2">
              <Field label="Booked under" htmlFor="ps-title" hint="The part of the order register these bookings go into. It's set for you from the section - only change it if this product is booked somewhere else.">
                <select id="ps-title" className={selectCls} value={titleId ?? sectionDefault ?? ""} onChange={(e) => setTitleId(e.target.value)}>
                  {titles.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </Field>
            </div>
          )}
        </div>
      </div>

      <SheetFooter className="flex-row items-center justify-between gap-2 border-t border-border/70 px-5 py-3">
        <div>
          {item && (
            <Button type="button" variant="ghost" size="sm" className="gap-1.5 text-destructive hover:text-destructive" onClick={remove} disabled={pending}>
              <Trash2 className="size-3.5" aria-hidden="true" /> Remove from the rate card
            </Button>
          )}
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="outline" size="sm" onClick={onClose}>Cancel</Button>
          <Button type="button" size="sm" onClick={() => save()} disabled={pending || !ready}>{pending ? "Saving…" : item ? "Save changes" : "Add price"}</Button>
        </div>
      </SheetFooter>
    </>
  );
}
