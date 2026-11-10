"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { addContactNote } from "@/lib/actions";
import { friendlyError } from "@/lib/errors";

/** "Add note" right on a contact's Notes tab: type it, save it, it's at the top of the list with today's date. */
export function AddNoteInline({ contactId }: { contactId: string }) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [pending, start] = useTransition();
  const router = useRouter();

  function save() {
    if (!text.trim()) return;
    start(async () => {
      try {
        await addContactNote(contactId, text.trim());
        setText("");
        setOpen(false);
        toast.success("Note added");
        router.refresh();
      } catch (e) {
        toast.error(friendlyError(e, "We couldn't save the note. Please try again."));
      }
    });
  }

  if (!open) {
    return (
      <Button size="sm" className="w-fit gap-1.5" onClick={() => setOpen(true)}>
        <Plus className="size-4" /> Add note
      </Button>
    );
  }
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border bg-card p-3">
      <Textarea
        autoFocus
        rows={3}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) save();
        }}
        placeholder="What do you want to remember about this contact?"
        aria-label="Note text"
        className="text-sm"
      />
      <div className="flex items-center gap-2">
        <Button size="sm" onClick={save} disabled={pending || !text.trim()}>
          Save note
        </Button>
        <Button size="sm" variant="ghost" onClick={() => { setOpen(false); setText(""); }}>
          Cancel
        </Button>
        <span className="ml-auto text-[11px] text-muted-foreground">Saved with today&apos;s date and your name.</span>
      </div>
    </div>
  );
}
