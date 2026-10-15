"use client";

import { Plus, Users, X } from "lucide-react";
import { ACTIVITY_KINDS, type DealActivity, type DealHandoff, type DealLine, type HandoffRoutes } from "@/lib/deals-types";
import { TEAM_LABEL, looksSponsored, routeFor, suggestTeam } from "@/lib/handoffs";
import { Input } from "@/components/ui/input";
import { InfoHint } from "@/components/sales/info-hint";

const selectCls = "h-7 rounded-md border border-input bg-transparent px-2 text-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";

/** On each item of the booking form: who works on it after it's sold, their addresses, the format, and where else it appears. */
export function LineHandoff({ line, titleName, productName, routes, productionFallback, onChange }: {
  line: DealLine; titleName: string | null; productName: string | null; routes?: HandoffRoutes; productionFallback: string;
  onChange: (patch: Pick<DealLine, "handoff"> | Pick<DealLine, "activities">) => void;
}) {
  const words = [line.description, line.detail, line.size, productName].filter(Boolean).join(" ");
  const suggested = suggestTeam(titleName, words);
  const h: DealHandoff = line.handoff ?? { team: "auto" };
  const team = h.team === "auto" ? suggested : h.team;
  const set = (patch: Partial<DealHandoff>) => onChange({ handoff: { ...h, ...patch } });
  const acts = line.activities ?? [];
  const setActs = (a: DealActivity[]) => onChange({ activities: a });
  const sponsored = looksSponsored(words);

  return (
    <details className="mt-3 rounded-lg border border-border/70 bg-muted/20 px-3 py-2 text-xs" open={sponsored || h.team !== "auto" || acts.length > 0}>
      <summary className="flex cursor-pointer items-center gap-1.5 font-semibold text-muted-foreground">
        <Users className="size-3.5" aria-hidden="true" /> After it&apos;s sold: {TEAM_LABEL[team]}{h.team === "auto" ? " (suggested)" : ""}
        <InfoHint>Once accounts have checked the booking, each team gets an email with this item, its dates and the client&apos;s copy contact, and a ready-written email asking the client for their copy or artwork.</InfoHint>
      </summary>
      <div className="mt-2 flex flex-col gap-2">
        <label className="flex flex-wrap items-center gap-1.5 text-muted-foreground">Hand off to
          <select className={selectCls} value={h.team} onChange={(e) => set({ team: e.target.value as DealHandoff["team"] })}>
            <option value="auto">Suggested: {TEAM_LABEL[suggested]}</option>
            <option value="editorial">Editorial</option><option value="production">Production</option>
            <option value="both">Editorial and production</option><option value="none">Nobody</option>
          </select>
        </label>
        {(team === "editorial" || team === "both") && (
          <div className="grid gap-2 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-muted-foreground">Editorial email(s)
              <Input value={h.editorial_to ?? ""} onChange={(e) => set({ editorial_to: e.target.value || null })}
                placeholder={routeFor(routes, line.title_id, "editorial") || "Type the editor's email"} className="h-7 text-xs" />
              {!h.editorial_to && !routeFor(routes, line.title_id, "editorial") && <span className="font-normal" style={{ color: "var(--warn)" }}>Nobody is set for this magazine yet - type the address.</span>}
            </label>
            <label className="flex flex-col gap-1 text-muted-foreground">Format or style
              <Input value={h.format ?? ""} onChange={(e) => set({ format: e.target.value || null })} placeholder="e.g. How to sell, Q&A - or TBC" className="h-7 text-xs" />
              <span className="font-normal">Not decided yet? Write TBC: editorial are told once you fill it in.</span>
            </label>
          </div>
        )}
        {(team === "production" || team === "both") && (
          <label className="flex flex-col gap-1 text-muted-foreground sm:w-1/2">Production email(s)
            <Input value={h.production_to ?? ""} onChange={(e) => set({ production_to: e.target.value || null })}
              placeholder={routeFor(routes, line.title_id, "production", productionFallback) || "Type production's email"} className="h-7 text-xs" />
            {!h.production_to && !routeFor(routes, line.title_id, "production", productionFallback) && <span className="font-normal" style={{ color: "var(--warn)" }}>Nobody is set yet - type the address.</span>}
          </label>
        )}
        {team !== "none" && (
          <div className="flex flex-col gap-1.5">
            <span className="font-semibold text-muted-foreground">Also appears</span>
            {acts.map((a, i) => (
              <div key={i} className="flex flex-wrap items-center gap-1.5">
                <select className={selectCls} value={a.kind} onChange={(e) => setActs(acts.map((x, j) => (j === i ? { ...x, kind: e.target.value as DealActivity["kind"] } : x)))} aria-label="Where">
                  {ACTIVITY_KINDS.map((k) => <option key={k.value} value={k.value}>{k.label}</option>)}
                </select>
                <Input type="date" value={a.on ?? ""} onChange={(e) => setActs(acts.map((x, j) => (j === i ? { ...x, on: e.target.value || null } : x)))} className="h-7 w-36 text-xs" aria-label="When" />
                <Input value={a.note ?? ""} onChange={(e) => setActs(acts.map((x, j) => (j === i ? { ...x, note: e.target.value || null } : x)))} placeholder="e.g. Selling Travel Weekly" className="h-7 w-48 text-xs" aria-label="Note" />
                <button type="button" aria-label="Remove" className="text-muted-foreground hover:text-foreground" onClick={() => setActs(acts.filter((_, j) => j !== i))}><X className="size-3.5" /></button>
              </div>
            ))}
            <button type="button" className="inline-flex items-center gap-1 self-start font-medium text-primary hover:underline" onClick={() => setActs([...acts, { kind: "online", on: null }])}>
              <Plus className="size-3" /> Online, newsletter, social…
            </button>
          </div>
        )}
      </div>
    </details>
  );
}
