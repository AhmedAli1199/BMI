"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Download } from "lucide-react";
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
import { loadActTemplates } from "@/lib/messaging-actions";
import { friendlyError } from "@/lib/errors";

/** Administrators and data managers: bring in the sales templates Clare sent from Act!. Safe to press again -
 * a template that's already in the library is never added twice. */
export function LoadActTemplatesButton() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [pending, start] = useTransition();

  function load() {
    start(async () => {
      try {
        const { added } = await loadActTemplates();
        setOpen(false);
        toast.success(
          added === 0
            ? "They're already all in the library - nothing new to add."
            : `Added ${added} ${added === 1 ? "template" : "templates"}. Each is marked "needs a check" until someone reads it through.`
        );
        router.refresh();
      } catch (e) {
        toast.error(friendlyError(e, "We couldn't load the templates. Please try again."));
      }
    });
  }

  return (
    <>
      <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setOpen(true)}>
        <Download className="size-3.5" />
        Load Clare&apos;s Act! templates
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Load Clare&apos;s Act! templates?</DialogTitle>
            <DialogDescription>
              This adds the Selling Travel sales emails Clare sent us from Act! to the library, shared with the team.
              Each one is marked &quot;needs a check&quot; so someone reads it before it&apos;s used. Templates that are
              already here are skipped, so nothing is added twice and nothing is changed. It also fills in any blank
              Selling Travel figures (such as the print run) in the editorial plan.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Not now</DialogClose>
            <Button onClick={load} disabled={pending}>
              {pending ? "Loading…" : "Yes - load the templates"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
