import Link from "next/link";
import { AlarmClock, Building2, User } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { Reminder } from "@/lib/messaging-types";
import { ReminderRowActions } from "@/components/reminder-row-actions";
import { CalendarRemindersHeader } from "@/components/calendar-reminders-header";
import { EmptyState } from "@/components/empty-state";

/** Request time - module-level so render stays pure. */
function nowMs() {
  return Date.now();
}

const TABS = [
  { key: "open", label: "Upcoming" },
  { key: "done", label: "Done" },
  { key: "all", label: "All" },
] as const;

function fmt(iso: string) {
  return new Date(iso).toLocaleString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default async function RemindersPage({ searchParams }: { searchParams: Promise<{ status?: string }> }) {
  const { status: raw } = await searchParams;
  const status = TABS.some((t) => t.key === raw) ? raw! : "open";
  const reminders = await backendFetch<Reminder[]>(`/api/reminders?status=${status}`).catch(() => [] as Reminder[]);
  const now = nowMs();
  const overdue = reminders.filter((r) => r.status === "open" && new Date(r.due_at).getTime() <= now);
  const upcoming = reminders.filter((r) => !(r.status === "open" && new Date(r.due_at).getTime() <= now));

  const Row = ({ r }: { r: Reminder }) => {
    const Icon = r.contact_id ? User : r.company_id ? Building2 : AlarmClock;
    const isOverdue = r.status === "open" && new Date(r.due_at).getTime() <= now;
    return (
      <li className="flex flex-wrap items-center gap-3 px-4 py-3 sm:flex-nowrap">
        <div className="w-44 shrink-0">
          <div className={`text-sm font-semibold ${isOverdue ? "text-destructive" : ""}`}>{fmt(r.due_at)}</div>
          <div className="text-[11px] text-muted-foreground">
            {r.status === "done" ? "Done" : r.notified_at ? "Notified" : "Scheduled"}
            {r.email_me ? " · email too" : " · in-app only"}
          </div>
        </div>
        <div className="min-w-0 flex-1">
          {r.about ? (
            <Link href={r.link ?? "#"} className="flex items-center gap-1.5 text-sm font-medium hover:text-primary">
              <Icon className="size-3.5 shrink-0 text-muted-foreground" />
              <span className="truncate">{r.about}</span>
            </Link>
          ) : (
            <span className="text-sm font-medium">Reminder</span>
          )}
          {r.note && <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{r.note}</p>}
        </div>
        <ReminderRowActions id={r.id} status={r.status} />
      </li>
    );
  };

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6">
      <CalendarRemindersHeader active="reminders" />

      <nav className="flex gap-1" aria-label="Filter reminders">
        {TABS.map((t) => (
          <Link
            key={t.key}
            href={`/reminders?status=${t.key}`}
            aria-current={status === t.key ? "page" : undefined}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              status === t.key ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-accent"
            }`}
          >
            {t.label}
          </Link>
        ))}
      </nav>

      {reminders.length === 0 ? (
        <EmptyState title={status === "open" ? "No upcoming reminders" : "Nothing here yet"}>
          Press <strong>Remind me</strong> on any contact or company, and it shows up here when it&apos;s due.
        </EmptyState>
      ) : (
        <>
          {overdue.length > 0 && (
            <section className="flex flex-col gap-2">
              <h2 className="text-xs font-bold uppercase tracking-wider text-destructive">Due now ({overdue.length})</h2>
              <ul className="divide-y divide-border rounded-lg border border-destructive/30 bg-card shadow-2xs">
                {overdue.map((r) => <Row key={r.id} r={r} />)}
              </ul>
            </section>
          )}
          {upcoming.length > 0 && (
            <section className="flex flex-col gap-2">
              {overdue.length > 0 && (
                <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Later</h2>
              )}
              <ul className="divide-y divide-border rounded-lg border border-border bg-card shadow-2xs">
                {upcoming.map((r) => <Row key={r.id} r={r} />)}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}
