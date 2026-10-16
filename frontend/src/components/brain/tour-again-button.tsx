"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { BrainBuddy } from "@/components/brain/brain-buddy";
import { setTourDone } from "@/lib/brain-coach";
import { friendlyError } from "@/lib/errors";

/** Plays the Brain's welcome tour again from Home. */
export function TourAgainButton({ tour }: { tour: string }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  return (
    <Button variant="outline" size="sm" className="gap-1.5" disabled={pending}
      onClick={() => start(async () => {
        try { await setTourDone(tour, false); router.push("/"); router.refresh(); }
        catch (e) { toast.error(friendlyError(e, "Couldn't start the tour")); }
      })}>
      <BrainBuddy head mood="happy" size={18} still /> Take the tour again
    </Button>
  );
}
