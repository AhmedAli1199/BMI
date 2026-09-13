"use client";

import { useState, useTransition } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";

/** The Act! replacement for its "Add Note" screen - a plain text note
 * attached to a contact or company. Kept deliberately simple (no rich text,
 * no attachments, no sharing to other records) to match what Act! notes
 * actually are once you strip the RTF/HTML formatting out: a timestamped
 * block of text. */
export function AddNoteDialog({
  id,
  action,
}: {
  id: string;
  /** A bare server action reference (e.g. addContactNote) - never wrap it
   * in an arrow function here, same rule as DeleteEntityButton. */
  action: (id: string, body: string) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState("");
  const [pending, startTransition] = useTransition();

  function save() {
    if (!body.trim()) return;
    startTransition(async () => {
      try {
        await action(id, body.trim());
        setBody("");
        setOpen(false);
        toast.success("Note added");
      } catch {
        toast.error("Couldn't add note");
      }
    });
  }

  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <Plus className="size-4" />
        Add note
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add note</DialogTitle>
          </DialogHeader>
          <Textarea
            autoFocus
            rows={6}
            placeholder="Type a note…"
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={save} disabled={pending || !body.trim()}>
              {pending ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
