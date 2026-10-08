"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Globe } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { updateEdition } from "@/lib/sales-actions";
import { friendlyError } from "@/lib/errors";

/** Where this edition can be read online. Next year's renewal emails link
 * advertisers to it (when the title's link pattern can't point at their
 * exact page). */
export function EditionLinkButton({ editionId, url }: { editionId: string; url: string | null }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState(url ?? "");
  const [pending, start] = useTransition();
  return (
    <>
      <Button size="sm" variant="outline" className="gap-1.5 font-semibold" onClick={() => setOpen(true)} title={url ?? "No online link yet"}>
        <Globe className="size-3.5" aria-hidden="true" /> {url ? "Online link" : "Add online link"}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Online edition link</DialogTitle>
            <DialogDescription>
              Where this issue can be read online (the digital edition). Renewal emails next year link advertisers back
              to it, so they can see their ad again.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ed-url">Link</Label>
            <Input id="ed-url" type="url" value={value} onChange={(e) => setValue(e.target.value)} placeholder="https://…" />
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button
              disabled={pending}
              onClick={() =>
                start(async () => {
                  try {
                    await updateEdition(editionId, { digital_url: value.trim() || null });
                    toast.success("Link saved");
                    setOpen(false);
                    router.refresh();
                  } catch (e) {
                    toast.error(friendlyError(e, "Couldn't save the link"));
                  }
                })
              }
            >
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
