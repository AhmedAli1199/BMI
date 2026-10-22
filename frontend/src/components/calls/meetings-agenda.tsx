"use client";

import { useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Ban, Bot, CircleAlert, ExternalLink, Lock } from "lucide-react";
import { toast } from "sonner";
import type { FilterDef, SortState } from "@/lib/data-view/schema";
import { PLATFORM_LABEL, type SharedMeeting } from "@/lib/calls-types";
import { setMeetingChoice } from "@/lib/calls-actions";
import { friendlyError } from "@/lib/errors";
import { ClientDataView } from "@/components/data-view/client-data-view";
import { DataViewLayout } from "@/components/data-view/data-view";
import { FilterSidebar } from "@/components/data-view/filter-sidebar";
import { DataSearch, FilterChips } from "@/components/data-view/toolbar";
import { Button } from "@/components/ui/button";
import { CallStatus } from "@/components/calls/call-status";

const DEFAULT_SORT: SortState = { key: "start", dir: "asc" };
const ACCESSORS = {
  q: (m: SharedMeeting) => [m.title, m.organizer, m.contact?.name, m.company?.name, ...m.bmi_people.map((p) => p.name), ...m.outside_people.map((p) => `${p.name} ${p.email}`)],
  person: (m: SharedMeeting) => m.bmi_people.map((p) => p.name),
  plan: (m: SharedMeeting) => (m.decision.record ? "record" : "no"),
  platform: (m: SharedMeeting) => m.platform ?? "none",
  mine: (m: SharedMeeting) => (m.mine ? "1" : "0"),
};
const TONE: Record<SharedMeeting["outcome"]["tone"], string> = {
  ok: "var(--ok)", live: "var(--warn)", warn: "var(--warn)", bad: "var(--destructive)", muted: "var(--muted-foreground)",
};
const SORTS = { start: (m: SharedMeeting) => m.start_at };

function day(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
}
function hm(iso: string) {
  return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

/** The shared calendar: everyone's meetings in one list, with what the notetaker will do. */
export function MeetingsAgenda({ meetings, people }: { meetings: SharedMeeting[]; people: string[] }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const defs: FilterDef[] = [
    { kind: "search", key: "q", label: "Search meetings", placeholder: "Title, person, company…" },
    { kind: "multi", key: "person", label: "Who from BMI", section: "Meeting", options: people.map((p) => ({ value: p, label: p })), searchable: people.length > 8 },
    { kind: "single", key: "plan", label: "Notetaker", section: "Meeting", options: [{ value: "record", label: "Meant to be recorded" }, { value: "no", label: "Not meant to be recorded" }] },
    { kind: "multi", key: "platform", label: "Call type", section: "Meeting", options: [{ value: "google_meet", label: "Google Meet" }, { value: "teams", label: "Microsoft Teams" }, { value: "zoom", label: "Zoom" }, { value: "none", label: "No meeting link" }] },
    { kind: "single", key: "mine", label: "Whose", section: "Meeting", options: [{ value: "1", label: "Only my meetings" }] },
  ];

  const choose = (m: SharedMeeting, choice: "record" | "skip" | null) =>
    start(async () => {
      try {
        await setMeetingChoice(m.id, choice);
        toast.success(choice === "skip" ? "The notetaker will skip this meeting" : choice === "record" ? "The notetaker will join this meeting" : "Back to your usual settings");
        router.refresh();
      } catch (e) { toast.error(friendlyError(e, "Couldn't change that meeting")); }
    });

  return (
    <ClientDataView rows={meetings} defs={defs} defaultSort={DEFAULT_SORT} accessors={ACCESSORS} sortAccessors={SORTS}>
      {(rows) => {
        const days: [string, SharedMeeting[]][] = [];
        for (const m of rows) {
          const d = day(m.start_at);
          const last = days[days.length - 1];
          if (last && last[0] === d) last[1].push(m); else days.push([d, [m]]);
        }
        return (
          <DataViewLayout sidebar={<FilterSidebar title="Filter meetings" />}>
            <DataSearch />
            <FilterChips />
            {rows.length === 0 ? (
              <p className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
                {meetings.length ? "No meetings match these filters." : "No meetings in the next two weeks yet. Connect a calendar above - its meetings appear here within a few minutes."}
              </p>
            ) : days.map(([d, ms]) => (
              <section key={d} aria-label={d} className="rounded-xl border border-border/80 bg-card shadow-2xs">
                <h3 className="border-b border-border/70 px-4 py-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">{d}</h3>
                <ul className="divide-y divide-border/60">
                  {ms.map((m) => (
                    <li key={m.id} className="grid gap-2 px-4 py-3 sm:grid-cols-[6.5rem_1fr_auto] sm:items-start">
                      <div className="text-sm font-semibold tabular-nums">{m.is_all_day ? "All day" : `${hm(m.start_at)}–${hm(m.end_at)}`}</div>
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          {m.private && <Lock className="size-3.5 text-muted-foreground" aria-label="Private" />}
                          <span className="font-medium">{m.title}</span>
                          {m.platform && <span className="rounded-full border border-border px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">{PLATFORM_LABEL[m.platform] ?? m.platform}</span>}
                          {m.join_url && <a href={m.join_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 text-[11px] text-muted-foreground hover:underline">link <ExternalLink className="size-3" /></a>}
                        </div>
                        {!m.private && (
                          <div className="mt-0.5 text-[11px] text-muted-foreground">
                            {m.bmi_people.map((p) => `${p.name}${p.response === "declined" ? " (declined)" : p.response === "organizer" ? " (organiser)" : ""}`).join(", ")}
                            {m.outside_people.length > 0 && <> · with {m.outside_people.slice(0, 3).map((p) => p.name).join(", ")}{m.outside_people.length > 3 ? ` +${m.outside_people.length - 3}` : ""}</>}
                            {m.contact && <> · <Link href={`/contacts/${m.contact.id}`} target="_blank" rel="noreferrer" className="hover:underline">{m.contact.name}</Link></>}
                            {m.company && <> (<Link href={`/companies/${m.company.id}`} target="_blank" rel="noreferrer" className="hover:underline">{m.company.name}</Link>)</>}
                          </div>
                        )}
                        <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px]">
                          {m.call && m.call.status !== "cancelled" && !(m.call.status === "scheduled" && new Date(m.end_at).getTime() <= Date.now()) && (
                            <Link href={`/calls/${m.call.id}`} className="hover:opacity-80"><CallStatus status={m.call.status} label={m.call.status_label} /></Link>
                          )}
                          <span className="inline-flex items-start gap-1 font-semibold" style={{ color: TONE[m.outcome?.tone ?? "muted"] }}>
                            {m.outcome?.tone === "ok" || m.outcome?.tone === "live" ? <Bot className="mt-px size-3 shrink-0" /> : m.outcome?.tone === "bad" || m.outcome?.tone === "warn" ? <CircleAlert className="mt-px size-3 shrink-0" /> : <Ban className="mt-px size-3 shrink-0" />}
                            {m.outcome?.text ?? m.decision.reason}
                          </span>
                        </div>
                      </div>
                      {!m.private && new Date(m.end_at).getTime() > Date.now() && m.platform && !["Everyone at BMI declined", "No meeting link", "All-day event", "Zoom isn't set up on the notetaker yet"].includes(m.decision.reason) &&
                        !m.decision.reason.startsWith("Nobody from BMI in it has connected Zoom") &&
                        (!m.call || m.call.status === "scheduled" || m.call.status === "cancelled") && (
                        <div className="flex gap-1.5 sm:justify-end">
                          {m.decision.record ? (
                            <Button size="xs" variant="outline" disabled={pending} onClick={() => choose(m, "skip")}>Skip</Button>
                          ) : (
                            <Button size="xs" disabled={pending} onClick={() => choose(m, "record")} className="gap-1"><Bot className="size-3" /> Record</Button>
                          )}
                          {m.override && <Button size="xs" variant="ghost" disabled={pending} onClick={() => choose(m, null)}>Undo</Button>}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </DataViewLayout>
        );
      }}
    </ClientDataView>
  );
}
