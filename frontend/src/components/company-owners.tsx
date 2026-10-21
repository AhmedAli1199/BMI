"use client";

import { useState, useTransition } from "react";
import { Loader2, UserRound } from "lucide-react";
import { toast } from "sonner";
import { changeClientOwner, type ClientOwner, type ClientOwners } from "@/lib/client-owners";
import { friendlyError } from "@/lib/errors";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { InfoHint } from "@/components/sales/info-hint";

const selectCls = "h-8 w-full min-w-0 rounded-md border border-input bg-transparent px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";
const NOBODY = "__nobody";

function RuleBadge({ o }: { o: ClientOwner }) {
  const tone = o.rule === "not_sure" ? "border-[var(--warn)]/40 bg-[var(--warn-tint)] text-[var(--warn)]"
    : o.chosen ? "border-primary/30 bg-primary/10 text-primary" : "text-muted-foreground";
  return <Badge variant="outline" className={`text-[11px] font-medium ${tone}`}>{o.rule_label}</Badge>;
}

/** "Who looks after them": one line per magazine with the salesperson and why. Administrators and data managers
 * can change it; a change is kept until someone puts it back to the rules. */
export function CompanyOwners({ companyId, initial }: { companyId: string; initial: ClientOwners }) {
  const [data, setData] = useState(initial);
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [pending, start] = useTransition();
  if (!data.owners.length) return null;

  const openSheet = () => {
    setDraft(Object.fromEntries(data.owners.filter((o) => !o.fixed).map((o) => [o.area, o.rep_id ?? NOBODY])));
    setOpen(true);
  };
  const editable = data.owners.filter((o) => !o.fixed);
  const save = () => start(async () => {
    try {
      let out = data;
      for (const o of editable) {
        const v = draft[o.area];
        if (v === undefined || v === (o.rep_id ?? NOBODY)) continue;
        out = await changeClientOwner(companyId, o.area, { rep_id: v === NOBODY ? null : v });
      }
      setData(out); setOpen(false); toast.success("Saved");
    } catch (e) { toast.error(friendlyError(e, "Couldn't save who looks after them. Try again.")); }
  });
  const backToRules = (area: string) => start(async () => {
    try { const out = await changeClientOwner(companyId, area, { rep_id: null, back_to_rules: true }); setData(out); setOpen(false); toast.success("Back to the rules"); }
    catch (e) { toast.error(friendlyError(e, "Couldn't put it back to the rules. Try again.")); }
  });

  return (
    <Card className="gap-2 py-3">
      <CardHeader className="flex flex-row items-center justify-between gap-2 px-4">
        <CardTitle className="flex items-center gap-1.5 text-sm font-semibold">
          <UserRound className="size-4 text-muted-foreground" aria-hidden="true" /> Who looks after them
          <InfoHint>
            Worked out by the agreed rules: The Business Travel Magazine is Kirsty&apos;s, Selling Travel events are Steve&apos;s and the
            Accessibility Awards are David&apos;s. Otherwise a client stays with whoever was last in touch or last booked them in the last two
            years; new Onboard Hospitality business is Craig&apos;s, and Selling Travel goes by the destination the client promotes. Checked again
            every night.
          </InfoHint>
        </CardTitle>
        {data.can_change && editable.length > 0 && <Button size="sm" variant="outline" onClick={openSheet}>Change</Button>}
      </CardHeader>
      <CardContent className="px-4">
        <ul className="flex flex-col divide-y divide-border/60">
          {data.owners.map((o) => (
            <li key={o.area} className="grid gap-x-3 gap-y-0.5 py-1.5 text-sm sm:grid-cols-[13rem_10rem_minmax(0,1fr)] sm:items-baseline">
              <span className="font-medium">{o.magazine}</span>
              <span className={o.rep_name ? "" : "text-muted-foreground"}>{o.rep_name ?? "Nobody yet"}</span>
              <span className="flex min-w-0 flex-wrap items-baseline gap-1.5 text-xs text-muted-foreground">
                <RuleBadge o={o} /><span className="min-w-0">{o.reason}</span>
              </span>
            </li>
          ))}
        </ul>
      </CardContent>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-full gap-0 overflow-y-auto p-0 sm:max-w-md">
          <SheetHeader className="border-b border-border/70">
            <SheetTitle>Who looks after them</SheetTitle>
            <SheetDescription>Your choice is kept, and the nightly check won&apos;t change it. Press Back to the rules to let the rules decide again.</SheetDescription>
          </SheetHeader>
          <div className="flex flex-col gap-4 p-4">
            {editable.map((o) => (
              <div key={o.area} className="flex flex-col gap-1.5">
                <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">{o.magazine}
                  <select className={selectCls} value={draft[o.area] ?? NOBODY} onChange={(e) => setDraft({ ...draft, [o.area]: e.target.value })}>
                    <option value={NOBODY}>Nobody yet (whoever takes it first)</option>
                    {data.people.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </label>
                <p className="text-xs text-muted-foreground">Now: {o.reason}</p>
                {o.chosen && (
                  <button type="button" disabled={pending} className="self-start text-xs font-medium text-primary hover:underline" onClick={() => backToRules(o.area)}>
                    Back to the rules
                  </button>
                )}
              </div>
            ))}
          </div>
          <SheetFooter className="flex-row border-t border-border/70">
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button disabled={pending} onClick={save}>{pending && <Loader2 className="size-3.5 animate-spin" />} Save</Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </Card>
  );
}
