import { Suspense } from "react";
import { CalendarDays } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { CalendarSetup as Setup, SharedMeeting } from "@/lib/calls-types";
import { CallsTabs } from "@/components/calls/calls-tabs";
import { CalendarSetup } from "@/components/calls/calendar-setup";
import { MeetingsAgenda } from "@/components/calls/meetings-agenda";
import { AutoRefresh } from "@/components/calls/auto-refresh";
import { SendNotetaker } from "@/components/calls/send-notetaker";

/** The shared calendar: everyone's connected Google and Outlook meetings in one place, and what the notetaker will do with each. */
export default async function MeetingsPage() {
  const [setup, data] = await Promise.all([
    backendFetch<Setup>("/api/calendar/connections").catch(() => null),
    backendFetch<{ meetings: SharedMeeting[]; people: string[] }>("/api/calendar/meetings").catch(() => ({ meetings: [], people: [] })),
  ]);
  const live = data.meetings.some((m) => m.call && ["joining", "waiting_room", "recording", "processing"].includes(m.call.status));
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <AutoRefresh seconds={live ? 6 : 60} />
      <div>
        <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary"><CalendarDays className="size-3.5" /><span>Calls</span></div>
        <h1 className="editorial-title text-2xl font-bold tracking-tight sm:text-3xl">Call notes</h1>
        <p className="mt-1 max-w-2xl text-xs text-muted-foreground sm:text-sm">
          Everyone&apos;s meetings in one shared calendar. BMI Notetaker joins the ones with a Meet or Teams link and writes up the notes - skip any you don&apos;t want recorded.
        </p>
      </div>
      <CallsTabs active="meetings" />
      <SendNotetaker />
      {setup && <Suspense><CalendarSetup setup={setup} /></Suspense>}
      <MeetingsAgenda meetings={data.meetings} people={data.people} />
    </div>
  );
}
