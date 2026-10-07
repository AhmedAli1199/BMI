"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, ArrowDown, ArrowUp, Check, CheckCheck, Download, Loader2, PackageOpen, Pencil, Plus, Printer, RotateCcw, Sparkles } from "lucide-react";
import { toast } from "sonner";
import type { BrandPage, RateItem, RateSection } from "@/lib/rate-card-types";
import { archiveRateItem, confirmAllRates, editRateItem, loadMediaPack, reorderRateItems } from "@/lib/rate-card-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { InfoHint } from "@/components/sales/info-hint";
import { SalesHeader, YearSwitch, fmtDate } from "@/components/sales/sales-ui";
import { brandColor } from "@/components/rate-card/brand-style";
import { PriceSheet, type PriceSheetTarget } from "@/components/rate-card/price-sheet";
import { OffersPanel } from "@/components/rate-card/offers-panel";
import { NextYearDialog } from "@/components/rate-card/next-year-dialog";
import { HistorySheet } from "@/components/rate-card/history-sheet";
import { OnlineLinks } from "@/components/rate-card/online-links";

const today = () => new Date().toISOString().slice(0, 10);

/** One brand's rate card, laid out like its media pack. Editors change prices in place (click a price)
 * or in the side panel; everyone else sees a clean, read-only price list. */
export function BrandRateCard({ data }: { data: BrandPage }) {
  const router = useRouter();
  const { brand, year } = data;
  const canEdit = brand.can_edit;
  const [sheet, setSheet] = useState<PriceSheetTarget>(null);
  const [pending, start] = useTransition();
  const [showHelp, setShowHelp] = useState(false);
  const refresh = () => router.refresh();
  const filled = data.sections.filter((s) => s.items.length > 0);
  const empty = data.sections.filter((s) => s.items.length === 0);
  const total = filled.reduce((n, s) => n + s.items.length, 0);

  return (
    <>
      <div className="flex flex-col gap-3">
        <span className="masthead-rule w-16" style={{ background: brandColor(brand.key) }} aria-hidden="true" />
        <SalesHeader
          title={`${brand.name} rate card`}
          crumbs={[{ label: "Sales Orders", href: "/sales" }, { label: "Rate card", href: `/sales/rate-card?year=${year}` }]}
          description={`${year} prices, before VAT. ${canEdit ? "Click a price to change it, or open a product for everything else." : "View only - ask an admin, a data manager or this brand's publisher to change a price."}`}
          actions={<YearSwitch years={data.years} current={year} href={(y) => `/sales/rate-card/${brand.key}?year=${y}`} />}
        />
      </div>

      {/* toolbar */}
      <div className="flex flex-wrap items-center gap-2 print-hide">
        {canEdit && <Button size="sm" className="gap-1.5" onClick={() => setSheet({ mode: "add", section: filled[0]?.key ?? "print" })}><Plus className="size-3.5" /> Add a price</Button>}
        {canEdit && total > 0 && <NextYearDialog brand={brand.key} brandName={brand.name} fromYear={year} hasNextYear={data.has_next_year} />}
        <HistorySheet brand={brand.key} year={year} onChanged={refresh} />
        <Button size="sm" variant="outline" className="gap-1.5" nativeButton={false} render={<a href={`/api/files/rate-card/export.xlsx?year=${year}&brand=${brand.key}`} download />}><Download className="size-3.5" /> Excel</Button>
        <Button size="sm" variant="outline" className="gap-1.5" onClick={() => window.print()}><Printer className="size-3.5" /> Print or save as PDF</Button>
        <Button size="sm" variant="ghost" className="ml-auto" aria-expanded={showHelp} onClick={() => setShowHelp(!showHelp)}>How this page works</Button>
      </div>

      {showHelp && (
        <section className="rounded-xl border border-border/80 bg-card p-4 text-sm shadow-2xs print-hide" aria-label="How this page works">
          <ol className="grid list-decimal gap-1.5 pl-5 text-muted-foreground">
            <li><strong className="text-foreground">Change a price:</strong> click the price, type the new one and press Enter. It saves straight away.</li>
            <li><strong className="text-foreground">Change anything else</strong> (name, size, notes, “also called”): click the pencil next to the product.</li>
            <li><strong className="text-foreground">“Please check”</strong> means the price was read from your media pack. If it&apos;s right, press the tick.</li>
            <li><strong className="text-foreground">Next year:</strong> “Prepare {year + 1} prices” copies this list, can raise everything by a percentage, and lets you check each price first.</li>
            <li><strong className="text-foreground">Made a mistake?</strong> “Changes” lists every change, with “Put back”. Removed products can be restored at the bottom of the page.</li>
          </ol>
        </section>
      )}

      {/* load from media pack */}
      {total === 0 && (
        <section className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border/80 bg-card/60 px-6 py-10 text-center">
          <PackageOpen className="size-8 text-muted-foreground" aria-hidden="true" />
          <h2 className="text-base font-bold">No {year} prices yet</h2>
          {brand.seed_available > 0 ? (
            <>
              <p className="max-w-lg text-sm text-muted-foreground">We&apos;ve prepared <strong className="text-foreground">{brand.seed_available} prices</strong> from your {year} media pack. Load them, then check each one - they&apos;ll be marked “Please check” until you do.</p>
              {canEdit && (
                <Button disabled={pending} className="gap-1.5" onClick={() => start(async () => {
                  try { const r = await loadMediaPack(brand.key, year); toast.success(`Loaded ${r.added} prices - now check them`); refresh(); }
                  catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't load the prices"); }
                })}>{pending ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />} Load the {year} media-pack prices</Button>
              )}
            </>
          ) : (
            <p className="max-w-lg text-sm text-muted-foreground">
              {canEdit ? <>Add prices one by one with “Add a price”, or go to {year - 1} and use “Prepare {year} prices” to copy last year&apos;s list.</> : "Nobody has added this year's prices yet."}
            </p>
          )}
        </section>
      )}

      {/* needs check banner */}
      {brand.needs_check > 0 && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border px-4 py-3 text-sm" style={{ borderColor: "color-mix(in oklab, var(--warn) 40%, transparent)", background: "color-mix(in oklab, var(--warn) 8%, transparent)" }}>
          <AlertTriangle className="size-4 shrink-0" style={{ color: "var(--warn)" }} aria-hidden="true" />
          <p className="min-w-0 flex-1"><strong>{brand.needs_check} {brand.needs_check === 1 ? "price or offer needs" : "prices and offers need"} checking.</strong> <span className="text-muted-foreground">{canEdit ? "They came from the media pack. Press “Looks right” on each one that is, or correct it." : "They came from the media pack and haven't been confirmed yet."}</span></p>
          {canEdit && (
            <Button size="sm" variant="outline" className="gap-1.5 print-hide" disabled={pending} onClick={() => {
              if (!window.confirm(`Mark all ${brand.needs_check} as checked? Only do this if you've looked at them all.`)) return;
              start(async () => { try { const r = await confirmAllRates(brand.key, year); toast.success(`${r.confirmed} marked as checked`); refresh(); } catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't save"); } });
            }}><CheckCheck className="size-3.5" /> I&apos;ve checked them all</Button>
          )}
        </div>
      )}

      {/* section jump links */}
      {filled.length > 1 && (
        <nav aria-label="Sections" className="sticky top-0 z-10 -mx-1 flex flex-wrap gap-1.5 bg-background/95 px-1 py-2 backdrop-blur print-hide">
          {filled.map((s) => <a key={s.key} href={`#${s.key}`} className="rounded-full border border-border/80 bg-card px-3 py-1 text-xs font-medium hover:bg-muted">{s.label} <span className="tabular-nums text-muted-foreground">{s.items.length}</span></a>)}
          <a href="#offers" className="rounded-full border border-border/80 bg-card px-3 py-1 text-xs font-medium hover:bg-muted">Offers <span className="tabular-nums text-muted-foreground">{data.offers.length}</span></a>
        </nav>
      )}

      {filled.map((s) => <SectionCard key={s.key} section={s} canEdit={canEdit} onEdit={(item) => setSheet({ mode: "edit", item })} onAdd={() => setSheet({ mode: "add", section: s.key })} onChanged={refresh} />)}

      {canEdit && total > 0 && empty.length > 0 && (
        <p className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground print-hide">
          Add prices to another section:
          {empty.map((s) => <Button key={s.key} size="xs" variant="outline" onClick={() => setSheet({ mode: "add", section: s.key })}><Plus className="size-3" /> {s.label}</Button>)}
        </p>
      )}

      {(total > 0 || data.offers.length > 0) && <OffersPanel brand={brand.key} year={year} offers={data.offers} sections={data.sections} canEdit={canEdit} />}

      <OnlineLinks titles={data.titles} canEdit={canEdit} />

      {data.archived.length > 0 && (
        <details className="rounded-xl border border-border/80 bg-card shadow-2xs print-hide">
          <summary className="cursor-pointer px-4 py-3 text-sm font-semibold">Removed from the rate card ({data.archived.length})</summary>
          <ul className="divide-y divide-border/60 border-t border-border/70">
            {data.archived.map((r) => (
              <li key={r.id} className="flex items-center gap-3 px-4 py-2 text-sm">
                <span className="min-w-0 flex-1 text-muted-foreground line-through">{r.product}</span>
                <span className="text-xs text-muted-foreground tabular-nums">{r.price_label}</span>
                {canEdit && <Button size="xs" variant="outline" className="gap-1" onClick={() => archiveRateItem(r.id, true).then(() => { toast.success(`${r.product} is back`); refresh(); }).catch((e) => toast.error(e instanceof Error ? e.message : "Couldn't restore it"))}><RotateCcw className="size-3" /> Put back</Button>}
              </li>
            ))}
          </ul>
        </details>
      )}

      <PriceSheet target={sheet} brand={brand.key} brandName={brand.name} year={year} sections={data.sections} titles={data.titles} onClose={() => setSheet(null)} onSaved={refresh} />
    </>
  );
}

function SectionCard({ section, canEdit, onEdit, onAdd, onChanged }: { section: RateSection; canEdit: boolean; onEdit: (i: RateItem) => void; onAdd: () => void; onChanged: () => void }) {
  const [, start] = useTransition();
  function move(i: number, d: -1 | 1) {
    const ids = section.items.map((x) => x.id);
    [ids[i], ids[i + d]] = [ids[i + d], ids[i]];
    start(async () => { try { await reorderRateItems(ids); onChanged(); } catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't move it"); } });
  }
  return (
    <section id={section.key} aria-labelledby={`${section.key}-h`} className="scroll-mt-24 overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs print-avoid-break">
      <header className="flex items-center gap-2 border-b border-border/70 px-4 py-3">
        <h2 id={`${section.key}-h`} className="text-sm font-bold">{section.label}</h2>
        <InfoHint>{section.hint}</InfoHint>
        {canEdit && <Button size="xs" variant="ghost" className="ml-auto gap-1 print-hide" onClick={onAdd}><Plus className="size-3" /> Add</Button>}
      </header>
      <table className="w-full text-sm">
        <caption className="sr-only">{section.label} prices</caption>
        <thead className="sr-only"><tr><th scope="col">Product</th><th scope="col">Price</th><th scope="col">Actions</th></tr></thead>
        <tbody>
          {section.items.map((r, i) => (
            <tr key={r.id} className="group border-t border-border/50 first:border-t-0 align-top">
              <td className="px-4 py-2.5">
                <p className="font-medium">{r.product}</p>
                <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                  {r.specs && <span>{r.specs}</span>}
                  {r.aliases.length > 0 && <span title="Also called (how the order register writes it)">Also: {r.aliases.join(", ")}</span>}
                  {r.valid_until && <ValidUntil date={r.valid_until} />}
                </p>
                {r.notes && <p className="mt-0.5 text-xs text-muted-foreground">{r.notes}</p>}
              </td>
              <td className="w-56 px-2 py-2 text-right">
                <PriceCell item={r} canEdit={canEdit} onChanged={onChanged} />
              </td>
              <td className="w-40 px-3 py-2 text-right whitespace-nowrap align-middle print-hide">
                {r.needs_check && (canEdit ? (
                  <Button size="xs" variant="outline" className="gap-1" style={{ borderColor: "color-mix(in oklab, var(--warn) 50%, transparent)" }} title="Read from the media pack - press if it's right"
                    onClick={() => editRateItem(r.id, { needs_check: false }).then(onChanged).catch((e) => toast.error(e instanceof Error ? e.message : "Couldn't save"))}>
                    <Check className="size-3" /> Looks right
                  </Button>
                ) : <span className="text-[11px] font-semibold" style={{ color: "var(--warn)" }}>Please check</span>)}
                {canEdit && (
                  <span className="ml-1 inline-flex opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
                    <Button size="icon-xs" variant="ghost" aria-label={`Move ${r.product} up`} disabled={i === 0} onClick={() => move(i, -1)}><ArrowUp className="size-3" /></Button>
                    <Button size="icon-xs" variant="ghost" aria-label={`Move ${r.product} down`} disabled={i === section.items.length - 1} onClick={() => move(i, 1)}><ArrowDown className="size-3" /></Button>
                    <Button size="icon-xs" variant="ghost" aria-label={`Change ${r.product}`} onClick={() => onEdit(r)}><Pencil className="size-3" /></Button>
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function ValidUntil({ date }: { date: string }) {
  const ended = date < today();
  return <span className="font-medium" style={{ color: ended ? "var(--bad)" : "var(--warn)" }}>{ended ? "Ended" : "Until"} {fmtDate(date)}</span>;
}

/** Click the price, type, press Enter - the quickest way to update a rate card each year. */
function PriceCell({ item, canEdit, onChanged }: { item: RateItem; canEdit: boolean; onChanged: () => void }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState("");
  const [pending, start] = useTransition();
  const sub = item.price_type === "from" ? "starting price" : item.unit !== "each" ? { month: "per month", week: "per week", year: "per year", event: "per event", entry: "per entry" }[item.unit] : null;
  const main = item.price_gbp == null ? "On request" : `£${item.price_gbp.toLocaleString("en-GB", { minimumFractionDigits: item.price_gbp % 1 ? 2 : 0 })}`;

  if (editing) {
    const save = () => {
      const n = Number(value.replace(/[£,\s]/g, ""));
      if (value.trim() === "" || Number.isNaN(n) || n < 0) return toast.error("Type a price in pounds, e.g. 2990");
      if (item.price_gbp && (n > item.price_gbp * 5 || n < item.price_gbp / 5) && !window.confirm(`Change ${item.product} from £${item.price_gbp.toLocaleString("en-GB")} to £${n.toLocaleString("en-GB")}? That's a big change.`)) return;
      start(async () => {
        try { await editRateItem(item.id, { price_gbp: n, price_type: item.price_type === "poa" ? "fixed" : item.price_type }); toast.success(`${item.product}: £${n.toLocaleString("en-GB")}`); setEditing(false); onChanged(); }
        catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't save the price"); }
      });
    };
    return (
      <span className="inline-flex items-center gap-1">
        <span className="text-sm text-muted-foreground">£</span>
        <Input autoFocus aria-label={`New price for ${item.product}`} inputMode="decimal" value={value} disabled={pending} onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") setEditing(false); }} onBlur={() => !pending && setEditing(false)}
          className="h-8 w-28 text-right tabular-nums" />
      </span>
    );
  }
  const content = (
    <>
      <span className={`block font-semibold tabular-nums ${item.price_gbp == null ? "text-muted-foreground" : ""}`}>{item.price_type === "from" && item.price_gbp != null ? `From ${main}` : main}</span>
      {sub && <span className="block text-[11px] text-muted-foreground">{sub}</span>}
    </>
  );
  return canEdit ? (
    <button type="button" onClick={() => { setValue(item.price_gbp != null ? String(item.price_gbp) : ""); setEditing(true); }} title="Click to change the price"
      className="rounded-md px-2 py-0.5 text-right hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring">{content}</button>
  ) : <span className="px-2">{content}</span>;
}
