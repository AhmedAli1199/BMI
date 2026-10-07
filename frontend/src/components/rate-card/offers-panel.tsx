"use client";

import { useState, useTransition } from "react";
import { AlertTriangle, CalendarClock, Layers, Percent, Plus, StickyNote, Trash2 } from "lucide-react";
import { toast } from "sonner";
import type { OfferKind, OfferTier, RateItem, RateOffer, RateSection } from "@/lib/rate-card-types";
import { OFFER_KIND_LABELS } from "@/lib/rate-card-types";
import { deleteOffer, saveOffer } from "@/lib/rate-card-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { InfoHint } from "@/components/sales/info-hint";
import { fmtDate, fmtGBP } from "@/components/sales/sales-ui";

const selectCls = "h-9 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";
const ICONS: Record<OfferKind, typeof Percent> = { volume: Percent, series: Layers, early_bird: CalendarClock, note: StickyNote };
const today = () => new Date().toISOString().slice(0, 10);

/** Builds the plain sentence from the steps, e.g. "Book 2 save 10%, 3 save 20%". */
function suggestLabel(kind: OfferKind, tiers: OfferTier[], what: string): string {
  if (kind === "volume" && tiers.length) return "Book " + tiers.map((t) => `${t.qty} save ${t.discount_pct}%`).join(", ");
  if (kind === "series" && tiers.length) return `${what || "Book more"}: ` + tiers.map((t) => (t.unit_price ? `${t.qty} at ${fmtGBP(t.unit_price)} each` : `${t.qty} for ${fmtGBP(t.total ?? 0)}`)).join(", ");
  return "";
}

/** The brand's deals, in plain sentences. The proposal builder works them out for the salesperson. */
export function OffersPanel({ brand, year, offers, sections, canEdit }: { brand: string; year: number; offers: RateOffer[]; sections: RateSection[]; canEdit: boolean }) {
  const [target, setTarget] = useState<RateOffer | "new" | null>(null);
  const items = sections.flatMap((s) => s.items);
  const nameOf = (id: string) => items.find((i) => i.id === id)?.product;
  return (
    <section id="offers" aria-labelledby="offers-h" className="scroll-mt-24 rounded-xl border border-border/80 bg-card shadow-2xs print-avoid-break">
      <header className="flex flex-wrap items-center gap-2 border-b border-border/70 px-4 py-3">
        <h2 id="offers-h" className="text-sm font-bold">Offers &amp; discounts</h2>
        <InfoHint>Deals the sales team can give: discounts for booking more, series prices, early-bird prices. The proposal builder applies them and shows them on the proposal.</InfoHint>
        {canEdit && <Button size="sm" variant="ghost" className="ml-auto gap-1.5 print-hide" onClick={() => setTarget("new")}><Plus className="size-3.5" /> Add an offer</Button>}
      </header>
      {offers.length === 0 ? (
        <p className="px-4 py-5 text-xs text-muted-foreground">No offers yet. Add one if this brand gives discounts for booking more, series prices or early-bird prices.</p>
      ) : (
        <ul className="divide-y divide-border/60">
          {offers.map((o) => {
            const Icon = ICONS[o.kind];
            const ended = o.valid_until && o.valid_until < today();
            return (
              <li key={o.id}>
                <button type="button" disabled={!canEdit} onClick={() => setTarget(o)} className="flex w-full items-start gap-3 px-4 py-3 text-left enabled:hover:bg-muted/40 disabled:cursor-default">
                  <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold">{o.label}</span>
                    {o.details && <span className="block text-xs text-muted-foreground">{o.details}</span>}
                    <span className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
                      <span>{OFFER_KIND_LABELS[o.kind].label}</span>
                      {o.section && <span>{sections.find((s) => s.key === o.section)?.label}</span>}
                      {o.rate_ids.length > 0 && <span>For: {o.rate_ids.map(nameOf).filter(Boolean).join(", ")}</span>}
                      {o.valid_until && <span style={{ color: ended ? "var(--bad)" : undefined }}>{ended ? "Ended" : "Until"} {fmtDate(o.valid_until)}</span>}
                    </span>
                  </span>
                  {o.needs_check && <span className="inline-flex shrink-0 items-center gap-1 text-[11px] font-semibold" style={{ color: "var(--warn)" }}><AlertTriangle className="size-3" aria-hidden="true" /> Please check</span>}
                </button>
              </li>
            );
          })}
        </ul>
      )}
      <OfferSheet target={target} brand={brand} year={year} sections={sections} onClose={() => setTarget(null)} />
    </section>
  );
}

function OfferSheet({ target, brand, year, sections, onClose }: { target: RateOffer | "new" | null; brand: string; year: number; sections: RateSection[]; onClose: () => void }) {
  return (
    <Sheet open={target !== null} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right" className="w-full gap-0 p-0 sm:max-w-lg">
        {target && <OfferForm key={target === "new" ? "new" : target.id} offer={target === "new" ? null : target} brand={brand} year={year} sections={sections} onClose={onClose} />}
      </SheetContent>
    </Sheet>
  );
}

function OfferForm({ offer, brand, year, sections, onClose }: { offer: RateOffer | null; brand: string; year: number; sections: RateSection[]; onClose: () => void }) {
  const [pending, start] = useTransition();
  const [kind, setKind] = useState<OfferKind>(offer?.kind ?? "volume");
  const [section, setSection] = useState(offer?.section ?? "print");
  const [tiers, setTiers] = useState<OfferTier[]>(offer?.rules.tiers ?? (offer ? [] : [{ qty: 2, discount_pct: 10 }]));
  const [rateIds, setRateIds] = useState<string[]>(offer?.rate_ids ?? []);
  const [validUntil, setValidUntil] = useState(offer?.valid_until ?? "");
  const [details, setDetails] = useState(offer?.details ?? "");
  const items: RateItem[] = sections.find((s) => s.key === section)?.items ?? [];
  const what = rateIds.map((id) => items.find((i) => i.id === id)?.product).filter(Boolean).join(" / ");
  const suggested = suggestLabel(kind, tiers, what);
  const [label, setLabel] = useState(offer?.label ?? "");
  const [labelTouched, setLabelTouched] = useState(!!offer);
  const shownLabel = labelTouched ? label : suggested;

  function changeKind(k: OfferKind) {
    setKind(k);
    if (k === "volume") setTiers([{ qty: 2, discount_pct: 10 }]);
    else if (k === "series") setTiers([{ qty: 2, unit_price: 0 }]);
    else setTiers([]);
  }
  function setTier(i: number, patch: Partial<OfferTier>) {
    setTiers(tiers.map((t, j) => (j === i ? { ...t, ...patch } : t)));
  }

  function save() {
    if (!shownLabel.trim()) return toast.error("Describe the offer in a sentence, e.g. Book 2 adverts save 10%.");
    start(async () => {
      try {
        await saveOffer(brand, year, { kind, label: shownLabel.trim(), details: details.trim() || null, rules: tiers.length ? { tiers } : {}, rate_ids: rateIds,
          section, valid_until: validUntil || null }, offer?.id);
        toast.success("Offer saved");
        onClose();
      } catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't save the offer"); }
    });
  }
  function remove() {
    if (!offer || !window.confirm("Delete this offer?")) return;
    start(async () => { try { await deleteOffer(offer.id); toast.success("Offer deleted"); onClose(); } catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't delete it"); } });
  }

  return (
    <>
      <SheetHeader className="border-b border-border/70 px-5 py-4">
        <SheetTitle className="pr-8 text-base font-bold">{offer ? "Change offer" : "Add an offer"}</SheetTitle>
        <SheetDescription className="text-xs">{year} prices</SheetDescription>
      </SheetHeader>
      <div className="flex flex-1 flex-col gap-5 overflow-y-auto px-5 py-4">
        <fieldset>
          <legend className="mb-1.5 text-xs font-semibold text-muted-foreground">What kind of offer?</legend>
          <div className="grid gap-2 sm:grid-cols-2">
            {(Object.keys(OFFER_KIND_LABELS) as OfferKind[]).map((k) => (
              <label key={k} className={`flex cursor-pointer flex-col gap-0.5 rounded-lg border p-2.5 text-xs ${kind === k ? "border-primary bg-primary/5" : "border-border/80 hover:bg-muted/40"}`}>
                <span className="flex items-center gap-2 font-semibold text-foreground">
                  <input type="radio" name="of-kind" checked={kind === k} onChange={() => changeKind(k)} className="size-3.5 accent-[var(--primary)]" />
                  {OFFER_KIND_LABELS[k].label}
                </span>
                <span className="text-muted-foreground">{OFFER_KIND_LABELS[k].hint}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="of-section" className="text-xs font-semibold text-muted-foreground">Which part of the rate card?</Label>
          <select id="of-section" className={selectCls} value={section} onChange={(e) => { setSection(e.target.value); setRateIds([]); }}>
            {sections.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
          </select>
        </div>

        {items.length > 0 && (kind === "series" || kind === "early_bird" || kind === "volume") && (
          <fieldset>
            <legend className="mb-1.5 flex items-center gap-1 text-xs font-semibold text-muted-foreground">Only for these products (optional) <InfoHint>Leave all unticked if it applies to everything in this section.</InfoHint></legend>
            <div className="flex max-h-40 flex-col gap-1 overflow-y-auto rounded-lg border border-border/70 p-2">
              {items.map((i) => (
                <label key={i.id} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={rateIds.includes(i.id)} onChange={(e) => setRateIds(e.target.checked ? [...rateIds, i.id] : rateIds.filter((x) => x !== i.id))} className="size-4 accent-[var(--primary)]" />
                  {i.product} <span className="text-xs text-muted-foreground">{i.price_label}</span>
                </label>
              ))}
            </div>
          </fieldset>
        )}

        {kind === "volume" && (
          <fieldset>
            <legend className="mb-1.5 text-xs font-semibold text-muted-foreground">The discounts</legend>
            <div className="flex flex-col gap-2">
              {tiers.map((t, i) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  Book <Input aria-label="Number of bookings" type="number" min={2} value={t.qty} onChange={(e) => setTier(i, { qty: Number(e.target.value) })} className="h-8 w-16 tabular-nums" />
                  save <Input aria-label="Discount percent" type="number" min={1} max={99} value={t.discount_pct ?? ""} onChange={(e) => setTier(i, { discount_pct: Number(e.target.value) })} className="h-8 w-16 tabular-nums" /> %
                  <Button size="icon-xs" variant="ghost" aria-label="Remove this step" onClick={() => setTiers(tiers.filter((_, j) => j !== i))}><Trash2 className="size-3" /></Button>
                </div>
              ))}
              <Button size="sm" variant="ghost" className="self-start gap-1.5" onClick={() => setTiers([...tiers, { qty: (tiers.at(-1)?.qty ?? 1) + 1, discount_pct: (tiers.at(-1)?.discount_pct ?? 0) + 10 }])}><Plus className="size-3.5" /> Add a step</Button>
            </div>
          </fieldset>
        )}

        {kind === "series" && (
          <fieldset>
            <legend className="mb-1.5 text-xs font-semibold text-muted-foreground">The series prices</legend>
            <div className="flex flex-col gap-2">
              {tiers.map((t, i) => (
                <div key={i} className="flex flex-wrap items-center gap-2 text-sm">
                  Book <Input aria-label="Number of bookings" type="number" min={2} value={t.qty} onChange={(e) => setTier(i, { qty: Number(e.target.value) })} className="h-8 w-16 tabular-nums" />
                  at £<Input aria-label="Price each" type="number" min={0} value={t.unit_price ?? (t.total && t.qty ? Math.round((t.total / t.qty) * 100) / 100 : "")} onChange={(e) => setTier(i, { unit_price: Number(e.target.value), total: undefined })} className="h-8 w-24 tabular-nums" /> each
                  <Button size="icon-xs" variant="ghost" aria-label="Remove this step" onClick={() => setTiers(tiers.filter((_, j) => j !== i))}><Trash2 className="size-3" /></Button>
                </div>
              ))}
              <Button size="sm" variant="ghost" className="self-start gap-1.5" onClick={() => setTiers([...tiers, { qty: (tiers.at(-1)?.qty ?? 1) + 1, unit_price: tiers.at(-1)?.unit_price ?? 0 }])}><Plus className="size-3.5" /> Add a step</Button>
            </div>
          </fieldset>
        )}

        {(kind === "early_bird" || kind === "volume" || kind === "series") && (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="of-until" className="text-xs font-semibold text-muted-foreground">{kind === "early_bird" ? "Ends on" : "Ends on (optional)"}</Label>
            <Input id="of-until" type="date" value={validUntil ?? ""} onChange={(e) => setValidUntil(e.target.value)} className="w-48" />
          </div>
        )}

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="of-label" className="text-xs font-semibold text-muted-foreground">How it reads on the rate card and proposals</Label>
          <Input id="of-label" value={shownLabel} onChange={(e) => { setLabel(e.target.value); setLabelTouched(true); }} placeholder="e.g. Book 2 adverts save 10%, 3 save 20%" />
          {!labelTouched && suggested && <span className="text-[11px] text-muted-foreground">Written for you from the steps above - change it if you like.</span>}
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="of-details" className="text-xs font-semibold text-muted-foreground">More detail (optional)</Label>
          <Textarea id="of-details" rows={2} value={details} onChange={(e) => setDetails(e.target.value)} placeholder="e.g. A full page then works out at £1,995 per advert." />
        </div>
      </div>
      <SheetFooter className="flex-row items-center justify-between gap-2 border-t border-border/70 px-5 py-3">
        <div>{offer && <Button variant="ghost" size="sm" className="gap-1.5 text-destructive hover:text-destructive" onClick={remove} disabled={pending}><Trash2 className="size-3.5" /> Delete</Button>}</div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onClose}>Cancel</Button>
          <Button size="sm" onClick={save} disabled={pending}>{pending ? "Saving…" : "Save offer"}</Button>
        </div>
      </SheetFooter>
    </>
  );
}
