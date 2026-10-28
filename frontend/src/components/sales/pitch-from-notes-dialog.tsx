"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { pitchFromNotes } from "@/lib/proposals-actions";
import { friendlyError } from "@/lib/errors";

/** SALES-023: notes from a meeting that wasn't recorded (typed or pasted) become a proposal draft that answers what
 * the client said. Calls the notetaker recorded have their own "Make a pitch" button on the call's page. */
export function PitchFromNotesDialog({ companyId, companyName }: { companyId: string; companyName: string }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [notes, setNotes] = useState("");
  const [pending, start] = useTransition();

  function make() {
    start(async () => {
      try {
        const p = await pitchFromNotes({ company_id: companyId, notes: notes.trim() });
        toast.success("Pitch drafted - check it before sending");
        setOpen(false);
        router.push(`/sales/proposals/${p.id}`);
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't make a pitch from these notes"));
      }
    });
  }

  return (
    <>
      <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setOpen(true)}>
        <Sparkles className="size-3.5" />
        Pitch from notes
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Pitch from meeting notes</DialogTitle>
            <DialogDescription>
              Paste or type your notes from a meeting with {companyName}. The Brain drafts a proposal that answers what they said, in your style
              and the magazine&apos;s template, with prices from the rate card. Nothing is sent - you check it first.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="pitch-notes">Meeting notes</Label>
            <Textarea id="pitch-notes" rows={9} value={notes} onChange={(e) => setNotes(e.target.value)}
              placeholder="What they're trying to achieve, what they liked, which magazine and products came up, timing…" />
            <p className="text-xs text-muted-foreground">Anything personal or off the record is left out of the pitch.</p>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button className="gap-1.5" disabled={pending || notes.trim().length < 20} onClick={make}>
              {pending ? <Loader2 className="size-3.5 animate-spin" /> : <Sparkles className="size-3.5" />} Draft the pitch
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
