"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Wand2 } from "lucide-react";
import { toast } from "sonner";
import type { NewBusinessStatus } from "@/lib/commission-types";
import { NB_LABEL } from "@/lib/commission-types";
import { loadCommissionStructure } from "@/lib/commission-actions";
import { Button } from "@/components/ui/button";
import { friendlyError } from "@/lib/errors";
export { monthLabel, pctLabel } from "@/lib/commission-format";

const NB_TONE: Record<NewBusinessStatus, string> = { new: "var(--ok)", returning: "var(--muted-foreground)", check: "var(--warn)" };

export function NewBusinessPill({ status, manager }: { status: NewBusinessStatus; manager?: boolean }) {
  const c = NB_TONE[status];
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap rounded-full px-1.5 py-0.5 text-[10px] font-semibold"
      style={{ color: c, background: `color-mix(in oklab, ${c} 14%, transparent)` }}>
      {NB_LABEL[status]}{manager ? " · set by a manager" : ""}
    </span>
  );
}

/** One button: loads Matt's commission structure (Oct 2026) as everyone's plan. */
export function LoadStructureButton({ replace = false, label = "Load BMI's commission structure" }: { replace?: boolean; label?: string }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  return (
    <Button size="sm" className="gap-1.5" disabled={pending} onClick={() => {
      if (replace && !window.confirm("Replace every salesperson's plan with BMI's structure? Your own changes to the plans will be lost.")) return;
      start(async () => {
        try {
          const r = await loadCommissionStructure(replace);
          toast.success(`${r.rules} commission rules loaded`);
          router.refresh();
        } catch (e) { toast.error(friendlyError(e, "Couldn't load the structure")); }
      });
    }}>
      {pending ? <Loader2 className="size-3.5 animate-spin" /> : <Wand2 className="size-3.5" />} {label}
    </Button>
  );
}
