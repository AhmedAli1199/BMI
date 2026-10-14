"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowDown, ArrowUp, Blocks, ExternalLink, Loader2, Plus, RefreshCw, Trash2, Type } from "lucide-react";
import { BLOCK_OPTIONS, type BlockKind, type ExampleLibrary, type ProposalBlock, type ProposalSection } from "@/lib/proposals-types";
import type { SalesRate, SalesTitle } from "@/lib/sales-types";
import { getExampleLibrary, previewBlock } from "@/lib/proposals-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { RichEmailEditor, EmailBodyView } from "@/components/mail-merge/rich-email-editor";
import { InfoHint } from "@/components/sales/info-hint";

const blockLabel = (k: BlockKind) => BLOCK_OPTIONS.find((b) => b.kind === k)?.label ?? k;

/** A ready-made block: shows exactly what it will say (filled from the Brain's data) and its few settings. */
export function BlockCard({ proposalId, block, onChange, titleId, rates, titles, brand, refreshKey, disabled, startOpen = false }: {
  proposalId: string; block: ProposalBlock; onChange: (b: ProposalBlock) => void; titleId: string | null; rates: SalesRate[]; titles: SalesTitle[];
  brand: string | null; refreshKey: string; disabled: boolean; startOpen?: boolean;
}) {
  const [html, setHtml] = useState<string | null>(null);
  const [lib, setLib] = useState<ExampleLibrary | null>(null);
  const [open, setOpen] = useState(startOpen);
  const cfg = JSON.stringify(block);

  useEffect(() => {
    let live = true;
    previewBlock(proposalId, block).then((h) => { if (live) setHtml(h); }).catch(() => { if (live) setHtml("<p><em>Couldn't show this block just now.</em></p>"); });
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [proposalId, cfg, refreshKey]);

  useEffect(() => {
    if (block.kind !== "examples" || !open || lib || !brand) return;
    getExampleLibrary(brand).then(setLib).catch(() => setLib({ items: [], sectors: {}, formats: [], brands: [] }));
  }, [block.kind, open, lib, brand]);

  const titleRates = useMemo(() => rates.filter((r) => r.title_id === (block.config.title_id ?? titleId)), [rates, block.config.title_id, titleId]);
  const ids = block.config.ids ?? [];
  const rateIds = block.config.rate_ids ?? [];
  const settable = ["prices", "examples", "issues"].includes(block.kind);

  return (
    <div>
      <div className="rounded-lg border border-dashed border-border bg-muted/20 p-3">
        {html === null ? <Loader2 className="size-4 animate-spin text-muted-foreground" /> : <EmailBodyView body={html} className="text-sm" />}
      </div>
      {settable && !disabled && (
        <button type="button" className="mt-2 text-xs font-medium text-primary hover:underline" onClick={() => setOpen(!open)}>
          {open ? "Done choosing" : block.kind === "prices" ? "Choose the products to show" : block.kind === "examples" ? "Choose the examples" : "Choose the title"}
        </button>
      )}
      {open && block.kind === "prices" && (
        <div className="mt-2 grid gap-2 rounded-lg border border-border/70 p-2 text-xs">
          <TitlePick titles={titles} value={block.config.title_id ?? titleId} onChange={(t) => onChange({ ...block, config: { ...block.config, title_id: t, rate_ids: [] } })} />
          {titleRates.length === 0 ? <p className="text-muted-foreground">No rate card prices for this title yet.</p> : (
            <ul className="grid max-h-56 gap-1 overflow-y-auto sm:grid-cols-2">
              {titleRates.map((r) => (
                <li key={r.id}><label className="flex items-start gap-1.5">
                  <input type="checkbox" className="mt-0.5" checked={rateIds.includes(r.id)} onChange={(e) => onChange({ ...block, config: { ...block.config, rate_ids: e.target.checked ? [...rateIds, r.id] : rateIds.filter((x) => x !== r.id) } })} />
                  <span>{r.product}</span>
                </label></li>
              ))}
            </ul>
          )}
          <p className="text-muted-foreground">Nothing ticked: the main print, sponsored and newsletter prices are shown.</p>
        </div>
      )}
      {open && block.kind === "issues" && (
        <div className="mt-2 rounded-lg border border-border/70 p-2 text-xs">
          <TitlePick titles={titles} value={block.config.title_id ?? titleId} onChange={(t) => onChange({ ...block, config: { ...block.config, title_id: t } })} />
        </div>
      )}
      {open && block.kind === "examples" && (
        <div className="mt-2 grid gap-2 rounded-lg border border-border/70 p-2 text-xs">
          {!brand ? <p className="text-muted-foreground">Choose the title first.</p> : !lib ? <Loader2 className="size-4 animate-spin" /> : (
            <>
              <label className="flex items-center gap-1.5 text-muted-foreground">Suggest for
                <select className="h-7 rounded-md border border-input bg-background px-1.5 text-xs text-foreground" value={block.config.sector ?? ""}
                  onChange={(e) => onChange({ ...block, config: { ...block.config, sector: e.target.value || null } })}>
                  <option value="">Any sector</option>
                  {Object.entries(lib.sectors).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
                <InfoHint>Nothing ticked: the Brain picks a few, the client&apos;s sector first. Tick to choose them yourself.</InfoHint>
              </label>
              <ul className="grid max-h-64 gap-1 overflow-y-auto sm:grid-cols-2">
                {lib.items.filter((x) => x.link_ok !== false).map((x) => (
                  <li key={x.id}><label className="flex items-start gap-1.5">
                    <input type="checkbox" className="mt-0.5" checked={ids.includes(x.id)} onChange={(e) => onChange({ ...block, config: { ...block.config, ids: e.target.checked ? [...ids, x.id] : ids.filter((i) => i !== x.id) } })} />
                    <span>{x.label}{x.format ? <span className="text-muted-foreground"> · {x.format}</span> : null}</span>
                  </label></li>
                ))}
              </ul>
              <Link href="/sales/proposals/examples" target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium text-primary hover:underline">Add or change examples <ExternalLink className="size-3" aria-hidden="true" /></Link>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function TitlePick({ titles, value, onChange }: { titles: SalesTitle[]; value: string | null | undefined; onChange: (id: string | null) => void }) {
  return (
    <label className="flex items-center gap-1.5 text-muted-foreground">Title
      <select className="h-7 rounded-md border border-input bg-background px-1.5 text-xs text-foreground" value={value ?? ""} onChange={(e) => onChange(e.target.value || null)}>
        {titles.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
      </select>
    </label>
  );
}

/** Every section of the proposal: rich text (tables and pictures included) or a ready-made block. */
export function ProposalSections({ proposalId, sections, onChange, titleId, titles, rates, brand, refreshKey, disabled }: {
  proposalId: string; sections: ProposalSection[]; onChange: (s: ProposalSection[]) => void; titleId: string | null; titles: SalesTitle[];
  rates: SalesRate[]; brand: string | null; refreshKey: string; disabled: boolean;
}) {
  const set = (id: string, patch: Partial<ProposalSection>) => onChange(sections.map((x) => (x.id === id ? { ...x, ...patch } : x)));
  const move = (i: number, d: -1 | 1) => { const next = [...sections]; [next[i], next[i + d]] = [next[i + d], next[i]]; onChange(next); };
  const add = (kind: BlockKind | "text") => {
    const b = BLOCK_OPTIONS.find((x) => x.kind === kind);
    onChange([...sections, b
      ? { id: crypto.randomUUID(), kind: `block_${b.kind}`, heading: b.heading, body: "", block: { kind: b.kind, config: {} } }
      : { id: crypto.randomUUID(), kind: "custom", heading: "New section", body: "", html: "" }]);
  };

  return (
    <div className="flex flex-col gap-3">
      {sections.map((s, i) => (
        <div key={s.id} className="rounded-xl border border-border/80 bg-card p-3 shadow-2xs">
          <div className="flex items-center gap-1.5">
            {s.block ? <Blocks className="size-4 shrink-0 text-muted-foreground" aria-label={blockLabel(s.block.kind)} /> : <Type className="size-4 shrink-0 text-muted-foreground" aria-label="Text" />}
            <Input aria-label="Section heading" value={s.heading} disabled={disabled} placeholder="Heading (optional)"
              onChange={(e) => set(s.id, { heading: e.target.value })} className="h-8 text-sm font-semibold" />
            {s.block && <span className="hidden shrink-0 rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground sm:inline">{blockLabel(s.block.kind)}</span>}
            {!disabled && <>
              <Button size="icon-sm" variant="ghost" aria-label="Move up" disabled={i === 0} onClick={() => move(i, -1)}><ArrowUp className="size-3.5" /></Button>
              <Button size="icon-sm" variant="ghost" aria-label="Move down" disabled={i === sections.length - 1} onClick={() => move(i, 1)}><ArrowDown className="size-3.5" /></Button>
              <Button size="icon-sm" variant="ghost" aria-label={`Remove ${s.heading || "this section"}`} onClick={() => onChange(sections.filter((x) => x.id !== s.id))}><Trash2 className="size-3.5" /></Button>
            </>}
          </div>
          <div className="mt-2">
            {s.block ? (
              <BlockCard proposalId={proposalId} block={s.block} onChange={(b) => set(s.id, { block: b })} titleId={titleId} rates={rates} titles={titles}
                brand={brand} refreshKey={refreshKey} disabled={disabled} />
            ) : (
              <>
              {s.kind === "investment" && <p className="mb-1.5 text-[11px] text-muted-foreground">The package and prices from the table above go first in this section, then your text.</p>}
              <RichEmailEditor value={s.html ?? s.body ?? ""} onChange={(h) => set(s.id, { html: h })} minHeight="6rem" rich disabled={disabled}
                ariaLabel={`${s.heading || "Section"} text`} />
              </>
            )}
          </div>
        </div>
      ))}
      {!disabled && (
        <DropdownMenu>
          <DropdownMenuTrigger render={<Button size="sm" variant="outline" className="gap-1.5 self-start" />}><Plus className="size-3.5" /> Add</DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-72">
            <DropdownMenuItem onClick={() => add("text")}><Type className="size-3.5" /> Text, tables and pictures</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuLabel className="text-xs">Ready-made, filled in for you</DropdownMenuLabel>
            {BLOCK_OPTIONS.map((b) => (
              <DropdownMenuItem key={b.kind} onClick={() => add(b.kind)}>
                <div className="flex flex-col"><span>{b.label}</span><span className="text-[11px] text-muted-foreground">{b.hint}</span></div>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      )}
      <p className="flex items-center gap-1 text-[11px] text-muted-foreground"><RefreshCw className="size-3" aria-hidden="true" /> Ready-made blocks always show the latest prices, issues and numbers, when you preview and when it&apos;s sent.</p>
    </div>
  );
}
