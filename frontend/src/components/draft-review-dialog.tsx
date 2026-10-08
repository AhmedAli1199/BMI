"use client";

import { useState, useTransition } from "react";
import { Sparkles, Wand2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { redraftReviewItem, resolveReviewItem } from "@/lib/actions";
import { useTypewriterReveal } from "@/lib/use-typewriter-reveal";
import { friendlyError } from "@/lib/errors";

/**
 * The full preview/edit/regenerate step for a kind whose "Draft follow-up"
 * / "Mark sent" action writes an AI-drafted note or email (signal_trigger,
 * followup_due - see registry.py's optional ReviewKind.redraft). Replaces
 * the old one-click "approve immediately" flow: nothing is written to the
 * contact's record until the reviewer explicitly hits Approve here, so
 * there's always a real look-before-you-commit step, an editable text
 * box, and a way to ask for a revision without losing the item from the
 * queue if they change their mind.
 *
 * Closing the dialog any other way (the X, clicking outside, Cancel) is a
 * pure no-op - nothing was called, the item is exactly as pending as it
 * was before the dialog opened.
 */
export function DraftReviewDialog({
  open,
  onOpenChange,
  itemId,
  actionId,
  actionLabel,
  initialDraft,
  send,
  onApproved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  itemId: string;
  actionId: string;
  actionLabel: string;
  initialDraft: string;
  /** For a draft that can be emailed from the reviewer's own Outlook: the
   * main button sends to `to` (editable, pre-filled), and a second button
   * just logs it to the CRM instead. */
  send?: { defaultTo: string; logOnlyActionId: string; logOnlyLabel: string };
  /** Called right after a successful approve, so the parent card can play
   * its own "done, folding away" animation - this dialog doesn't own that
   * transition, it just closes itself. */
  onApproved: (label: string) => void;
}) {
  const { text: draft, setText: setDraft, reveal: revealDraft } = useTypewriterReveal(initialDraft);
  const [instructions, setInstructions] = useState("");
  const [regenerating, startRegenerate] = useTransition();
  const [approving, startApprove] = useTransition();
  const [to, setTo] = useState(send?.defaultTo ?? "");

  function handleRegenerate() {
    if (!instructions.trim()) return;
    startRegenerate(async () => {
      try {
        const newDraft = await redraftReviewItem(itemId, instructions.trim());
        revealDraft(newDraft);
        setInstructions("");
        toast.success("Draft updated");
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't regenerate the draft"));
      }
    });
  }

  function handleApprove(which: "main" | "log" = "main") {
    if (!draft.trim()) {
      toast.error("The draft is empty - write something or regenerate before approving.");
      return;
    }
    if (send && which === "main" && !/^[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+$/.test(to.trim())) {
      toast.error("Enter the email address to send this to.");
      return;
    }
    const id = send && which === "log" ? send.logOnlyActionId : actionId;
    const label = send && which === "log" ? send.logOnlyLabel : actionLabel;
    startApprove(async () => {
      try {
        await resolveReviewItem(itemId, id, { note: draft, fields: send && which === "main" ? { to: to.trim() } : undefined });
        onOpenChange(false);
        onApproved(send && which === "main" ? `Sent to ${to.trim()}` : label);
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't save this draft"));
      }
    });
  }

  const busy = regenerating || approving;

  return (
    <Dialog open={open} onOpenChange={(next) => !busy && onOpenChange(next)}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="size-4 text-primary" />
            Review the draft
          </DialogTitle>
          <DialogDescription>
            {send
              ? "Edit it, ask for a revision, then send it from your own Outlook - it lands in your Sent Items, replies come back to you, and a copy is logged on the company. Or just log it and send it yourself."
              : "Edit it directly, ask for a revision, or approve as-is. Approving saves it as a note on the contact's record — copy it into your own email or phone call to actually send it."}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          {send && (
            <div>
              <Label htmlFor="draft-to" className="mb-1 block text-xs text-muted-foreground">
                Send to
              </Label>
              <Input
                id="draft-to"
                type="email"
                value={to}
                onChange={(e) => setTo(e.target.value)}
                placeholder="name@company.com"
                disabled={busy}
              />
              {!send.defaultTo && (
                <p className="mt-1 text-[11px] text-muted-foreground">
                  No contact with an email is linked to this company yet - type the address.
                </p>
              )}
            </div>
          )}
          <div className="relative">
            <Textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              readOnly={regenerating}
              rows={7}
              className={`resize-none text-sm transition-opacity duration-150 ${regenerating ? "opacity-40" : "opacity-100"}`}
              placeholder="No draft text yet."
            />
            {regenerating && (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                <span className="flex items-center gap-1.5 rounded-full bg-background/90 px-3 py-1.5 text-xs font-semibold text-muted-foreground shadow-sm ring-1 ring-border">
                  <Wand2 className="size-3.5 animate-pulse" />
                  Rewriting…
                </span>
              </div>
            )}
          </div>

          <div className="flex items-end gap-2">
            <div className="flex-1">
              <Label htmlFor="redraft-instructions" className="mb-1 block text-xs text-muted-foreground">
                Ask for a revision (optional)
              </Label>
              <Input
                id="redraft-instructions"
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="e.g. make it shorter, mention the renewal date"
                disabled={busy}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleRegenerate();
                  }
                }}
              />
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={busy || !instructions.trim()}
              onClick={handleRegenerate}
            >
              {regenerating ? "Rewriting…" : "Regenerate"}
            </Button>
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" disabled={busy} onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          {send && (
            <Button type="button" variant="outline" disabled={busy} onClick={() => handleApprove("log")}>
              {send.logOnlyLabel}
            </Button>
          )}
          <Button type="button" disabled={busy} onClick={() => handleApprove("main")}>
            {approving ? (send ? "Sending…" : "Saving…") : actionLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
