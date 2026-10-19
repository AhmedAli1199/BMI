"use client";

import { useEffect, useTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { CalendarCheck2, CircleAlert, Loader2, RefreshCw, Unplug } from "lucide-react";
import { toast } from "sonner";
import type { CalendarSetup as Setup } from "@/lib/calls-types";
import { disconnectCalendar, setRecordingPreference, syncCalendarsNow } from "@/lib/calls-actions";
import { friendlyError } from "@/lib/errors";
import { Button } from "@/components/ui/button";
import { InfoHint } from "@/components/sales/info-hint";

const NAMES = { google: "Google Calendar", microsoft: "Outlook Calendar" } as const;

function ago(iso: string | null) {
  if (!iso) return "not read yet";
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  return mins < 1 ? "just now" : mins < 60 ? `${mins} min ago` : new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

/** Connect calendars and choose what the notetaker does with your meetings. */
export function CalendarSetup({ setup }: { setup: Setup }) {
  const router = useRouter();
  const params = useSearchParams();
  const [pending, start] = useTransition();

  useEffect(() => {
    const ok = params.get("calendar_connected") || params.get("outlook_connected");
    const err = params.get("calendar_error");
    if (ok) toast.success(`Calendar connected (${ok}) - its meetings now show on the shared calendar`);
    if (err) toast.error(friendlyError(err, "Your calendar couldn't be connected - please try again."));
    if (ok || err) router.replace("/calls/meetings");
  }, [params, router]);

  const run = (fn: () => Promise<unknown>, ok: string, fallback: string) =>
    start(async () => { try { await fn(); toast.success(ok); router.refresh(); } catch (e) { toast.error(friendlyError(e, fallback)); } });

  const has = (p: "google" | "microsoft") => setup.connections.find((c) => c.provider === p);

  return (
    <section aria-labelledby="cal-setup" className="rounded-xl border border-border/80 bg-card p-5 shadow-2xs">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h2 id="cal-setup" className="flex items-center gap-1.5 text-sm font-bold">
          <CalendarCheck2 className="size-4 text-primary" aria-hidden="true" /> Your calendars
          <InfoHint>Read-only: BMI Brain only looks at your meetings, it never changes them. Meetings with the same link and time in several people&apos;s calendars show once, with everyone from BMI who&apos;s in it.</InfoHint>
        </h2>
        {setup.connections.length > 0 && (
          <Button size="sm" variant="ghost" className="gap-1.5" disabled={pending}
            onClick={() => run(() => syncCalendarsNow(), "Calendars read again", "Couldn't read your calendars just now")}>
            {pending ? <Loader2 className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />} Check now
          </Button>
        )}
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        {(["microsoft", "google"] as const).map((p) => {
          const c = has(p);
          const available = p === "google" ? setup.google_available : setup.microsoft_available;
          return (
            <div key={p} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border/70 px-3 py-2.5">
              <div className="min-w-0">
                <div className="text-sm font-semibold">{NAMES[p]}</div>
                {c ? (
                  c.status === "error" ? (
                    <div className="flex items-center gap-1 text-[11px]" style={{ color: "var(--destructive)" }}><CircleAlert className="size-3" /> {c.last_error || "Needs reconnecting"}</div>
                  ) : (
                    <div className="truncate text-[11px] text-muted-foreground">{c.email} · read {ago(c.last_synced_at)}</div>
                  )
                ) : (
                  <div className="text-[11px] text-muted-foreground">{available ? "Not connected" : "Not set up yet - an administrator needs to add it"}</div>
                )}
              </div>
              {c ? (
                <div className="flex gap-1.5">
                  {c.status === "error" && <Button size="xs" nativeButton={false} render={<a href={`/api/calendar/connect?provider=${p}`} />}>Reconnect</Button>}
                  <Button size="xs" variant="ghost" className="gap-1" disabled={pending}
                    onClick={() => { if (window.confirm(`Disconnect ${NAMES[p]}? Its meetings leave the shared calendar.`)) run(() => disconnectCalendar(p), "Disconnected", "Couldn't disconnect it"); }}>
                    <Unplug className="size-3" /> Disconnect
                  </Button>
                </div>
              ) : available ? (
                <Button size="xs" nativeButton={false} render={<a href={`/api/calendar/connect?provider=${p}`} />}>Connect</Button>
              ) : null}
            </div>
          );
        })}
      </div>
      <fieldset className="mt-4">
        <legend className="mb-1.5 text-xs font-semibold text-muted-foreground">When I have a meeting with a Meet or Teams link</legend>
        <div className="flex flex-wrap gap-2">
          {([["auto", "The notetaker joins automatically"], ["remind", "Just remind me"], ["off", "Do nothing"]] as const).map(([v, label]) => (
            <label key={v} className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-1.5 text-sm ${setup.preference === v ? "border-primary" : "border-border/70"}`}>
              <input type="radio" name="cal-pref" checked={setup.preference === v} disabled={pending}
                onChange={() => run(() => setRecordingPreference(v), "Saved", "Couldn't save that")} />
              {label}
            </label>
          ))}
        </div>
      </fieldset>
      {!setup.notetaker_available && <p className="mt-3 text-xs" style={{ color: "var(--warn)" }}>The notetaker itself isn&apos;t connected yet, so nothing will be recorded until an administrator connects it.</p>}
    </section>
  );
}
