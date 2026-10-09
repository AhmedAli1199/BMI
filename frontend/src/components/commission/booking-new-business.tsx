"use client";

import { useEffect, useState, useTransition } from "react";
import { toast } from "sonner";
import type { BookingNewBusiness } from "@/lib/commission-types";
import { decideNewBusiness, getBookingNewBusiness } from "@/lib/commission-actions";
import { InfoHint } from "@/components/sales/info-hint";
import { NewBusinessPill } from "@/components/commission/commission-ui";
import { friendlyError } from "@/lib/errors";

/** On a booking's edit panel: the "New business" tick box for commission. The salesperson ticks it themselves
 *  (a manager checks the ticks each month); until someone ticks it, the system's suggestion from the last 24 months is shown. */
export function BookingNewBusinessRow({ orderId }: { orderId: string }) {
  const [nb, setNb] = useState<BookingNewBusiness | null>(null);
  const [pending, start] = useTransition();

  useEffect(() => {
    let live = true;
    getBookingNewBusiness(orderId).then((r) => live && setNb(r)).catch(() => undefined);
    return () => { live = false; };
  }, [orderId]);

  if (!nb) return null;
  const decided = nb.decided_by !== "history";
  const save = (decision: "new" | "returning" | null) => start(async () => {
    try {
      setNb(await decideNewBusiness(orderId, decision));
      toast.success(decision === null ? "Back to the suggestion" : decision === "new" ? "Ticked as new business" : "Not new business");
    } catch (e) { toast.error(friendlyError(e, "Couldn't save that")); }
  });

  return (
    <div className="rounded-lg border border-border/70 bg-muted/20 px-3 py-2 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        {nb.can_decide ? (
          <label className="flex items-center gap-2 text-sm font-semibold">
            <input type="checkbox" className="size-4" checked={nb.status === "new"} disabled={pending}
              onChange={(e) => save(e.target.checked ? "new" : "returning")} />
            New business
          </label>
        ) : (
          <span className="font-semibold text-muted-foreground">For commission</span>
        )}
        <InfoHint>Tick this if the client hasn&apos;t spent with BMI in the last 24 months. Everything on their first invoice counts. A manager checks the ticks each month.</InfoHint>
        <NewBusinessPill status={nb.status} by={nb.decided_by} />
        {nb.can_decide && decided && (
          <button type="button" className="ml-auto font-semibold text-primary hover:underline" disabled={pending} onClick={() => save(null)}>Use the suggestion</button>
        )}
      </div>
      <p className="mt-1 text-muted-foreground">{decided ? nb.reason : `Suggestion: ${nb.reason}`}</p>
    </div>
  );
}
