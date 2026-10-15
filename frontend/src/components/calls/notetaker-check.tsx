"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, CircleAlert, Loader2, RotateCcw, Stethoscope } from "lucide-react";
import { toast } from "sonner";
import type { NotetakerHealth } from "@/lib/calls-types";
import { getNotetakerHealth, startCalendarOver } from "@/lib/calls-actions";
import { friendlyError } from "@/lib/errors";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";

function when(iso: string) {
  return new Date(iso).toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

/** Admins: is everything the automatic notetaker needs working, which meetings it missed and why, and a fresh start. */
export function NotetakerCheck() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [health, setHealth] = useState<NotetakerHealth | null>(null);
  const [loading, setLoading] = useState(false);
  const [pending, start] = useTransition();

  const load = async () => {
    setLoading(true);
    try { setHealth(await getNotetakerHealth()); }
    catch (e) { toast.error(friendlyError(e, "Couldn't run the check just now")); }
    finally { setLoading(false); }
  };

  const startOver = () => {
    if (!window.confirm("Clear the whole meeting history and start fresh?\n\nEvery meeting on this list is removed and bots that were booked but haven't joined are called off. Calendar connections stay, and the calendars are read again straight away. Calls that were recorded keep their notes.")) return;
    start(async () => {
      try {
        const r = await startCalendarOver();
        toast.success(`Cleared ${r.meetings} meeting${r.meetings === 1 ? "" : "s"} - the calendars have been read again`);
        router.refresh();
        await load();
      } catch (e) { toast.error(friendlyError(e, "Couldn't clear the meeting history")); }
    });
  };

  return (
    <>
      <Button size="sm" variant="outline" className="gap-1.5 self-start" onClick={() => { setOpen(true); void load(); }}>
        <Stethoscope className="size-3.5" /> Notetaker check
      </Button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-full gap-0 p-0 sm:max-w-lg">
          <SheetHeader className="border-b border-border/70 px-5 py-4">
            <SheetTitle className="pr-8 text-base font-bold">Notetaker check</SheetTitle>
            <SheetDescription className="text-xs">Everything the automatic notetaker needs, and whether it&apos;s working. Only administrators see this.</SheetDescription>
          </SheetHeader>
          <div className="flex-1 space-y-5 overflow-y-auto px-5 py-4">
            {loading && !health ? (
              <p className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" /> Checking…</p>
            ) : health ? (
              <>
                <ul className="space-y-2">
                  {health.checks.map((c, i) => (
                    <li key={i} className="flex gap-2 rounded-lg border border-border/70 px-3 py-2">
                      {c.ok ? <CheckCircle2 className="mt-0.5 size-4 shrink-0" style={{ color: "var(--ok)" }} aria-label="Working" />
                        : <CircleAlert className="mt-0.5 size-4 shrink-0" style={{ color: "var(--destructive)" }} aria-label="Needs attention" />}
                      <div className="min-w-0">
                        <div className="text-sm font-semibold">{c.label}</div>
                        <div className="text-xs text-muted-foreground">{c.text}</div>
                      </div>
                    </li>
                  ))}
                </ul>
                <div>
                  <h3 className="mb-1.5 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Missed in the last 7 days{health.missed_count ? ` (${health.missed_count})` : ""}
                  </h3>
                  {health.missed.length === 0 ? (
                    <p className="text-sm text-muted-foreground">None - every meeting that should have been recorded was.</p>
                  ) : (
                    <ul className="divide-y divide-border/60 rounded-lg border border-border/70">
                      {health.missed.map((m, i) => (
                        <li key={i} className="px-3 py-2">
                          <div className="text-sm font-medium">{m.title} <span className="text-xs font-normal text-muted-foreground">· {when(m.start_at)}</span></div>
                          <div className="text-xs" style={{ color: "var(--destructive)" }}>{m.text}</div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </>
            ) : null}
          </div>
          <SheetFooter className="flex-row items-center justify-between gap-2 border-t border-border/70 px-5 py-3">
            <Button size="sm" variant="ghost" className="gap-1.5" disabled={pending} onClick={startOver}>
              {pending ? <Loader2 className="size-3.5 animate-spin" /> : <RotateCcw className="size-3.5" />} Clear meeting history
            </Button>
            <Button size="sm" variant="outline" disabled={loading} onClick={() => void load()}>
              {loading ? <Loader2 className="size-3.5 animate-spin" /> : null} Check again
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </>
  );
}
