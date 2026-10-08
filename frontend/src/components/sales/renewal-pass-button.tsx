"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { RefreshCcw } from "lucide-react";
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
import { startRenewalPass } from "@/lib/sales-actions";
import type { RenewalPassResult } from "@/lib/sales-types";
import { friendlyError } from "@/lib/errors";

/** SALES-021's "open a renewal pass": when an edition opens for bookings,
 * draft a renewal email for everyone who advertised in its equivalent
 * last cycle and hasn't rebooked - instead of waiting for each
 * advertiser's anniversary. */
export function RenewalPassButton({ editionId, editionLabel, renewsFrom }: { editionId: string; editionLabel: string; renewsFrom: string }) {
  const [open, setOpen] = useState(false);
  const [pending, start] = useTransition();
  const [result, setResult] = useState<RenewalPassResult | null>(null);

  function run() {
    start(async () => {
      try {
        setResult(await startRenewalPass(editionId));
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't start the renewal pass"));
      }
    });
  }

  return (
    <>
      <Button size="sm" variant="outline" className="gap-1.5 font-semibold" onClick={() => { setResult(null); setOpen(true); }}>
        <RefreshCcw className="size-3.5" aria-hidden="true" /> Start renewals
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Start renewals for {editionLabel}</DialogTitle>
            <DialogDescription>
              Drafts a personal renewal email for every advertiser in <strong>{renewsFrom}</strong> who hasn&apos;t booked again
              this year. Each one goes to the salesperson who sold it, to check and send from their own Outlook. Anyone
              already booked - or already sent a renewal this year - is left out, so it&apos;s safe to run again later.
            </DialogDescription>
          </DialogHeader>
          {result && (
            <div className="rounded-lg border border-border bg-muted/30 p-3 text-sm">
              <p>
                <strong>{result.queued}</strong> renewal email{result.queued === 1 ? "" : "s"} drafted from {result.advertisers} advertisers in{" "}
                {result.previous_edition}.
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {result.already_booked} already booked again · {result.already_queued} already had a renewal this year
              </p>
              {result.queued > 0 && (
                <Link href="/automations/revenue" className="mt-2 inline-block text-xs font-semibold text-primary hover:underline">
                  See them in Revenue &amp; Orders →
                </Link>
              )}
            </div>
          )}
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>{result ? "Done" : "Cancel"}</DialogClose>
            {!result && (
              <Button onClick={run} disabled={pending}>
                {pending ? "Drafting…" : "Draft renewal emails"}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
