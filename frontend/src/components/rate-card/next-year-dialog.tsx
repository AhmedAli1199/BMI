"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, CalendarPlus, Loader2 } from "lucide-react";
import { toast } from "sonner";
import type { NextYearPreview } from "@/lib/rate-card-types";
import { applyNextYear, previewNextYear } from "@/lib/rate-card-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { fmtGBP } from "@/components/sales/sales-ui";
import { friendlyError } from "@/lib/errors";

const selectCls = "h-9 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";

/** "Prepare next year's prices": copy this year's list, optionally raise everything by a percentage,
 * look over (and change) every new price, then save. This year's prices stay as they were. */
export function NextYearDialog({ brand, brandName, fromYear, hasNextYear }: { brand: string; brandName: string; fromYear: number; hasNextYear: boolean }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<1 | 2>(1);
  const [pct, setPct] = useState("0");
  const [roundTo, setRoundTo] = useState(5);
  const [preview, setPreview] = useState<NextYearPreview | null>(null);
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [pending, start] = useTransition();
  const to = fromYear + 1;
  const raise = Number(pct) || 0;

  function next() {
    start(async () => {
      try {
        setPreview(await previewNextYear({ brand, from_year: fromYear, raise_pct: raise, round_to: roundTo }));
        setOverrides({});
        setStep(2);
      } catch (e) { toast.error(friendlyError(e, "Couldn't work out the new prices")); }
    });
  }
  function save() {
    const o: Record<string, number | null> = {};
    for (const [id, v] of Object.entries(overrides)) if (v.trim() !== "" && !Number.isNaN(Number(v))) o[id] = Number(v);
    start(async () => {
      try {
        const r = await applyNextYear({ brand, from_year: fromYear, raise_pct: raise, round_to: roundTo, overrides: o });
        toast.success(`${r.copied} prices ready for ${r.year}`);
        setOpen(false);
        router.push(`/sales/rate-card/${brand}?year=${r.year}`);
      } catch (e) { toast.error(friendlyError(e, "Couldn't save next year's prices")); }
    });
  }

  return (
    <>
      <Button size="sm" variant="outline" className="gap-1.5" onClick={() => { setStep(1); setOpen(true); }}>
        <CalendarPlus className="size-3.5" /> {hasNextYear ? `Add more to ${to}` : `Prepare ${to} prices`}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Prepare {brandName}&apos;s {to} prices</DialogTitle>
            <DialogDescription>
              {step === 1 ? `We copy every ${fromYear} price into ${to}. You can raise them all at once, then check each one before saving. Your ${fromYear} prices don't change.`
                : "Here's every new price. Type over any you want to set yourself, then save."}
            </DialogDescription>
          </DialogHeader>
          {step === 1 ? (
            <div className="grid gap-4">
              <div className="flex flex-col gap-1.5">
                <span className="text-xs font-semibold text-muted-foreground">Raise all prices by</span>
                <div className="flex flex-wrap items-center gap-2">
                  {[0, 3, 5, 10].map((p) => (
                    <button key={p} type="button" onClick={() => setPct(String(p))} aria-pressed={raise === p}
                      className={`rounded-full border px-3 py-1 text-xs font-medium ${raise === p ? "border-primary bg-primary/10" : "border-border text-muted-foreground hover:text-foreground"}`}>
                      {p === 0 ? "Keep the same" : `${p}%`}
                    </button>
                  ))}
                  <span className="text-xs text-muted-foreground">or</span>
                  <Input aria-label="Percentage" type="number" value={pct} onChange={(e) => setPct(e.target.value)} className="h-8 w-20 tabular-nums" /> %
                </div>
              </div>
              {raise !== 0 && (
                <label className="flex flex-col gap-1.5 text-xs font-semibold text-muted-foreground">
                  Round the new prices to the nearest
                  <select className={`${selectCls} w-40`} value={roundTo} onChange={(e) => setRoundTo(Number(e.target.value))}>
                    {[1, 5, 10, 25, 50].map((r) => <option key={r} value={r}>£{r}</option>)}
                  </select>
                </label>
              )}
              <p className="text-xs text-muted-foreground">Offers and early-bird dates are copied too, moved on a year, and marked “Please check”.</p>
            </div>
          ) : preview && (
            preview.rows.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">Every {fromYear} price is already in {to}. Nothing to copy.</p>
            ) : (
              <div className="max-h-[50vh] overflow-y-auto rounded-lg border border-border/70">
                <table className="w-full text-sm">
                  <caption className="sr-only">New prices for {to}</caption>
                  <thead className="sticky top-0 bg-card">
                    <tr className="text-left text-xs text-muted-foreground">
                      <th scope="col" className="px-3 py-2 font-semibold">Product</th>
                      <th scope="col" className="px-2 py-2 text-right font-semibold">{fromYear}</th>
                      <th scope="col" className="w-6" />
                      <th scope="col" className="px-3 py-2 text-right font-semibold">{to}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((r) => (
                      <tr key={r.id} className="border-t border-border/60">
                        <td className="px-3 py-1.5">{r.product}</td>
                        <td className="px-2 py-1.5 text-right text-muted-foreground tabular-nums">{r.old_label}</td>
                        <td><ArrowRight className="size-3 text-muted-foreground" aria-hidden="true" /></td>
                        <td className="px-3 py-1.5 text-right">
                          {r.price_type === "poa" ? <span className="text-xs text-muted-foreground">On request</span> : (
                            <Input aria-label={`${to} price for ${r.product}`} inputMode="decimal" value={overrides[r.id] ?? String(r.new ?? "")}
                              onChange={(e) => setOverrides({ ...overrides, [r.id]: e.target.value })} className="ml-auto h-8 w-28 text-right tabular-nums" />
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}
          {step === 2 && preview && (
            <p className="text-xs text-muted-foreground">
              {preview.rows.length} prices{preview.already_there ? `; ${preview.already_there} already in ${to} are left as they are` : ""}.
              {raise ? ` Raised by ${raise}% and rounded to the nearest ${fmtGBP(roundTo)}.` : ""}
            </p>
          )}
          <DialogFooter>
            {step === 2 ? <Button variant="ghost" onClick={() => setStep(1)} disabled={pending}>Back</Button> : <DialogClose render={<Button variant="ghost" />}>Cancel</DialogClose>}
            {step === 1 ? (
              <Button onClick={next} disabled={pending}>{pending && <Loader2 className="size-4 animate-spin" />} See the new prices</Button>
            ) : (
              <Button onClick={save} disabled={pending || !preview?.rows.length}>{pending && <Loader2 className="size-4 animate-spin" />} Save {to} prices</Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
