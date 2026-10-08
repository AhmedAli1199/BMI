"use client";

import { useEffect, useState, useTransition } from "react";
import { toast } from "sonner";
import type { BookingNewBusiness } from "@/lib/commission-types";
import { decideNewBusiness, getBookingNewBusiness } from "@/lib/commission-actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NewBusinessPill } from "@/components/commission/commission-ui";

/** On a booking's edit panel: is it new business for commission, why, and (for managers) a way to decide it. */
export function BookingNewBusinessRow({ orderId }: { orderId: string }) {
  const [nb, setNb] = useState<BookingNewBusiness | null>(null);
  const [editing, setEditing] = useState(false);
  const [reason, setReason] = useState("");
  const [pending, start] = useTransition();

  useEffect(() => {
    let live = true;
    getBookingNewBusiness(orderId).then((r) => live && setNb(r)).catch(() => undefined);
    return () => { live = false; };
  }, [orderId]);

  if (!nb) return null;
  const save = (decision: "new" | "returning" | null) => start(async () => {
    try { setNb(await decideNewBusiness(orderId, decision, reason.trim() || undefined)); setEditing(false); setReason(""); toast.success("Saved"); }
    catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't save"); }
  });

  return (
    <div className="rounded-lg border border-border/70 bg-muted/20 px-3 py-2 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-muted-foreground">For commission</span>
        <NewBusinessPill status={nb.status} manager={nb.decided_by === "manager"} />
        {nb.can_decide && !editing && (
          nb.decided_by === "manager"
            ? <button type="button" className="ml-auto font-semibold text-primary hover:underline" disabled={pending} onClick={() => save(null)}>Undo decision</button>
            : <button type="button" className="ml-auto font-semibold text-primary hover:underline" onClick={() => setEditing(true)}>Change</button>
        )}
      </div>
      <p className="mt-1 text-muted-foreground">{nb.reason}</p>
      {editing && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why" className="h-7 min-w-40 flex-1 text-xs" aria-label="Why" />
          <Button type="button" size="xs" variant="outline" disabled={pending || !reason.trim()} onClick={() => save("new")}>New business</Button>
          <Button type="button" size="xs" variant="outline" disabled={pending || !reason.trim()} onClick={() => save("returning")}>Returning customer</Button>
          <Button type="button" size="xs" variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
        </div>
      )}
    </div>
  );
}
