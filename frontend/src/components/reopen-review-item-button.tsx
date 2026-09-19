"use client";

import { useTransition } from "react";
import { RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { reopenReviewItem } from "@/lib/actions";

/** Puts a rejected item back into the pending queue - the audit/undo path
 * for "I dismissed a batch of these too fast and want a second look at
 * one." Only ever rendered for rejected items - see backend's
 * POST /api/review-queue/{id}/reopen for why an approved item can't be
 * reopened this way (it already made a real CRM write). */
export function ReopenReviewItemButton({ itemId }: { itemId: string }) {
  const [pending, startTransition] = useTransition();

  function reopen() {
    startTransition(async () => {
      try {
        await reopenReviewItem(itemId);
        toast.success("Back in the pending queue for another look");
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Couldn't reopen this item");
      }
    });
  }

  return (
    <Button size="sm" variant="outline" disabled={pending} onClick={reopen}>
      <RotateCcw className="size-3.5" />
      {pending ? "Reopening…" : "Reopen for review"}
    </Button>
  );
}
