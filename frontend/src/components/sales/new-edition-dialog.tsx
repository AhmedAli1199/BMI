"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Plus } from "lucide-react";
import type { SalesTitle } from "@/lib/sales-types";
import { createEdition } from "@/lib/sales-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { InfoHint } from "@/components/sales/info-hint";

const selectCls = "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";

/** Replaces "copy the TEMPLATE DO NOT COPY OVER sheet and rename it". */
export function NewEditionDialog({ titles, year, defaultTitleId }: { titles: SalesTitle[]; year: number; defaultTitleId?: string }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [pending, start] = useTransition();
  const [titleId, setTitleId] = useState(defaultTitleId ?? titles[0]?.id ?? "");
  const [ey, setEy] = useState(String(year));
  const [name, setName] = useState("");
  const [date, setDate] = useState("");
  const [period, setPeriod] = useState("");
  const [rate, setRate] = useState("");
  const [target, setTarget] = useState("");

  function submit() {
    const r = rate.trim() ? Number(rate) : null;
    const t = target.trim() ? Number(target.replace(/[£,]/g, "")) : null;
    if ((r !== null && Number.isNaN(r)) || (t !== null && Number.isNaN(t))) return toast.error("Exchange rate and target must be numbers.");
    start(async () => {
      try {
        const ed = await createEdition({
          title_id: titleId, year: Number(ey), name: name.trim(), edition_date: date || null,
          period_label: period.trim() || null, exchange_rate: r, target_gbp: t,
        });
        toast.success(`${ed.label} created`);
        setOpen(false);
        router.push(`/sales/editions/${ed.id}`);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Couldn't create the edition");
      }
    });
  }

  return (
    <>
      <Button size="sm" className="gap-1.5 font-semibold" onClick={() => setOpen(true)}>
        <Plus className="size-3.5" aria-hidden="true" /> New edition
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New edition</DialogTitle>
            <DialogDescription>An issue, a month of online sales, or an event - bookings are added to it once it exists.</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2 flex flex-col gap-1.5">
                <Label htmlFor="ne-title">Title</Label>
                <select id="ne-title" className={selectCls} value={titleId} onChange={(e) => setTitleId(e.target.value)}>
                  {titles.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="ne-year">Year</Label>
                <Input id="ne-year" inputMode="numeric" value={ey} onChange={(e) => setEy(e.target.value)} />
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="ne-name">Name</Label>
              <Input id="ne-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. 109, Jan 2027, Feb Asia" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center gap-1">
                  <Label htmlFor="ne-date">Publishes / takes place</Label>
                  <InfoHint>Drives &ldquo;Coming up&rdquo;, invoice chasing (bookings still uninvoiced a week after this date are flagged) and the comparison with last year.</InfoHint>
                </div>
                <Input id="ne-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="ne-period">Period label</Label>
                <Input id="ne-period" value={period} onChange={(e) => setPeriod(e.target.value)} placeholder="e.g. March/April/May" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="ne-rate">Exchange rate (US$ per £)</Label>
                <Input id="ne-rate" inputMode="decimal" value={rate} onChange={(e) => setRate(e.target.value)} placeholder="1.35" />
              </div>
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center gap-1">
                  <Label htmlFor="ne-target">Target (£)</Label>
                  <InfoHint>Optional - shows a progress bar on the edition page.</InfoHint>
                </div>
                <Input id="ne-target" inputMode="decimal" value={target} onChange={(e) => setTarget(e.target.value)} placeholder="Optional" />
              </div>
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={submit} disabled={pending || !name.trim() || !titleId}>
              {pending ? "Creating…" : "Create edition"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
