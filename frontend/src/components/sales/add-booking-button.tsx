"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import type { SalesRep } from "@/lib/sales-types";
import { Button } from "@/components/ui/button";
import { OrderSheet, type OrderSheetTarget } from "@/components/sales/order-sheet";

/** "Add booking" for one edition - opens the booking sheet empty. */
export function AddBookingButton({
  edition,
  reps,
}: {
  edition: { editionId: string; titleId: string; editionLabel: string; year: number };
  reps: SalesRep[];
}) {
  const [target, setTarget] = useState<OrderSheetTarget | null>(null);
  return (
    <>
      <Button size="sm" className="h-9 gap-1.5" onClick={() => setTarget({ mode: "create", ...edition })}>
        <Plus className="size-3.5" aria-hidden="true" /> Add booking
      </Button>
      <OrderSheet target={target} reps={reps} canDelete={false} onClose={() => setTarget(null)} />
    </>
  );
}
