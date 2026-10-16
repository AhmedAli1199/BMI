import Link from "next/link";
import { CalendarDays } from "lucide-react";
import { hiddenSections } from "@/lib/hidden-sections";

/** One place for "what's coming up": the shared calendar and to-dos, and your own reminders, as two tabs of
 * Calendar & Reminders (sidebar). Each tab is its own page, so links to either still work; a tab is left out when an
 * administrator has hidden that section for the person. `actions` sit on the right (search, Log or schedule). */
export async function CalendarRemindersHeader({ active, actions }: { active: "calendar" | "reminders"; actions?: React.ReactNode }) {
  const hidden = await hiddenSections();
  const tabs = [
    { key: "calendar", label: "Calendar & tasks", href: "/activities", show: !hidden.includes("calendar") },
    { key: "reminders", label: "Reminders", href: "/reminders", show: !hidden.includes("reminders") },
  ].filter((t) => t.show || t.key === active);
  return (
    <div className="flex flex-col gap-3 border-b border-border/80">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
            <CalendarDays className="size-3.5" aria-hidden="true" />
            <span>Calendar &amp; Reminders</span>
          </div>
          <h1 className="editorial-title text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            {active === "calendar" ? "Calendar & tasks" : "My reminders"}
          </h1>
          <p className="mt-1 text-xs text-muted-foreground sm:text-sm">
            {active === "calendar"
              ? "Calls, meetings and to-dos across your contacts and companies - yours and the team's."
              : <>Set one from any contact or company with <strong>Remind me</strong>. When it&apos;s due you get a notification under the bell - and an email, if you asked for one.</>}
          </p>
        </div>
        {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
      </div>
      {tabs.length > 1 && (
        <nav className="-mb-px flex gap-4" aria-label="Calendar and reminders">
          {tabs.map((t) => (
            <Link key={t.key} href={t.href} aria-current={t.key === active ? "page" : undefined}
              className={`border-b-2 px-1 pb-2 text-sm font-semibold transition-colors ${
                t.key === active ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"
              }`}>
              {t.label}
            </Link>
          ))}
        </nav>
      )}
    </div>
  );
}
