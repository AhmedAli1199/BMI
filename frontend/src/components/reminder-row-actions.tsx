"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { Check, Clock, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { deleteReminder, updateReminder } from "@/lib/messaging-actions";

export function ReminderDoneButton({ id }: { id: string }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  return (
    <Button
      size="sm"
      variant="ghost"
      className="h-7 gap-1 text-xs"
      disabled={pending}
      onClick={() =>
        start(async () => {
          try {
            await updateReminder(id, { status: "done" });
            toast.success("Reminder done");
            router.refresh();
          } catch (e) {
            toast.error(e instanceof Error ? e.message : "Couldn't update the reminder");
          }
        })
      }
    >
      <Check className="size-3.5" />
      Done
    </Button>
  );
}

const SNOOZE: { label: string; hours: number }[] = [
  { label: "1 hour", hours: 1 },
  { label: "Tomorrow morning", hours: -1 },
  { label: "1 week", hours: 24 * 7 },
  { label: "1 month", hours: 24 * 30 },
];

export function ReminderRowActions({ id, status }: { id: string; status: string }) {
  const router = useRouter();
  const [pending, start] = useTransition();

  function run(fn: () => Promise<unknown>, ok: string) {
    start(async () => {
      try {
        await fn();
        toast.success(ok);
        router.refresh();
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Something went wrong");
      }
    });
  }

  function snooze(hours: number) {
    const d = new Date();
    if (hours < 0) {
      d.setDate(d.getDate() + 1);
      d.setHours(9, 0, 0, 0);
    } else {
      d.setTime(d.getTime() + hours * 3600_000);
    }
    run(() => updateReminder(id, { due_at: d.toISOString() }), "Snoozed");
  }

  return (
    <div className="flex items-center justify-end gap-1">
      {status === "open" ? (
        <>
          <Button size="sm" variant="outline" className="h-7 gap-1 text-xs" disabled={pending}
            onClick={() => run(() => updateReminder(id, { status: "done" }), "Marked done")}>
            <Check className="size-3.5" />
            Done
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger
              render={
                <Button size="sm" variant="ghost" className="h-7 gap-1 text-xs" disabled={pending}>
                  <Clock className="size-3.5" />
                  Snooze
                </Button>
              }
            />
            <DropdownMenuContent align="end">
              {SNOOZE.map((s) => (
                <DropdownMenuItem key={s.label} onClick={() => snooze(s.hours)}>
                  {s.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </>
      ) : (
        <Button size="sm" variant="ghost" className="h-7 text-xs" disabled={pending}
          onClick={() => run(() => updateReminder(id, { status: "open" }), "Reopened")}>
          Reopen
        </Button>
      )}
      <Button size="sm" variant="ghost" className="h-7 text-muted-foreground" disabled={pending} aria-label="Delete reminder"
        onClick={() => run(() => deleteReminder(id), "Deleted")}>
        <Trash2 className="size-3.5" />
      </Button>
    </div>
  );
}
