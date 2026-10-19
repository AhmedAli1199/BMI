"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Pencil, Send, Users } from "lucide-react";
import { toast } from "sonner";
import { ACTIVITY_KINDS, type Deal, type DealLine, type HandoffRoutes } from "@/lib/deals-types";
import { sendHandoffs, setLineHandoff } from "@/lib/deals-actions";
import { Input } from "@/components/ui/input";
import { friendlyError } from "@/lib/errors";
import { Button } from "@/components/ui/button";
import { fmtDate } from "@/components/sales/sales-ui";
import { LineHandoff } from "@/components/deals/line-handoff";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";

const STATE: Record<string, [string, string]> = {
  sent: ["Sent", "var(--ok)"], failed: ["Didn't go", "var(--bad)"], no_address: ["No address yet", "var(--warn)"],
  waiting_format: ["Waiting for the format", "var(--muted-foreground)"], waiting_check: ["Goes after the accounts check", "var(--muted-foreground)"],
  due: ["Ready to send", "var(--warn)"],
};

/** Who each item has gone to (editorial / production) and when, with Send again. */
export function DealHandoffs({ deal, titles = [], routes, productionEmails = "" }: {
  deal: Deal;
  /** For the Brain's team suggestion in the editor (title names). */
  titles?: { id: string; name: string }[];
  routes?: HandoffRoutes;
  productionEmails?: string;
}) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [busy, setBusy] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  // On a locked booking the edit form is closed, so the hand-off details are changed here (they don't change the invoice).
  const canChange = !!deal.locked && (deal.can_edit || !!deal.can_approve);
  const rows = (deal.handoffs ?? []).filter((h) => h.teams.length > 0 || canChange);
  if (!rows.length || deal.status === "cancelled") return null;
  const editLine = editing ? deal.lines.find((l) => l.key === editing) ?? null : null;
  // Only that item, only that team: teams it already went to aren't sent it again.
  const send = (line: string, team: string) => { setBusy(`${line}:${team}`); start(async () => {
    try { const d = await sendHandoffs(deal.id, [line], [team]); toast.success((d.notes_after_save ?? [])[0] ?? "Done"); router.refresh(); }
    catch (e) { toast.error(friendlyError(e, "Couldn't send it")); }
  }); };
  return (
    <section className="rounded-xl border border-border/80 bg-card shadow-2xs" aria-labelledby="ho-h">
      <h2 id="ho-h" className="flex items-center gap-1.5 border-b border-border/70 px-4 py-3 text-sm font-bold"><Users className="size-4" aria-hidden="true" /> Hand-offs to editorial and production</h2>
      <ul className="divide-y divide-border/60">
        {rows.map((h) => (
          <li key={h.line} className="flex flex-wrap items-start gap-3 px-4 py-2.5 text-sm">
            <div className="min-w-0 flex-1">
              <p className="font-medium">{h.description}{h.format ? <span className="font-normal text-muted-foreground"> · {h.format}</span> : null}</p>
              {h.activities.length > 0 && <p className="text-xs text-muted-foreground">Also {h.activities.map((a) => `${ACTIVITY_KINDS.find((k) => k.value === a.kind)?.label ?? a.kind}${a.on ? ` ${fmtDate(a.on)}` : ""}${a.note ? ` (${a.note})` : ""}`).join(" · ")}</p>}
              {h.teams.length === 0 && <p className="text-xs text-muted-foreground">Not handed off to anyone.</p>}
              {h.teams.some((t) => t.state === "waiting_format") && deal.can_edit && <FormatBox deal={deal} lineKey={h.line} />}
              {h.teams.map((t) => (
                <p key={t.team} className="text-xs">
                  <span className="font-semibold capitalize">{t.team}</span>: {t.to.length ? t.to.join(", ") : "nobody set"} ·{" "}
                  <span style={{ color: STATE[t.state][1] }} className="font-medium">{STATE[t.state][0]}{t.state === "sent" && t.sent_at ? ` ${fmtDate(t.sent_at.slice(0, 10))}` : ""}</span>
                  {t.error && <span className="text-muted-foreground"> - {t.error}</span>}
                  {deal.handoffs_ready && t.to.length > 0 && t.state !== "waiting_format" && (
                    <Button size="sm" variant="ghost" className="ml-1 h-6 gap-1 px-1.5 text-xs" disabled={pending}
                      aria-label={`${t.state === "sent" ? "Send again" : "Send"} to ${t.team}`} onClick={() => send(h.line, t.team)}>
                      {pending && busy === `${h.line}:${t.team}` ? <Loader2 className="size-3 animate-spin" /> : <Send className="size-3" />} {t.state === "sent" ? "Send again" : "Send"}
                    </Button>
                  )}
                </p>
              ))}
            </div>
            {canChange && (
              <Button size="sm" variant="outline" className="h-7 gap-1 px-2 text-xs" onClick={() => setEditing(h.line)} aria-label={`Change the hand-off for ${h.description}`}>
                <Pencil className="size-3" aria-hidden="true" /> Change hand-off
              </Button>
            )}
          </li>
        ))}
      </ul>
      <Sheet open={!!editLine} onOpenChange={(o) => !o && setEditing(null)}>
        <SheetContent side="right" className="w-full gap-0 overflow-y-auto p-0 sm:max-w-lg">
          {editLine && (
            <HandoffEditor key={editLine.key ?? ""} deal={deal} line={editLine} titles={titles} routes={routes} productionEmails={productionEmails} onDone={() => setEditing(null)} />
          )}
        </SheetContent>
      </Sheet>
    </section>
  );
}

/** The same hand-off editor as the booking form, for one item of a locked booking: teams, their addresses, the format and where else it appears. */
function HandoffEditor({ deal, line, titles, routes, productionEmails, onDone }: {
  deal: Deal; line: DealLine; titles: { id: string; name: string }[]; routes?: HandoffRoutes; productionEmails: string; onDone: () => void;
}) {
  const router = useRouter();
  const [draft, setDraft] = useState<DealLine>(line);
  const [pending, start] = useTransition();
  const save = () => start(async () => {
    try {
      await setLineHandoff(deal.id, line.key ?? "", { handoff: draft.handoff ?? { team: "auto" }, activities: draft.activities ?? [] });
      toast.success("Hand-off saved");
      onDone();
      router.refresh();
    } catch (e) {
      toast.error(friendlyError(e, "Couldn't save the hand-off"));
    }
  });
  return (
    <>
      <SheetHeader className="border-b border-border/70">
        <SheetTitle>Hand-off for {line.description || "this item"}</SheetTitle>
        <SheetDescription>
          This booking has been checked by accounts, but who works on it after it&apos;s sold can still be changed here - it doesn&apos;t change the invoice.
          When you save, a team that hasn&apos;t had it yet is sent it, and a team that already has it gets one email marked as a change.
        </SheetDescription>
      </SheetHeader>
      <div className="p-4">
        <LineHandoff line={draft} titleName={titles.find((t) => t.id === draft.title_id)?.name ?? null} productName={null} routes={routes}
          productionFallback={productionEmails} onChange={(patch) => setDraft((d) => ({ ...d, ...patch }))} />
      </div>
      <SheetFooter className="flex-row justify-end border-t border-border/70">
        <Button variant="ghost" onClick={onDone}>Cancel</Button>
        <Button disabled={pending || !line.key} onClick={save}>{pending && <Loader2 className="size-3.5 animate-spin" />} Save hand-off</Button>
      </SheetFooter>
    </>
  );
}

/** The client has picked the sponsored format: fill it in and editorial are told (works on a locked booking). */
function FormatBox({ deal, lineKey }: { deal: Deal; lineKey: string }) {
  const router = useRouter();
  const [v, setV] = useState("");
  const [pending, start] = useTransition();
  const line = deal.lines.find((l) => l.key === lineKey);
  return (
    <div className="my-1 flex flex-wrap items-center gap-1.5">
      <Input value={v} onChange={(e) => setV(e.target.value)} placeholder="The format the client chose, e.g. How to sell" className="h-7 w-64 text-xs" aria-label="Format" />
      <Button size="sm" className="h-7 px-2 text-xs" disabled={pending || !v.trim()} onClick={() => start(async () => {
        try { await setLineHandoff(deal.id, lineKey, { handoff: { ...(line?.handoff ?? { team: "auto" }), format: v.trim() } }); toast.success("Saved. Editorial are told now."); router.refresh(); }
        catch (e) { toast.error(friendlyError(e, "Couldn't save the format")); }
      })}>{pending && <Loader2 className="size-3 animate-spin" />} Save and tell editorial</Button>
    </div>
  );
}
