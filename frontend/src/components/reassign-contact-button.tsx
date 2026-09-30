"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { UserRoundX } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EntityPicker } from "@/components/entity-picker";
import { reassignContact, searchContacts } from "@/lib/actions";

/** "Mark as departed / move notes to another contact" - a manual action
 * for exactly the case BMI described: a rep already knows a contact left
 * a company and already knows who replaced them, and just wants an easy
 * way to move that person's history over rather than losing it or
 * scanning back through it by hand later split across two records.
 *
 * Deliberately NOT routed through the (unbuilt) CS-003 departure-
 * detection automation - see app/services/contact_transfer.py's docstring
 * for why the actual move logic is a standalone shared function instead.
 */
export function ReassignContactButton({ contactId, contactName }: { contactId: string; contactName: string }) {
  const [open, setOpen] = useState(false);
  const [successor, setSuccessor] = useState<{ id: string; label: string } | null>(null);
  const [pending, startTransition] = useTransition();
  const router = useRouter();

  function confirm() {
    if (!successor) return;
    startTransition(async () => {
      try {
        await reassignContact(contactId, successor.id);
        toast.success(`Moved ${contactName}'s notes and history to ${successor.label}`);
        setOpen(false);
        setSuccessor(null);
        router.push(`/contacts/${successor.id}`);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Couldn't move those records - try again");
      }
    });
  }

  return (
    <>
      <Button
        size="sm"
        variant="outline"
        onClick={() => setOpen(true)}
        className="h-7 text-xs gap-1.5 cursor-pointer font-medium hover:border-destructive/50 hover:text-destructive"
      >
        <UserRoundX className="size-3" />
        <span>Mark as departed</span>
      </Button>

      <Dialog open={open} onOpenChange={(next) => !pending && setOpen(next)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Move {contactName}&apos;s notes to a successor</DialogTitle>
            <DialogDescription>
              Every note and history entry on this record moves to whoever you pick below - this record itself
              stays, but its history won&apos;t be here anymore. Both records get a short note explaining the
              handover.
            </DialogDescription>
          </DialogHeader>

          <EntityPicker
            label="contact"
            placeholder="Search for who replaced them…"
            search={async (q) => (await searchContacts(q)).filter((c) => c.id !== contactId).map((c) => ({ id: c.id, label: c.full_name || "(no name)", sublabel: c.company_name }))}
            value={successor}
            onChange={setSuccessor}
            viewHref={(id) => `/contacts/${id}`}
          />

          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button variant="destructive" onClick={confirm} disabled={!successor || pending}>
              {pending ? "Moving…" : "Move notes and history"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
