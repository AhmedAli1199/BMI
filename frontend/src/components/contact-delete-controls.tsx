"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DeleteEntityButton } from "@/components/delete-entity-button";
import { deleteContact, requestContactDeletion } from "@/lib/actions";
import { friendlyError } from "@/lib/errors";

/** Deleting a contact completely (Craig, feedback #8). Administrators and data managers delete it, after a
 * confirmation that says exactly what goes with it. Everyone else can ask one of them to, with a reason. */
export function ContactDeleteControls({ contactId, name, canDelete }: { contactId: string; name: string; canDelete: boolean }) {
  if (canDelete) {
    return (
      <DeleteEntityButton
        entityLabel={name}
        id={contactId}
        action={deleteContact}
        redirectTo="/contacts"
        className="h-7 gap-1.5 text-xs font-medium"
        description={`This removes ${name} from BMI Brain for good, with their email addresses, phone numbers, addresses, notes, history and group memberships. Their bookings, activities and deals are kept, just no longer linked to them. This can't be undone. If they've only left their company, use "Mark as departed" instead.`}
      />
    );
  }
  return <AskToDelete contactId={contactId} name={name} />;
}

function AskToDelete({ contactId, name }: { contactId: string; name: string }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [pending, start] = useTransition();
  const router = useRouter();

  function send() {
    start(async () => {
      try {
        const { told } = await requestContactDeletion(contactId, reason);
        setOpen(false);
        setReason("");
        toast.success(told ? "Asked - an administrator will delete it." : "Asked - it's noted on the contact for an administrator.");
        router.refresh();
      } catch (e) {
        toast.error(friendlyError(e, "We couldn't send the request. Please try again."));
      }
    });
  }

  return (
    <>
      <Button size="sm" variant="outline" className="h-7 gap-1.5 text-xs font-medium" onClick={() => setOpen(true)}>
        <Trash2 className="size-3 text-muted-foreground" /> Ask to delete
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Ask to delete {name}</DialogTitle>
            <DialogDescription>
              Deleting a contact can&apos;t be undone, so an administrator or data manager does it. They&apos;ll get a
              message with a link to this contact. If the person has only left their company, use &ldquo;Mark as
              departed&rdquo; instead.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Why should it go? e.g. a duplicate of another record, or a test entry"
            aria-label="Reason"
            className="text-sm"
          />
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={send} disabled={pending}>{pending ? "Sending…" : "Send request"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
