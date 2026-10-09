import type { DealStatus } from "@/lib/deals-types";
import { DEAL_STATUS_LABEL } from "@/lib/deals-types";

const TONE: Record<DealStatus, string> = { pencilled: "var(--warn)", confirmed: "var(--ok)", cancelled: "var(--bad)" };

export function DealStatusPill({ status }: { status: DealStatus }) {
  const c = TONE[status];
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-semibold"
      style={{ color: c, borderColor: `color-mix(in oklab, ${c} 35%, transparent)` }}>
      <span className="size-1.5 rounded-full" style={{ background: c }} aria-hidden="true" />
      {DEAL_STATUS_LABEL[status]}
    </span>
  );
}
