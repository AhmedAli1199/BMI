"use client";

import { useEffect } from "react";
import { celebrate } from "@/lib/celebrate";

/** Cheers once when the Review Queue goes from something waiting to nothing waiting while you work through it - not
 * every time you open an empty queue. Remembers the last count for this browser tab only. */
export function QueueClearWatcher({ pending }: { pending: number }) {
  useEffect(() => {
    let before: number | null = null;
    try { before = Number(sessionStorage.getItem("brain:queue-pending") ?? "NaN"); } catch { /* storage blocked */ }
    try { sessionStorage.setItem("brain:queue-pending", String(pending)); } catch { /* storage blocked */ }
    if (pending === 0 && before !== null && before > 0) celebrate("All clear - nothing waiting for you in the Review Queue.");
  }, [pending]);
  return null;
}
