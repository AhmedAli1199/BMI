"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Lock, LockOpen } from "lucide-react";
import { updateEdition } from "@/lib/sales-actions";
import { Button } from "@/components/ui/button";

/** Close an edition once it's done selling (it stops appearing in
 * "Coming up"), or reopen it. Nothing is deleted or locked for editing -
 * late invoices still get recorded against a closed edition. */
export function EditionStatusButton({ editionId, status }: { editionId: string; status: "open" | "closed" }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const closing = status === "open";
  return (
    <Button
      size="sm"
      variant="outline"
      className="gap-1.5 font-semibold"
      disabled={pending}
      title={closing ? "Mark as finished selling - invoices can still be recorded" : "Reopen for bookings"}
      onClick={() =>
        start(async () => {
          try {
            await updateEdition(editionId, { status: closing ? "closed" : "open" });
            toast.success(closing ? "Edition closed" : "Edition reopened");
            router.refresh();
          } catch (e) {
            toast.error(e instanceof Error ? e.message : "Couldn't update the edition");
          }
        })
      }
    >
      {closing ? <Lock className="size-3.5" aria-hidden="true" /> : <LockOpen className="size-3.5" aria-hidden="true" />}
      {closing ? "Close edition" : "Reopen"}
    </Button>
  );
}
