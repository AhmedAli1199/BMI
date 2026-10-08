"use client";

import { useState, useTransition } from "react";
import { NotebookPen } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { updateEdition } from "@/lib/sales-actions";
import { friendlyError } from "@/lib/errors";

/** Free-text notes for a publication, event or project - anything worth
 * knowing when looking at its revenue (Matt, 8 Sep: "general notes on the
 * new SOR"). Saved on the edition, kept through a re-import. */
export function EditionNotes({ editionId, notes }: { editionId: string; notes: string | null }) {
  const [value, setValue] = useState(notes ?? "");
  const [saved, setSaved] = useState(notes ?? "");
  const [pending, start] = useTransition();
  const dirty = value !== saved;
  return (
    <section aria-labelledby="notes-heading" className="flex flex-col gap-2 rounded-xl border border-border/80 bg-card px-4 py-3 shadow-2xs">
      <h2 id="notes-heading" className="flex items-center gap-1.5 text-sm font-bold">
        <NotebookPen className="size-3.5 text-muted-foreground" aria-hidden="true" /> Notes
      </h2>
      <Textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        rows={value ? Math.min(8, value.split("\n").length + 1) : 2}
        placeholder="Anything useful about this edition - venue contracted, who's attending, deadlines, why it's up or down on last year…"
        className="text-sm"
        aria-label="Edition notes"
      />
      {dirty && (
        <div className="flex gap-2">
          <Button
            size="sm"
            disabled={pending}
            onClick={() =>
              start(async () => {
                try {
                  await updateEdition(editionId, { notes: value.trim() || null });
                  setSaved(value);
                  toast.success("Notes saved");
                } catch (e) {
                  toast.error(friendlyError(e, "Couldn't save the notes"));
                }
              })
            }
          >
            Save notes
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setValue(saved)}>Cancel</Button>
        </div>
      )}
    </section>
  );
}
