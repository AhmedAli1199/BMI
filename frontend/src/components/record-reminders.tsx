import Link from "next/link";
import { BellRing } from "lucide-react";
import type { Reminder } from "@/lib/messaging-types";
import { ReminderDoneButton } from "@/components/reminder-row-actions";

/** Request time - module-level so render stays pure. */
function nowMs() {
  return Date.now();
}

/** "Your reminders about this record" - a small strip on contact and
 * company pages, only when there are some. */
export function RecordReminders({ reminders }: { reminders: Reminder[] }) {
  if (reminders.length === 0) return null;
  return (
    <div className="flex flex-col gap-1.5 rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2">
      {reminders.map((r) => {
        const due = new Date(r.due_at);
        const overdue = due.getTime() < nowMs();
        return (
          <div key={r.id} className="flex flex-wrap items-center gap-2 text-sm">
            <BellRing className={`size-4 shrink-0 ${overdue ? "text-destructive" : "text-amber-600"}`} />
            <span className={`font-medium ${overdue ? "text-destructive" : ""}`}>
              {due.toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
            </span>
            <span className="min-w-0 flex-1 truncate text-muted-foreground">{r.note || "Reminder"}</span>
            <ReminderDoneButton id={r.id} />
          </div>
        );
      })}
      <Link href="/reminders" className="self-end text-[11px] font-medium text-primary hover:underline">
        All my reminders →
      </Link>
    </div>
  );
}
