"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Check, Globe, Pencil, Plus, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import type { SalesRate, SalesTitle } from "@/lib/sales-types";
import { deleteRate, saveRate, saveTitleLinks } from "@/lib/sales-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { InfoHint } from "@/components/sales/info-hint";
import { TitleIcon, fmtGBP } from "@/components/sales/sales-ui";

const inputCls = "h-8 text-sm";

/** One title's prices for the year plus where its digital edition lives -
 * the two things a renewal email needs that the order register doesn't hold. */
export function RateCardEditor({ title, rates, year, canEdit }: { title: SalesTitle; rates: SalesRate[]; year: number; canEdit: boolean }) {
  return (
    <section className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs" aria-labelledby={`t-${title.id}`}>
      <header className="flex items-center gap-2 border-b border-border/70 px-4 py-3">
        <span className="text-muted-foreground"><TitleIcon line={title.product_line} /></span>
        <h2 id={`t-${title.id}`} className="text-sm font-bold">{title.name}</h2>
        <span className="ml-auto text-xs text-muted-foreground">
          {rates.length ? `${rates.length} price${rates.length === 1 ? "" : "s"}` : "No prices yet"}
        </span>
      </header>
      <div className="grid gap-0 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] lg:divide-x divide-border/70">
        <Prices title={title} rates={rates} year={year} canEdit={canEdit} />
        <Links title={title} canEdit={canEdit} />
      </div>
    </section>
  );
}

function Prices({ title, rates, year, canEdit }: { title: SalesTitle; rates: SalesRate[]; year: number; canEdit: boolean }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [editing, setEditing] = useState<string | "new" | null>(null);
  const [draft, setDraft] = useState({ product: "", price: "", notes: "" });

  function edit(r?: SalesRate) {
    setEditing(r ? r.id : "new");
    setDraft(r ? { product: r.product, price: String(r.price_gbp), notes: r.notes ?? "" } : { product: "", price: "", notes: "" });
  }

  function save() {
    const price = Number(draft.price);
    if (!draft.product.trim() || !draft.price || Number.isNaN(price)) {
      toast.error("Enter the product and its price");
      return;
    }
    start(async () => {
      try {
        await saveRate(
          { title_id: title.id, year, product: draft.product.trim(), price_gbp: price, notes: draft.notes.trim() || null },
          editing && editing !== "new" ? editing : undefined
        );
        setEditing(null);
        router.refresh();
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Couldn't save the price");
      }
    });
  }

  const editRow = (key: string) => (
    <tr key={key} className="border-t border-border/60 bg-primary/5">
      <td className="px-4 py-2">
        <Input aria-label="Product" value={draft.product} onChange={(e) => setDraft({ ...draft, product: e.target.value })} placeholder="FP, 1/2, DPS, Banner…" className={inputCls} autoFocus />
      </td>
      <td className="px-2 py-2">
        <Input aria-label="Price in £" type="number" min={0} step={50} value={draft.price} onChange={(e) => setDraft({ ...draft, price: e.target.value })} placeholder="£" className={`${inputCls} text-right tabular-nums`} />
      </td>
      <td className="px-2 py-2">
        <Input aria-label="Notes" value={draft.notes} onChange={(e) => setDraft({ ...draft, notes: e.target.value })} placeholder="Optional" className={inputCls} />
      </td>
      <td className="px-4 py-2 text-right whitespace-nowrap">
        <Button size="icon-sm" onClick={save} disabled={pending} aria-label="Save price"><Check className="size-4" /></Button>
        <Button size="icon-sm" variant="ghost" onClick={() => setEditing(null)} aria-label="Cancel"><X className="size-4" /></Button>
      </td>
    </tr>
  );

  return (
    <div className="flex flex-col">
      <table className="w-full text-sm">
        <caption className="sr-only">{title.name} prices for {year}</caption>
        <thead>
          <tr className="text-left text-xs text-muted-foreground">
            <th scope="col" className="px-4 py-2 font-semibold">
              <span className="flex items-center gap-1">
                Product
                <InfoHint>Use the same shorthand as the order register&apos;s Size column (FP, 1/2, DPS, Banner…) - that&apos;s how a renewal finds the price of what they booked last year. FP / Full page / 1 all match each other.</InfoHint>
              </span>
            </th>
            <th scope="col" className="w-32 px-2 py-2 text-right font-semibold">{year} price</th>
            <th scope="col" className="px-2 py-2 font-semibold">Notes</th>
            <th scope="col" className="w-24 px-4 py-2"><span className="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          {rates.map((r) =>
            editing === r.id ? (
              editRow(r.id)
            ) : (
              <tr key={r.id} className="group border-t border-border/60">
                <td className="px-4 py-2 font-medium">{r.product}</td>
                <td className="px-2 py-2 text-right font-semibold tabular-nums">{fmtGBP(r.price_gbp)}</td>
                <td className="px-2 py-2 text-xs text-muted-foreground">{r.notes}</td>
                <td className="px-4 py-2 text-right whitespace-nowrap">
                  {canEdit && (
                    <span className="opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
                      <Button size="icon-sm" variant="ghost" onClick={() => edit(r)} aria-label={`Edit ${r.product}`}><Pencil className="size-3.5" /></Button>
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        aria-label={`Delete ${r.product}`}
                        onClick={() =>
                          start(async () => {
                            await deleteRate(r.id);
                            router.refresh();
                          })
                        }
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </span>
                  )}
                </td>
              </tr>
            )
          )}
          {editing === "new" && editRow("new")}
          {rates.length === 0 && editing !== "new" && (
            <tr className="border-t border-border/60">
              <td colSpan={4} className="px-4 py-4 text-xs text-muted-foreground">
                No {year} prices yet. Renewal emails for this title won&apos;t quote a price until there&apos;s one here.
              </td>
            </tr>
          )}
        </tbody>
      </table>
      {canEdit && editing === null && (
        <div className="border-t border-border/60 px-4 py-2">
          <Button size="sm" variant="ghost" className="gap-1.5" onClick={() => edit()}>
            <Plus className="size-3.5" /> Add a price
          </Button>
        </div>
      )}
    </div>
  );
}

function Links({ title, canEdit }: { title: SalesTitle; canEdit: boolean }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [page, setPage] = useState(title.digital_page_url ?? "");
  const [issue, setIssue] = useState(title.digital_issue_url ?? "");
  const dirty = page !== (title.digital_page_url ?? "") || issue !== (title.digital_issue_url ?? "");
  const example = (t: string) => t.replace("{edition}", "105").replace("{year}", String(new Date().getFullYear())).replace("{page}", "23");
  return (
    <div className="flex flex-col gap-3 border-t border-border/70 p-4 lg:border-t-0">
      <div className="flex items-center gap-1.5 text-xs font-semibold">
        <Globe className="size-3.5 text-muted-foreground" aria-hidden="true" /> Online edition links
        <InfoHint>
          Renewal emails link the advertiser to last year&apos;s ad. Use {"{edition}"} (the edition name, e.g. 105), {"{year}"} and
          {" {page}"} (the page number from the order register). If the page isn&apos;t known the issue link is used; an
          edition&apos;s own link (set on its page) overrides both.
        </InfoHint>
      </div>
      <label className="flex flex-col gap-1 text-xs text-muted-foreground">
        Link to a page in an issue
        <Input value={page} onChange={(e) => setPage(e.target.value)} disabled={!canEdit} placeholder="https://…/{edition}/page/{page}" className={inputCls} />
        {page && <span className="truncate text-[11px]">e.g. {example(page)}</span>}
      </label>
      <label className="flex flex-col gap-1 text-xs text-muted-foreground">
        Link to an issue
        <Input value={issue} onChange={(e) => setIssue(e.target.value)} disabled={!canEdit} placeholder="https://…/{edition}" className={inputCls} />
        {issue && <span className="truncate text-[11px]">e.g. {example(issue)}</span>}
      </label>
      {canEdit && dirty && (
        <Button
          size="sm"
          className="self-start"
          disabled={pending}
          onClick={() =>
            start(async () => {
              try {
                await saveTitleLinks(title.id, { digital_page_url: page.trim() || null, digital_issue_url: issue.trim() || null });
                toast.success("Links saved");
                router.refresh();
              } catch (e) {
                toast.error(e instanceof Error ? e.message : "Couldn't save the links");
              }
            })
          }
        >
          Save links
        </Button>
      )}
    </div>
  );
}
