"use client";

import { useTransition } from "react";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";

/** Small icon-only delete affordance shared by every note/history/activity
 * row across the app (act-tab-workstation.tsx, the company Notes tab,
 * unified-activity-timeline.tsx) - one confirm-then-call-then-toast
 * pattern instead of each list reimplementing it slightly differently.
 * Hard delete, no undo - see delete_entity_row's docstring in the backend
 * for why there's no separate restore flow (matches every other record
 * type in this app). stopPropagation so this can sit inside a clickable
 * row/card without also triggering the row's own click handler. */
export function DeleteItemButton({
  onDelete,
  label = "Delete",
  confirmMessage = "Delete this? This can't be undone.",
  className = "",
}: {
  onDelete: () => Promise<void>;
  label?: string;
  confirmMessage?: string;
  className?: string;
}) {
  const [pending, startTransition] = useTransition();

  function handleClick(e: React.MouseEvent) {
    e.stopPropagation();
    e.preventDefault();
    if (!window.confirm(confirmMessage)) return;
    startTransition(async () => {
      try {
        await onDelete();
        toast.success("Deleted");
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Couldn't delete");
      }
    });
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={pending}
      title={label}
      aria-label={label}
      className={`inline-flex shrink-0 items-center justify-center rounded-md p-1 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive disabled:pointer-events-none disabled:opacity-50 ${className}`}
    >
      <Trash2 className="size-3.5" />
    </button>
  );
}
