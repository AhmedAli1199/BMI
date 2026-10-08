"use client";

import { useEffect, useState, useTransition } from "react";
import { History, Undo2 } from "lucide-react";
import { toast } from "sonner";
import type { RateHistoryRow } from "@/lib/rate-card-types";
import { getRateHistory, putBackChange } from "@/lib/rate-card-actions";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { friendlyError } from "@/lib/errors";

function show(field: string, v: string | null): string {
  if (v === null || v === "None" || v === "") return "(empty)";
  if (field === "price" && !Number.isNaN(Number(v))) return `£${Number(v).toLocaleString("en-GB")}`;
  if (field === "removed") return v === "True" ? "removed" : "on the rate card";
  if (field === "how it's priced") return ({ fixed: "a set price", from: "starts from", poa: "price on request" } as Record<string, string>)[v] ?? v;
  return v;
}

/** Every change to this brand's prices: who, when, what it was before - and a way to put it back. */
export function HistorySheet({ brand, year, onChanged }: { brand: string; year: number; onChanged: () => void }) {
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<RateHistoryRow[] | null>(null);
  const [pending, start] = useTransition();

  useEffect(() => {
    if (!open) return;
    let alive = true;
    getRateHistory(brand, year).then((r) => alive && setRows(r)).catch(() => alive && setRows([]));
    return () => { alive = false; };
  }, [open, brand, year]);

  function putBack(r: RateHistoryRow) {
    start(async () => {
      try {
        await putBackChange(r.id);
        toast.success(`Put back: ${r.what}`);
        setRows(await getRateHistory(brand, year));
        onChanged();
      } catch (e) { toast.error(friendlyError(e, "Couldn't put it back")); }
    });
  }

  return (
    <>
      <Button size="sm" variant="outline" className="gap-1.5" onClick={() => { setRows(null); setOpen(true); }}><History className="size-3.5" /> Changes</Button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-full gap-0 p-0 sm:max-w-lg">
          <SheetHeader className="border-b border-border/70 px-5 py-4">
            <SheetTitle className="text-base font-bold">Changes to these prices</SheetTitle>
            <SheetDescription className="text-xs">Newest first. “Put back” undoes one change, as long as nobody has changed it again since.</SheetDescription>
          </SheetHeader>
          <div className="flex-1 overflow-y-auto">
            {rows === null ? <p className="p-5 text-sm text-muted-foreground">Loading…</p> : rows.length === 0 ? <p className="p-5 text-sm text-muted-foreground">No changes yet.</p> : (
              <ul className="divide-y divide-border/60">
                {rows.map((r) => (
                  <li key={r.id} className="flex items-start gap-3 px-5 py-3 text-sm">
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold">{r.what}</p>
                      <p className="text-xs">
                        {r.field === "added" ? <>Added at {r.new_value}</> : r.field === "deleted" ? <>Deleted</> : (
                          <><span className="text-muted-foreground">{r.field}:</span> {show(r.field, r.old_value)} → <strong>{show(r.field, r.new_value)}</strong></>
                        )}
                      </p>
                      <p className="text-[11px] text-muted-foreground">{r.by ?? "Someone"} · {new Date(r.at).toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}</p>
                    </div>
                    {r.can_put_back && <Button size="xs" variant="outline" disabled={pending} onClick={() => putBack(r)} className="gap-1"><Undo2 className="size-3" /> Put back</Button>}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
