"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Send, Users } from "lucide-react";
import { toast } from "sonner";
import { ACTIVITY_KINDS, type Deal } from "@/lib/deals-types";
import { sendHandoffs, setLineHandoff } from "@/lib/deals-actions";
import { Input } from "@/components/ui/input";
import { friendlyError } from "@/lib/errors";
import { Button } from "@/components/ui/button";
import { fmtDate } from "@/components/sales/sales-ui";

const STATE: Record<string, [string, string]> = {
  sent: ["Sent", "var(--ok)"], failed: ["Didn't go", "var(--bad)"], no_address: ["No address yet", "var(--warn)"],
  waiting_format: ["Waiting for the format", "var(--muted-foreground)"], waiting_check: ["Goes after the accounts check", "var(--muted-foreground)"],
  due: ["Ready to send", "var(--warn)"],
};

/** Who each item has gone to (editorial / production) and when, with Send again. */
export function DealHandoffs({ deal }: { deal: Deal }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const rows = (deal.handoffs ?? []).filter((h) => h.teams.length > 0);
  if (!rows.length || deal.status === "cancelled") return null;
  const send = (lines: string[]) => start(async () => {
    try { const d = await sendHandoffs(deal.id, lines); toast.success((d.notes_after_save ?? [])[0] ?? "Done"); router.refresh(); }
    catch (e) { toast.error(friendlyError(e, "Couldn't send it")); }
  });
  return (
    <section className="rounded-xl border border-border/80 bg-card shadow-2xs" aria-labelledby="ho-h">
      <h2 id="ho-h" className="flex items-center gap-1.5 border-b border-border/70 px-4 py-3 text-sm font-bold"><Users className="size-4" aria-hidden="true" /> Hand-offs to editorial and production</h2>
      <ul className="divide-y divide-border/60">
        {rows.map((h) => (
          <li key={h.line} className="flex flex-wrap items-start gap-3 px-4 py-2.5 text-sm">
            <div className="min-w-0 flex-1">
              <p className="font-medium">{h.description}{h.format ? <span className="font-normal text-muted-foreground"> · {h.format}</span> : null}</p>
              {h.activities.length > 0 && <p className="text-xs text-muted-foreground">Also {h.activities.map((a) => `${ACTIVITY_KINDS.find((k) => k.value === a.kind)?.label ?? a.kind}${a.on ? ` ${fmtDate(a.on)}` : ""}${a.note ? ` (${a.note})` : ""}`).join(" · ")}</p>}
              {h.teams.some((t) => t.state === "waiting_format") && deal.can_edit && <FormatBox deal={deal} lineKey={h.line} />}
              {h.teams.map((t) => (
                <p key={t.team} className="text-xs">
                  <span className="font-semibold capitalize">{t.team}</span>: {t.to.length ? t.to.join(", ") : "nobody set"} ·{" "}
                  <span style={{ color: STATE[t.state][1] }} className="font-medium">{STATE[t.state][0]}{t.state === "sent" && t.sent_at ? ` ${fmtDate(t.sent_at.slice(0, 10))}` : ""}</span>
                  {t.error && <span className="text-muted-foreground"> - {t.error}</span>}
                </p>
              ))}
            </div>
            {deal.check?.state === "checked" && h.teams.some((t) => t.to.length && t.state !== "waiting_format") && (
              <Button size="sm" variant="ghost" className="gap-1.5" disabled={pending} onClick={() => send([h.line])}>
                {pending ? <Loader2 className="size-3.5 animate-spin" /> : <Send className="size-3.5" />} {h.teams.every((t) => t.state === "sent") ? "Send again" : "Send"}
              </Button>
            )}
          </li>
        ))}
      </ul>
    </section>
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
