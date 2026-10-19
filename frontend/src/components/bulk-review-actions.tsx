"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Layers } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { ReviewAction, ReviewKind } from "@/lib/types";
import { bulkResolveReviewItems } from "@/lib/actions";
import { fmtCount } from "@/lib/automation-format";
import { friendlyError } from "@/lib/errors";

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

/** The server does at most this many rounds of 500 cards before we stop and say what's left. */
const MAX_ROUNDS = 40;

/** "Approve all" / "Dismiss all" for whatever the review queue is currently
 * filtered to - always one kind, the pending status, and the same filters,
 * search and Queue Insights group the list is showing. Hidden when no kind is
 * selected, since each kind has its own buttons. Every choice opens a dialog
 * that says how many cards it will change and asks to confirm (and for the
 * note, when the button needs one). Big selections are done in rounds of 500
 * on the server, with progress shown here. */
export function BulkReviewActions({
  kind,
  pendingCount,
  filters,
}: {
  kind: ReviewKind;
  pendingCount: number;
  /** What the list is filtered by right now - bulk actions only touch those items. */
  filters?: { facets?: string[]; q?: string; bucket?: string };
}) {
  const [pending, startTransition] = useTransition();
  const [chosen, setChosen] = useState<ReviewAction | null>(null);
  const [note, setNote] = useState("");
  const [progress, setProgress] = useState<number | null>(null);
  const router = useRouter();

  const bulkableActions = kind.actions.filter(isBulkable);
  if (bulkableActions.length === 0 || pendingCount === 0) return null;

  const cards = `${fmtCount(pendingCount)} card${pendingCount === 1 ? "" : "s"}`;
  const noteMissing = Boolean(chosen?.requires_note) && !note.trim();

  function open(action: ReviewAction) {
    setNote("");
    setProgress(null);
    setChosen(action);
  }

  function run() {
    const action = chosen;
    if (!action || noteMissing) return;
    startTransition(async () => {
      let succeeded = 0;
      let failed = 0;
      let remaining = 0;
      const errors: string[] = [];
      try {
        for (let round = 0; round < MAX_ROUNDS; round++) {
          const result = await bulkResolveReviewItems(kind.kind, action.id, note.trim() || undefined, { ...filters, offset: failed });
          succeeded += result.succeeded;
          failed += result.failed;
          remaining = result.remaining;
          errors.push(...result.errors);
          setProgress(succeeded + failed);
          if (remaining === 0 || result.succeeded + result.failed === 0) break;
        }
      } catch (e) {
        toast.error(friendlyError(e, `Couldn't finish "${action.label}" for every card. Refresh the page to see what's left.`));
        setChosen(null);
        router.refresh();
        return;
      }
      setChosen(null);
      if (failed > 0) {
        toast.warning(`${action.label}: ${fmtCount(succeeded)} done, ${fmtCount(failed)} couldn't be done`, {
          description: errors.slice(0, 3).join(" ") || undefined,
        });
      } else {
        toast.success(`${action.label}: done for ${fmtCount(succeeded)} card${succeeded === 1 ? "" : "s"}`);
      }
      if (remaining > 0) {
        toast.info(`${fmtCount(remaining)} more cards are still waiting. Run it again to do the rest.`);
      }
      router.refresh();
    });
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <Button size="sm" variant="outline" disabled={pending} className="gap-1.5 text-xs font-semibold">
              <Layers className="size-3.5" />
              {pending ? "Applying…" : `Bulk action (${fmtCount(pendingCount)})`}
            </Button>
          }
        />
        <DropdownMenuContent align="end">
          {bulkableActions.map((action) => (
            <DropdownMenuItem
              key={action.id}
              onClick={() => open(action)}
              className={action.style === "destructive" ? "text-destructive focus:text-destructive" : ""}
            >
              {action.label} all ({fmtCount(pendingCount)})
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={chosen !== null} onOpenChange={(o) => !o && !pending && setChosen(null)}>
        <DialogContent className="sm:max-w-md" showCloseButton={!pending}>
          <DialogHeader>
            <DialogTitle>
              {chosen?.label} for {cards}?
            </DialogTitle>
            <DialogDescription>
              This presses &ldquo;{chosen?.label}&rdquo; on every waiting &ldquo;{kind.label}&rdquo; card that matches what the list is
              showing now ({cards}). You can&apos;t undo this in bulk.
            </DialogDescription>
          </DialogHeader>
          {pendingCount > 500 && (
            <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
              <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-[var(--warn)]" aria-hidden="true" />
              That&apos;s a lot of cards, so they&apos;re done 500 at a time. Keep this window open until it finishes.
            </p>
          )}
          {chosen?.requires_note && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="bulk-note">Note (added to every card)</Label>
              <Textarea
                id="bulk-note"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Why, or any context worth keeping on the record…"
                disabled={pending}
              />
            </div>
          )}
          {pending && progress !== null && (
            <p className="text-xs text-muted-foreground" role="status">
              Done {fmtCount(progress)} of {fmtCount(pendingCount)}…
            </p>
          )}
          <DialogFooter>
            <DialogClose render={<Button variant="ghost" disabled={pending} />}>Cancel</DialogClose>
            <Button
              onClick={run}
              disabled={pending || noteMissing}
              variant={chosen?.style === "destructive" ? "destructive" : "default"}
            >
              {pending ? "Applying…" : `Confirm - ${chosen?.label ?? ""} (${fmtCount(pendingCount)})`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
