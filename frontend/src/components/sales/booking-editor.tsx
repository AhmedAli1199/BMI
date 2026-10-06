"use client";

import { useState } from "react";
import { Pencil } from "lucide-react";
import type { SalesOrder, SalesRep } from "@/lib/sales-types";
import { Button } from "@/components/ui/button";
import { OrderSheet } from "@/components/sales/order-sheet";

/** The booking page's edit panel - open when the page loads (that's usually
 * why someone followed a link to a booking), reopenable from the button. */
export function BookingEditor({ order, reps, canDelete, year }: { order: SalesOrder; reps: SalesRep[]; canDelete: boolean; year: number }) {
  const [open, setOpen] = useState(true);
  return (
    <>
      <Button size="sm" className="gap-1.5 font-semibold" onClick={() => setOpen(true)}>
        <Pencil className="size-3.5" aria-hidden="true" />
        Edit booking
      </Button>
      <OrderSheet target={open ? { mode: "edit", order, year } : null} reps={reps} canDelete={canDelete} onClose={() => setOpen(false)} />
    </>
  );
}
