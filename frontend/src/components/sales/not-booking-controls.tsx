"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Ban, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { markInvoiceNotBooking, putBackInvoice } from "@/lib/sales-actions";
import { friendlyError } from "@/lib/errors";

/** "This invoice isn't for a booking" (a cost share, a refund...), with an optional note for whoever looks later. */
export function NotBookingButton({ invoiceId, number }: { invoiceId: string; number: string | null }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");
  const [pending, start] = useTransition();
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button size="xs" variant="ghost" className="gap-1" />}>
        <Ban className="size-3" aria-hidden="true" /> Not a booking
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Invoice {number} isn&apos;t for a booking?</DialogTitle>
          <DialogDescription>
            For money that isn&apos;t a sale - a cost share, a refund, a recharge. It won&apos;t be matched to bookings again, and moves to
            &ldquo;Marked as not a booking&rdquo; on this page, where it can be put back.
          </DialogDescription>
        </DialogHeader>
        <Input className="h-9 text-sm" value={note} onChange={(e) => setNote(e.target.value)} placeholder="What is it? e.g. Reed's half of the freelancer fee (optional)" maxLength={300} />
        <DialogFooter>
          <Button size="sm" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            size="sm"
            disabled={pending}
            onClick={() =>
              start(async () => {
                try {
                  await markInvoiceNotBooking(invoiceId, note.trim() || null);
                  toast.success(`Invoice ${number ?? ""} marked as not a booking`);
                  setOpen(false);
                  router.refresh();
                } catch (e) {
                  toast.error(friendlyError(e, "Couldn't save that"));
                }
              })
            }
          >
            Not a booking
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function PutBackButton({ invoiceId }: { invoiceId: string }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  return (
    <Button
      size="xs"
      variant="outline"
      className="gap-1"
      disabled={pending}
      onClick={() =>
        start(async () => {
          try {
            await putBackInvoice(invoiceId);
            toast.success("Put back - it will be matched to bookings again within the hour");
            router.refresh();
          } catch (e) {
            toast.error(friendlyError(e, "Couldn't put it back"));
          }
        })
      }
    >
      <RotateCcw className="size-3" aria-hidden="true" /> Put back
    </Button>
  );
}
