"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { ListTree, Loader2, Pencil, Plus } from "lucide-react";
import { toast } from "sonner";
import type { SalesTitle } from "@/lib/sales-types";
import type { BookingProduct } from "@/lib/deals-types";
import { saveBookingProduct } from "@/lib/deals-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { InfoHint } from "@/components/sales/info-hint";
import { friendlyError } from "@/lib/errors";

const SECTIONS: [string, string][] = [
  ["print", "Print magazine"], ["sponsored", "Sponsored content"], ["website", "Website"], ["newsletter", "Newsletter & emails"],
  ["events", "Events & sponsorship"], ["awards", "Awards"], ["listings", "Directory listings"], ["other", "Other"],
];
const BOOKED_BY = { issue: "Pick an issue", dates: "From and To dates", event: "Pick an event" } as const;
type Draft = Omit<BookingProduct, "id" | "rate_ids" | "group"> & { group_label: string };
const words = (s: string) => s.split(",").map((w) => w.trim()).filter(Boolean);

/** Bookings settings: the booking form's Publication drop-down, in BMI's own words (Craig's list, 12 Nov). Each option
 * is filed under one of the existing publications, so figures, commission and history don't change. */
export function PublicationListButton({ products, titles }: { products: BookingProduct[]; titles: SalesTitle[] }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<{ id: string | null; d: Draft; text: Record<string, string> } | null>(null);
  const [pending, start] = useTransition();
  const titleName = (id: string) => titles.find((t) => t.id === id)?.name ?? "-";
  const groups = [...new Set(products.map((p) => p.group))];

  function edit(p: BookingProduct | null) {
    const d: Draft = p
      ? { label: p.label, group_label: p.group, title_id: p.title_id, booked_by: p.booked_by, rate_sections: p.rate_sections, rate_words: p.rate_words,
          rate_exclude: p.rate_exclude, edition_words: p.edition_words, sort_order: p.sort_order, active: p.active }
      : { label: "", group_label: groups[0] ?? "", title_id: titles[0]?.id ?? "", booked_by: "issue", rate_sections: [], rate_words: [], rate_exclude: [],
          edition_words: [], sort_order: (products.at(-1)?.sort_order ?? 0) + 1, active: true };
    setEditing({ id: p?.id ?? null, d, text: { rate_words: d.rate_words.join(", "), rate_exclude: d.rate_exclude.join(", "), edition_words: d.edition_words.join(", ") } });
  }
  const set = (patch: Partial<Draft>) => setEditing((e) => (e ? { ...e, d: { ...e.d, ...patch } } : e));
  const setText = (k: string, v: string) => setEditing((e) => (e ? { ...e, text: { ...e.text, [k]: v } } : e));

  function save() {
    if (!editing) return;
    const d = { ...editing.d, rate_words: words(editing.text.rate_words), rate_exclude: words(editing.text.rate_exclude), edition_words: words(editing.text.edition_words) };
    if (!d.label.trim() || !d.title_id) return toast.error("Give it a name and choose what it's filed under.");
    start(async () => {
      try {
        await saveBookingProduct(editing.id, d);
        toast.success("Saved");
        setEditing(null);
        router.refresh();
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't save that option. Try again."));
      }
    });
  }

  const sel = "h-8 w-full rounded-md border border-input bg-background px-2 text-sm";
  const lbl = "flex flex-col gap-1 text-xs font-semibold text-muted-foreground";
  return (
    <>
      <Button size="sm" variant="outline" className="gap-1.5" onClick={() => { setEditing(null); setOpen(true); }}><ListTree className="size-3.5" /> Publication list</Button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-full gap-0 overflow-y-auto p-0 sm:max-w-xl">
          <SheetHeader className="border-b border-border/70">
            <SheetTitle>{editing ? (editing.id ? "Change option" : "Add an option") : "Publication list"}</SheetTitle>
            <SheetDescription>
              The choices in a booking item&apos;s Publication drop-down, in BMI&apos;s own words. Each one is filed under one of the
              publications the order book uses, so figures, commission and last year&apos;s comparisons don&apos;t change.
            </SheetDescription>
          </SheetHeader>
          {!editing ? (
            <div className="flex flex-col gap-4 p-4">
              {groups.map((g) => (
                <div key={g}>
                  <p className="mb-1 text-xs font-bold uppercase tracking-wide text-muted-foreground">{g || "Other"}</p>
                  <ul className="divide-y divide-border/60 rounded-lg border border-border/70">
                    {products.filter((p) => p.group === g).map((p) => (
                      <li key={p.id} className="flex items-center gap-3 px-3 py-2 text-sm">
                        <span className="min-w-0 flex-1">
                          <span className={`font-semibold ${p.active ? "" : "text-muted-foreground line-through"}`}>{p.label}</span>
                          <span className="block text-[11px] text-muted-foreground">
                            Filed under {titleName(p.title_id)} · {BOOKED_BY[p.booked_by]} · {p.rate_ids.length ? `${p.rate_ids.length} prices` : "Nothing on the rate card"}
                          </span>
                        </span>
                        <Button size="icon-sm" variant="ghost" aria-label={`Change ${p.label}`} onClick={() => edit(p)}><Pencil className="size-3.5" /></Button>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
              <Button size="sm" variant="outline" className="self-start gap-1.5" onClick={() => edit(null)}><Plus className="size-3.5" /> Add an option</Button>
            </div>
          ) : (
            <div className="flex flex-col gap-3 p-4">
              <label className={lbl}>Name in the drop-down<Input value={editing.d.label} onChange={(e) => set({ label: e.target.value })} placeholder="e.g. OBH Weekly Newsletter" className="h-8 text-sm" /></label>
              <label className={lbl}>Heading it sits under<Input value={editing.d.group_label} onChange={(e) => set({ group_label: e.target.value })} list="pl-groups" className="h-8 text-sm" />
                <datalist id="pl-groups">{groups.map((g) => <option key={g} value={g} />)}</datalist></label>
              <label className={lbl}><span className="flex items-center gap-1">Filed under <InfoHint>The publication the order book, figures and commission count it in. Changing this changes which figures new bookings appear in.</InfoHint></span>
                <select className={sel} value={editing.d.title_id} onChange={(e) => set({ title_id: e.target.value })}>
                  {titles.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select></label>
              <label className={lbl}>How it&apos;s booked
                <select className={sel} value={editing.d.booked_by} onChange={(e) => set({ booked_by: e.target.value as Draft["booked_by"] })}>
                  {Object.entries(BOOKED_BY).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select></label>
              <fieldset className="flex flex-col gap-1">
                <legend className="mb-1 flex items-center gap-1 text-xs font-semibold text-muted-foreground">Prices from these rate-card sections <InfoHint>None ticked: every price of the publication it&apos;s filed under.</InfoHint></legend>
                <div className="grid grid-cols-2 gap-1.5 text-sm">
                  {SECTIONS.map(([k, v]) => (
                    <label key={k} className="flex items-center gap-2">
                      <input type="checkbox" checked={editing.d.rate_sections.includes(k)}
                        onChange={(e) => set({ rate_sections: e.target.checked ? [...editing.d.rate_sections, k] : editing.d.rate_sections.filter((x) => x !== k) })} />{v}
                    </label>
                  ))}
                </div>
              </fieldset>
              <label className={lbl}><span className="flex items-center gap-1">Only prices with these words <InfoHint>Separate with commas, e.g. solus, dedicated. Leave empty for all of them.</InfoHint></span>
                <Input value={editing.text.rate_words} onChange={(e) => setText("rate_words", e.target.value)} className="h-8 text-sm" /></label>
              <label className={lbl}>Leave out prices with these words<Input value={editing.text.rate_exclude} onChange={(e) => setText("rate_exclude", e.target.value)} className="h-8 text-sm" /></label>
              <label className={lbl}><span className="flex items-center gap-1">Only issues or events with these words <InfoHint>e.g. dinner, to list only Dinner Club dates. If none match, all of the publication&apos;s are listed.</InfoHint></span>
                <Input value={editing.text.edition_words} onChange={(e) => setText("edition_words", e.target.value)} className="h-8 text-sm" /></label>
              <div className="grid grid-cols-2 gap-3">
                <label className={lbl}>Order in the list<Input type="number" value={editing.d.sort_order} onChange={(e) => set({ sort_order: Number(e.target.value) || 0 })} className="h-8 text-sm" /></label>
                <label className="flex items-center gap-2 pt-5 text-sm"><input type="checkbox" checked={editing.d.active} onChange={(e) => set({ active: e.target.checked })} /> In the drop-down</label>
              </div>
            </div>
          )}
          {editing && (
            <SheetFooter className="flex-row justify-end gap-2 border-t border-border/70">
              <Button variant="outline" onClick={() => setEditing(null)}>Back</Button>
              <Button onClick={save} disabled={pending}>{pending && <Loader2 className="size-3.5 animate-spin" />} Save</Button>
            </SheetFooter>
          )}
        </SheetContent>
      </Sheet>
    </>
  );
}
