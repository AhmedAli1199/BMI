"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Trash2 } from "lucide-react";
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
import { toast } from "sonner";

export function DeleteEntityButton({
  entityLabel,
  id,
  action,
  redirectTo,
  description,
}: {
  /** Shown in the confirmation copy, e.g. "Jane Doe" or "this company". */
  entityLabel: string;
  id: string;
  /** A server action reference (e.g. deleteContact from lib/actions) - must
   * be passed as-is, never wrapped in a new arrow function here or at the
   * call site, or Next.js loses track of it being a server action at all. */
  action: (id: string) => Promise<void>;
  /** Where to send the user after a successful delete - omit to just refresh in place (list pages). */
  redirectTo?: string;
  /** Override the default "addresses, phones, emails" copy below, which
   * describes what a contact/company delete actually cascades into - a
   * group (its only other caller) owns none of those, so it needs its
   * own accurate wording instead of this generic one. */
  description?: string;
}) {
  const [open, setOpen] = useState(false);
  const [pending, startTransition] = useTransition();
  const router = useRouter();

  function confirmDelete() {
    startTransition(async () => {
      try {
        await action(id);
        setOpen(false);
        toast.success(`${entityLabel} deleted`);
        if (redirectTo) {
          // A full navigation, not router.push: Next's client router cache
          // kept handing back a snapshot of the destination list page taken
          // before the delete completed, even with router.refresh() chained
          // after it (verified against a real delete during testing) - a
          // real document load is the only thing that reliably sees the
          // post-delete state here.
          window.location.assign(redirectTo);
        } else {
          router.refresh();
        }
      } catch {
        toast.error(`Couldn't delete ${entityLabel}`);
      }
    });
  }

  return (
    <>
      <Button variant="outline" size="sm" className="text-destructive hover:text-destructive" onClick={() => setOpen(true)}>
        <Trash2 className="size-4" />
        Delete
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete {entityLabel}?</DialogTitle>
          <DialogDescription>
            {description ??
              "This can't be undone. Linked records (addresses, phones, emails, group memberships) are removed too; anything else that only references it is unlinked, not deleted."}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
          <Button variant="destructive" onClick={confirmDelete} disabled={pending}>
            {pending ? "Deleting…" : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
      </Dialog>
    </>
  );
}
