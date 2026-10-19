"use client";

import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Copy, FileInput, Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import type { SalesRep, SalesTitle } from "@/lib/sales-types";
import type { BookingForm, BookingFormInput, DealIssue } from "@/lib/deals-types";
import { deleteBookingForm, getDealIssues, saveBookingForm } from "@/lib/deals-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { InfoHint } from "@/components/sales/info-hint";
import { fmtDate, fmtGBP } from "@/components/sales/sales-ui";
import { friendlyError } from "@/lib/errors";

const labelCls = "flex flex-col gap-1 text-xs font-semibold text-muted-foreground";
const selectCls = "h-8 w-full rounded-lg border border-input bg-background px-2 text-sm font-normal text-foreground";
const SOURCES = { jotform: "Jotform", stova: "Stova", other: "Another form" } as const;

const blank = (): BookingFormInput => ({ name: "", source: "jotform", active: true, title_id: null, edition_id: null, rate_id: null, rep_id: null, description: "", unit_price: null });

/** Online booking forms (Jotform, Stova): each entry waits in the Review Queue; "Create booking" there adds it as a confirmed booking. */
export function BookingFormsButton({ forms, titles, reps }: { forms: BookingForm[]; titles: SalesTitle[]; reps: SalesRep[] }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<{ id: string | null; f: BookingFormInput } | null>(null);
  const [issues, setIssues] = useState<DealIssue[]>([]);
  const [pending, start] = useTransition();
  const titleId = editing?.f.title_id ?? null;

  useEffect(() => {
    if (!titleId) return;
    let live = true;
    getDealIssues(titleId, editing?.f.edition_id ? [editing.f.edition_id] : []).then((x) => { if (live) setIssues(x); }).catch(() => { if (live) setIssues([]); });
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [titleId]);

  const set = (patch: Partial<BookingFormInput>) => setEditing((e) => (e ? { ...e, f: { ...e.f, ...patch } } : e));
  const copy = (text: string) => navigator.clipboard.writeText(text).then(() => toast.success("Copied")).catch(() => toast.error("Couldn't copy - select the address and copy it instead"));

  return (
    <>
      <Button size="sm" variant="outline" className="gap-1.5" onClick={() => { setEditing(null); setOpen(true); }}><FileInput className="size-3.5" /> Online forms</Button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-full gap-0 overflow-y-auto p-0 sm:max-w-xl">
          <SheetHeader className="border-b border-border/70">
            <SheetTitle>{editing ? (editing.id ? "Change form" : "Add a form") : "Online booking forms"}</SheetTitle>
            <SheetDescription>
              {editing ? "What each entry becomes. Entries wait in the Review Queue under Online bookings. Pressing Create booking there adds it straight away as a confirmed booking, without retyping."
                : "Jotform and Stova forms (awards entries, event seats, the Quiz). Each entry waits in the Review Queue. Pressing Create booking there adds it as a confirmed booking, not a pencilled one."}
            </SheetDescription>
          </SheetHeader>

          {!editing ? (
            <div className="flex flex-col gap-3 p-4">
              {forms.length === 0 && <p className="text-sm text-muted-foreground">No forms connected yet. Add one, then paste its address into the form&apos;s webhook setting.</p>}
              {forms.map((f) => (
                <article key={f.id} className="rounded-xl border border-border/80 p-3 text-sm">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-semibold">{f.name} <span className="text-xs font-normal text-muted-foreground">· {SOURCES[f.source]}{!f.active ? " · switched off" : ""}</span></p>
                      <p className="text-xs text-muted-foreground">Each entry becomes: {f.becomes}</p>
                      <p className="text-xs text-muted-foreground">
                        {f.received ? `${f.received} entr${f.received === 1 ? "y" : "ies"} so far, the last on ${fmtDate(f.last_received_at?.slice(0, 10) ?? null)}` : "No entries yet"}
                        {f.received > 0 && <> · <Link href="/automations/review?kind=online_booking" target="_blank" rel="noreferrer" className="text-primary hover:underline">see them</Link></>}
                      </p>
                    </div>
                    <span className="flex shrink-0 gap-1">
                      <Button size="icon-sm" variant="ghost" aria-label={`Change ${f.name}`} onClick={() => setEditing({ id: f.id, f: { name: f.name, source: f.source, active: f.active, title_id: f.title_id, edition_id: f.edition_id, rate_id: f.rate_id, rep_id: f.rep_id, description: f.description, unit_price: f.unit_price } })}><Pencil className="size-3.5" /></Button>
                      <Button size="icon-sm" variant="ghost" aria-label={`Remove ${f.name}`} disabled={pending} onClick={() => {
                        if (!window.confirm(`Remove “${f.name}”? Entries sent to its address after this are turned away. Bookings already made stay.`)) return;
                        start(async () => {
                          try { await deleteBookingForm(f.id); toast.success("Removed"); router.refresh(); }
                          catch (e) { toast.error(friendlyError(e, "Couldn't remove the form")); }
                        });
                      }}><Trash2 className="size-3.5 text-destructive" /></Button>
                    </span>
                  </div>
                  <div className="mt-2 flex items-center gap-1.5">
                    <Input readOnly value={f.address} className="h-7 font-mono text-[11px]" aria-label={`Address for ${f.name}`} onFocus={(e) => e.currentTarget.select()} />
                    <Button size="sm" variant="outline" className="h-7 gap-1 text-xs" onClick={() => copy(f.address)}><Copy className="size-3" /> Copy</Button>
                  </div>
                </article>
              ))}
              <Button size="sm" className="gap-1.5 self-start" onClick={() => setEditing({ id: null, f: blank() })}><Plus className="size-3.5" /> Add a form</Button>
              <div className="rounded-xl bg-muted/40 p-3 text-xs text-muted-foreground">
                <p className="font-semibold text-foreground">Connecting a form</p>
                <ol className="mt-1 list-decimal space-y-0.5 pl-4">
                  <li>Add it here and copy its address.</li>
                  <li>In Jotform, open the form, then Settings, Integrations, Webhooks, and paste the address. In Stova, ask for entries to be sent to the address.</li>
                  <li>Send a test entry. It shows up in the Review Queue under Online bookings within a few seconds.</li>
                </ol>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-4 p-4">
              <label className={labelCls}>Name<Input value={editing.f.name} onChange={(e) => set({ name: e.target.value })} placeholder="Onboard Awards entries" className="h-8 text-sm" /></label>
              <label className={labelCls}>Where it comes from
                <select className={selectCls} value={editing.f.source} onChange={(e) => set({ source: e.target.value as BookingFormInput["source"] })}>
                  {Object.entries(SOURCES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select></label>
              <label className={labelCls}>Title
                <select className={selectCls} value={editing.f.title_id ?? ""} onChange={(e) => set({ title_id: e.target.value || null, edition_id: null })}>
                  <option value="">Choose the title…</option>
                  {titles.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select></label>
              <label className={labelCls}>
                <span className="flex items-center gap-1">Issue or event <InfoHint>Leave it as &quot;not decided&quot; for a form that runs all year: its bookings are marked as still to be allocated.</InfoHint></span>
                <select className={selectCls} value={editing.f.edition_id ?? ""} disabled={!editing.f.title_id} onChange={(e) => set({ edition_id: e.target.value || null })}>
                  <option value="">Not decided - allocate each booking later</option>
                  {issues.map((i) => <option key={i.id} value={i.id}>{i.label}{i.edition_date ? ` · ${fmtDate(i.edition_date)}` : ""}</option>)}
                </select></label>
              <label className={labelCls}>Each entry is<Input value={editing.f.description} onChange={(e) => set({ description: e.target.value })} placeholder="Awards entry" className="h-8 text-sm" /></label>
              <label className={labelCls}>Price each (£, before VAT)
                <Input type="number" min={0} step="0.01" value={editing.f.unit_price ?? ""} onChange={(e) => set({ unit_price: e.target.value === "" ? null : Number(e.target.value) })} className="h-8 w-40 text-sm" />
                <span className="text-[11px] font-normal">If the form asks how many (seats, entries, tickets), the booking is for that many.{editing.f.unit_price ? ` Two would be ${fmtGBP(editing.f.unit_price * 2)}.` : ""}</span></label>
              <label className={labelCls}>Salesperson
                <select className={selectCls} value={editing.f.rep_id ?? ""} onChange={(e) => set({ rep_id: e.target.value || null })}>
                  <option value="">House account</option>
                  {reps.filter((r) => r.active).map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                </select></label>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={editing.f.active} onChange={(e) => set({ active: e.target.checked })} /> Taking entries</label>
            </div>
          )}

          {editing && (
            <SheetFooter className="flex-row border-t border-border/70">
              <Button variant="ghost" onClick={() => setEditing(null)}>Back</Button>
              <Button disabled={pending || !editing.f.name.trim() || !editing.f.title_id} onClick={() => start(async () => {
                try {
                  await saveBookingForm(editing.id, { ...editing.f, name: editing.f.name.trim() });
                  toast.success(editing.id ? "Saved" : "Added - now copy its address into the form");
                  setEditing(null);
                  router.refresh();
                } catch (e) { toast.error(friendlyError(e, "Couldn't save the form")); }
              })}>{pending && <Loader2 className="size-3.5 animate-spin" />} Save</Button>
            </SheetFooter>
          )}
        </SheetContent>
      </Sheet>
    </>
  );
}
