"use client";

import { useEffect, useState, useTransition } from "react";
import { CheckCircle2, FileCheck2, Lock, Unlock } from "lucide-react";
import { toast } from "sonner";
import type { EditionCommission } from "@/lib/commission-types";
import type { SalesRep } from "@/lib/sales-types";
import { getEditionCommission, markCostsFinal, markNewGuide, signOffCosts } from "@/lib/commission-actions";
import { Button } from "@/components/ui/button";
import { InfoHint } from "@/components/sales/info-hint";
import { fmtDate } from "@/components/sales/sales-ui";

const selectCls = "h-7 rounded-lg border border-input bg-transparent px-2 text-xs outline-none focus-visible:border-ring dark:bg-input/30";

/** Commission bits on an edition: "new contract-publishing guide" (guide bonus) and event cost sign-off (profit share). */
export function EditionCommissionPanel({ editionId, reps }: { editionId: string; reps: SalesRep[] }) {
  const [c, setC] = useState<EditionCommission | null>(null);
  const [rep, setRep] = useState("");
  const [pending, start] = useTransition();

  useEffect(() => {
    let live = true;
    getEditionCommission(editionId).then((r) => { if (live) { setC(r); setRep(r.new_contract_rep?.id ?? ""); } }).catch(() => undefined);
    return () => { live = false; };
  }, [editionId]);

  if (!c || (!c.guide_title && !c.profit_share && !c.new_contract_guide)) return null;
  const run = (fn: () => Promise<EditionCommission>, ok: string) => start(async () => {
    try { setC(await fn()); toast.success(ok); } catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't save"); }
  });
  const who = c.profit_share_reps.map((r) => r.name.split(" ")[0]).join(" and ");

  return (
    <section aria-label="Commission" className="flex flex-col gap-3 rounded-xl border border-border/80 bg-card px-4 py-3 shadow-2xs">
      {(c.guide_title || c.new_contract_guide) && (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="flex items-center gap-1 font-semibold">New contract-publishing guide <InfoHint>Tick this on a guide or supplement that is a new contract-publishing job. Whoever sold it gets the new-guide bonus in the month it publishes.</InfoHint></span>
          {c.can_mark_guide ? (
            <>
              <label className="flex items-center gap-1.5 text-xs">
                <input type="checkbox" checked={c.new_contract_guide} disabled={pending} onChange={(e) => {
                  if (e.target.checked && !rep) return toast.error("Choose who sold it first");
                  run(() => markNewGuide(editionId, e.target.checked, e.target.checked ? rep : null), e.target.checked ? "Marked as a new guide" : "Unmarked");
                }} /> Yes
              </label>
              <select className={selectCls} value={rep} disabled={pending} aria-label="Who sold it" onChange={(e) => { setRep(e.target.value); if (c.new_contract_guide && e.target.value) run(() => markNewGuide(editionId, true, e.target.value), "Saved"); }}>
                <option value="">Who sold it?</option>
                {reps.filter((r) => r.active).map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
              </select>
            </>
          ) : <span className="text-xs text-muted-foreground">{c.new_contract_guide ? `Yes, sold by ${c.new_contract_rep?.name ?? "-"}` : "No"}</span>}
        </div>
      )}
      {c.profit_share && (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="flex items-center gap-1 font-semibold">Event costs for {who}&apos;s profit share
            <InfoHint>{who}&apos;s commission includes a share of this event&apos;s profit (income minus the costs below). Mark the costs final once the event has run and every bill is in; a manager then signs them off and the share goes on that month&apos;s statement. Signed-off costs are locked.</InfoHint>
          </span>
          {c.costs_signed_off_at ? (
            <span className="inline-flex items-center gap-1 text-xs" style={{ color: "var(--ok)" }}><Lock className="size-3.5" aria-hidden="true" /> Signed off {fmtDate(c.costs_signed_off_at.slice(0, 10))}{c.costs_signed_off_by ? ` by ${c.costs_signed_off_by}` : ""}</span>
          ) : c.costs_final_at ? (
            <span className="inline-flex items-center gap-1 text-xs" style={{ color: "var(--ok)" }}><CheckCircle2 className="size-3.5" aria-hidden="true" /> Final{c.costs_final_by ? ` (${c.costs_final_by})` : ""}, waiting for sign-off</span>
          ) : <span className="text-xs text-muted-foreground">Still being added</span>}
          <span className="ml-auto flex gap-1.5">
            {!c.costs_signed_off_at && c.can_mark_final && (
              <Button size="xs" variant="outline" className="gap-1" disabled={pending} onClick={() => run(() => markCostsFinal(editionId, !c.costs_final_at), c.costs_final_at ? "Back to draft" : "Marked final")}>
                <FileCheck2 className="size-3" /> {c.costs_final_at ? "Not final yet" : "Costs are final"}
              </Button>
            )}
            {c.can_sign_off && !c.costs_signed_off_at && c.costs_final_at && (
              <Button size="xs" className="gap-1" disabled={pending} onClick={() => run(() => signOffCosts(editionId, true), "Signed off")}><Lock className="size-3" /> Sign off</Button>
            )}
            {c.can_sign_off && c.costs_signed_off_at && (
              <Button size="xs" variant="ghost" className="gap-1" disabled={pending} onClick={() => {
                if (window.confirm("Reopen these costs? Any change after this shows as an adjustment on the next statement.")) run(() => signOffCosts(editionId, false), "Reopened");
              }}><Unlock className="size-3" /> Reopen</Button>
            )}
          </span>
        </div>
      )}
    </section>
  );
}
