"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { CalendarPlus, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import type { NextYearRow } from "@/lib/editorial-types";
import { applyPlanNextYear, loadPublishedPlan, previewPlanNextYear } from "@/lib/editorial-actions";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { fmtDay } from "@/components/editorial/editorial-ui";

/** "We've prepared your published plan - load it?" */
export function LoadPlanButton({ brand, brandName, year, count }: { brand: string; brandName: string; year: number; count: number }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  return (
    <Button size="sm" disabled={pending} className="gap-1.5" onClick={() => start(async () => {
      try { const r = await loadPublishedPlan(brand, year); toast.success(`Loaded ${r.issues} issues and events with ${r.features} features for ${brandName}`); router.refresh(); }
      catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't load the plan"); }
    })}>{pending ? <Loader2 className="size-3.5 animate-spin" /> : <Sparkles className="size-3.5" />} Load {brandName}&apos;s {year} plan ({count})</Button>
  );
}

/** Copies a brand's issues and events a year on, on the same weekday, deadlines moved with them. */
export function PlanNextYearButton({ brand, brandName, fromYear }: { brand: string; brandName: string; fromYear: number }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<NextYearRow[] | null>(null);
  const [skip, setSkip] = useState<Set<string>>(new Set());
  const [keep, setKeep] = useState(true);
  const [pending, start] = useTransition();
  const to = fromYear + 1;

  function openIt() {
    setOpen(true);
    setRows(null);
    setSkip(new Set());
    start(async () => { try { setRows(await previewPlanNextYear(brand, fromYear)); } catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't prepare it"); setOpen(false); } });
  }
  function save() {
    start(async () => {
      try {
        const r = await applyPlanNextYear(brand, fromYear, keep, [...skip]);
        toast.success(`${r.created} issues and events added to ${r.year} - check their dates`);
        setOpen(false);
        router.push(`/editorial?year=${r.year}&brand=${brand}`);
      } catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't copy the plan"); }
    });
  }
  return (
    <>
      <Button size="sm" variant="outline" className="gap-1.5" onClick={openIt}><CalendarPlus className="size-3.5" /> Plan {to}</Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Start {brandName}&apos;s {to} plan from {fromYear}</DialogTitle>
            <DialogDescription>Each issue and event is copied a year on, on the same day of the week, with its deadlines moved too. Numbered issues carry on the numbering. Everything is marked “please check” so you can confirm the dates.</DialogDescription>
          </DialogHeader>
          {rows === null ? <p className="py-6 text-center text-sm text-muted-foreground">Working it out…</p> : rows.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Everything from {fromYear} is already in {to}.</p>
          ) : (
            <>
              <div className="max-h-[45vh] overflow-y-auto rounded-lg border border-border/70">
                <table className="w-full text-sm">
                  <caption className="sr-only">Issues and events to copy</caption>
                  <thead className="sticky top-0 bg-card"><tr className="text-left text-xs text-muted-foreground">
                    <th scope="col" className="w-10 px-3 py-2"><span className="sr-only">Copy</span></th>
                    <th scope="col" className="px-2 py-2 font-semibold">{fromYear}</th>
                    <th scope="col" className="px-2 py-2 font-semibold">Becomes</th>
                    <th scope="col" className="px-3 py-2 font-semibold">New date</th>
                  </tr></thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.id} className="border-t border-border/60">
                        <td className="px-3 py-1.5"><input type="checkbox" aria-label={`Copy ${r.old_name}`} checked={!skip.has(r.id)} onChange={(e) => { const s = new Set(skip); if (e.target.checked) s.delete(r.id); else s.add(r.id); setSkip(s); }} className="size-4 accent-[var(--primary)]" /></td>
                        <td className="px-2 py-1.5">{r.old_name} <span className="text-xs text-muted-foreground">{r.title_name} · {fmtDay(r.old_date)}</span></td>
                        <td className="px-2 py-1.5 font-semibold">{r.new_name}</td>
                        <td className="px-3 py-1.5 whitespace-nowrap">{fmtDay(r.new_date, true)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={keep} onChange={(e) => setKeep(e.target.checked)} className="size-4 accent-[var(--primary)]" /> Copy the features too, as a starting point</label>
            </>
          )}
          <DialogFooter>
            <DialogClose render={<Button variant="ghost" />}>Cancel</DialogClose>
            <Button onClick={save} disabled={pending || !rows?.length || skip.size === rows.length}>{pending && <Loader2 className="size-4 animate-spin" />} Copy {(rows?.length ?? 0) - skip.size} to {to}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
