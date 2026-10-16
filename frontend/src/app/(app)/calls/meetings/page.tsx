import { Suspense } from "react";
import { backendFetch } from "@/lib/backend";
import type { CalendarSetup as Setup, SharedMeeting } from "@/lib/calls-types";
import { CallsTabs } from "@/components/calls/calls-tabs";
import { CalendarSetup } from "@/components/calls/calendar-setup";
import { MeetingsAgenda } from "@/components/calls/meetings-agenda";
import { AutoRefresh } from "@/components/calls/auto-refresh";
import { SendNotetaker } from "@/components/calls/send-notetaker";
import { NotetakerCheck } from "@/components/calls/notetaker-check";
import { getSession } from "@/lib/session";
import { PageHeader } from "@/components/page-header";

/** The shared calendar: everyone's connected Google and Outlook meetings in one place, and what the notetaker will do with each. */
export default async function MeetingsPage() {
  const [session, setup, data] = await Promise.all([
    getSession(),
    backendFetch<Setup>("/api/calendar/connections").catch(() => null),
    backendFetch<{ meetings: SharedMeeting[]; people: string[] }>("/api/calendar/meetings").catch(() => ({ meetings: [], people: [] })),
  ]);
  const live = data.meetings.some((m) => m.call && ["joining", "waiting_room", "recording", "processing"].includes(m.call.status));
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <AutoRefresh seconds={live ? 6 : 60} />
      <PageHeader
        title="Call notes"
        section="Everyday"
        description="Everyone's meetings in one shared calendar. BMI Notetaker joins the ones with a Meet or Teams link and writes up the notes - skip any you don't want recorded."
        actions={session?.role === "admin" ? <NotetakerCheck /> : undefined}
      />
      <CallsTabs active="meetings" />
      <SendNotetaker />
      {setup && <Suspense><CalendarSetup setup={setup} /></Suspense>}
      <MeetingsAgenda meetings={data.meetings} people={data.people} />
    </div>
  );
}
