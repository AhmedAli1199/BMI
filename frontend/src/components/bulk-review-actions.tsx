"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Layers } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { ReviewAction, ReviewKind } from "@/lib/types";
import { bulkResolveReviewItems } from "@/lib/actions";

/** Only an action with no per-item input can be applied in bulk - the
 * backend enforces this too (see review_queue.py's bulk_resolve_review_items),
 * this just keeps the menu from offering something that would immediately
 * 400. A note-requiring action is still offered: the same note (if any) is
 * applied to every item, same as a single-item resolve already allows. */
function isBulkable(action: ReviewAction): boolean {
  if (action.requires_contact_picker || action.requires_related_entity_choice) return false;
  if (action.extra_fields.some((f) => f.required && f.field_type !== "bool")) return false;
  return true;
}

/** "Approve all" / "Dismiss all" for whatever the review queue is currently
 * filtered to - always scoped to one kind and the pending status (the only
 * status with anything left to act on), so it respects the same kind
 * filter chip the reviewer already picked. Hidden entirely when no kind is
 * selected ("All"), since bulk actions are defined per kind and there's no
 * single action that would mean the same thing across every automation at
 * once - the reviewer picks a kind chip first, same as the single-item
 * flow already requires implicitly (each ReviewItemCard only offers that
 * item's own kind's actions). */
export function BulkReviewActions({ kind, pendingCount }: { kind: ReviewKind; pendingCount: number }) {
  const [pending, startTransition] = useTransition();
  const [open, setOpen] = useState(false);
  const router = useRouter();

  const bulkableActions = kind.actions.filter(isBulkable);
  if (bulkableActions.length === 0 || pendingCount === 0) return null;

  function run(action: ReviewAction) {
    if (action.requires_note) {
      const note = window.prompt(`"${action.label}" requires a note, applied to every item:`);
      if (note === null) return; // cancelled
      if (!note.trim()) {
        toast.error("A note is required for this action.");
        return;
      }
      fire(action, note.trim());
      return;
    }
    if (!window.confirm(`${action.label} all ${pendingCount} pending "${kind.label}" item${pendingCount === 1 ? "" : "s"}? This can't be undone in bulk.`)) {
      return;
    }
    fire(action);
  }

  function fire(action: ReviewAction, note?: string) {
    setOpen(false);
    startTransition(async () => {
      try {
        const result = await bulkResolveReviewItems(kind.kind, action.id, note);
        if (result.failed > 0) {
          toast.warning(`${action.label}: ${result.succeeded} done, ${result.failed} failed`, {
            description: result.errors.slice(0, 3).join("; ") || undefined,
          });
        } else {
          toast.success(`${action.label} - applied to ${result.succeeded} item${result.succeeded === 1 ? "" : "s"}`);
        }
        router.refresh();
      } catch (e) {
        toast.error(e instanceof Error ? e.message : `Couldn't apply "${action.label}" in bulk`);
      }
    });
  }

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger
        render={
          <Button size="sm" variant="outline" disabled={pending} className="gap-1.5 text-xs font-semibold">
            <Layers className="size-3.5" />
            {pending ? "Applying…" : `Bulk action (${pendingCount})`}
          </Button>
        }
      />
      <DropdownMenuContent align="end">
        {bulkableActions.map((action) => (
          <DropdownMenuItem
            key={action.id}
            onClick={() => run(action)}
            className={action.style === "destructive" ? "text-destructive focus:text-destructive" : ""}
          >
            {action.label} all ({pendingCount})
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
