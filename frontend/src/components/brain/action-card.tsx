"use client";

import { Bell, CheckCircle2, ClipboardCheck, ExternalLink, Loader2, Mail, NotebookPen, ReceiptText, ToggleRight, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { BrainAction } from "@/lib/brain-types";

const ICONS: Record<string, typeof Bell> = {
  reminder: Bell, log: NotebookPen, email: Mail, booking: ReceiptText, review: ClipboardCheck, automation: ToggleRight,
};

/** Something the Brain offered to do (Phase 4, backend app/brain/actions.py). Nothing has happened yet: it runs
 * only when the person presses the button, and records it links to open in a new tab so they can check first. */
export function ActionCard({ card, busy, onDecide }: { card: BrainAction; busy: boolean; onDecide: (confirm: boolean) => void }) {
  const Icon = ICONS[card.kind] ?? ClipboardCheck;
  const waiting = card.status === "pending" && !(card.expires_at && new Date(card.expires_at) < new Date());
  const links = card.status === "done" && card.result.links?.length ? card.result.links : card.links;
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-border bg-card p-3 text-card-foreground shadow-sm" data-action-card={card.kind}>
      <div className="flex items-center gap-2">
        <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon className="size-4" /></span>
        <p className="min-w-0 flex-1 text-sm font-semibold">{card.title}</p>
        {card.status === "done" && <CheckCircle2 className="size-4 shrink-0" style={{ color: "var(--ok)" }} aria-label="Done" />}
        {(card.status === "failed") && <XCircle className="size-4 shrink-0" style={{ color: "var(--warn)" }} aria-label="Not done" />}
      </div>
      {card.lines.length > 0 && (
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
          {card.lines.map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-muted-foreground">{k}</dt>
              <dd className={k === "Email" ? "whitespace-pre-wrap rounded-md border border-border/70 bg-background p-2" : "min-w-0 break-words"}>{v}</dd>
            </div>
          ))}
        </dl>
      )}
      {links.length > 0 && (
        <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs">
          {links.map((l) => (
            <a key={l.href + l.label} href={l.href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline">
              {l.label} <ExternalLink className="size-3" />
            </a>
          ))}
        </div>
      )}
      {waiting ? (
        <div className="flex items-center justify-end gap-1.5 border-t border-border/60 pt-2">
          <span className="mr-auto text-[11px] text-muted-foreground">Nothing happens until you press {card.confirm}.</span>
          <Button size="xs" variant="ghost" disabled={busy} onClick={() => onDecide(false)}>Cancel</Button>
          <Button size="xs" disabled={busy} onClick={() => onDecide(true)}>{busy && <Loader2 className="size-3 animate-spin" />} {card.confirm}</Button>
        </div>
      ) : (
        <p className="border-t border-border/60 pt-2 text-xs" style={card.status === "failed" ? { color: "var(--warn)" } : undefined}>
          {card.result.text ?? (card.status === "pending" ? "This card has expired. Ask again and I'll make a new one." : "")}
        </p>
      )}
    </div>
  );
}
