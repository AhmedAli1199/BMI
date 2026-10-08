"use client";

import { useState, useTransition } from "react";
import { BellPlus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { createReminder } from "@/lib/messaging-actions";
import { friendlyError } from "@/lib/errors";

const PRESETS: { label: string; days?: number; months?: number }[] = [
  { label: "Tomorrow", days: 1 },
  { label: "In 3 days", days: 3 },
  { label: "1 week", days: 7 },
  { label: "2 weeks", days: 14 },
  { label: "1 month", months: 1 },
  { label: "3 months", months: 3 },
  { label: "6 months", months: 6 },
  { label: "1 year", months: 12 },
];

function pad(n: number) {
  return String(n).padStart(2, "0");
}

/** yyyy-MM-ddTHH:mm in local time, for <input type="datetime-local">. */
function toLocalInput(d: Date) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function presetDate(p: (typeof PRESETS)[number]) {
  const d = new Date();
  if (p.days) d.setDate(d.getDate() + p.days);
  if (p.months) d.setMonth(d.getMonth() + p.months);
  d.setHours(9, 0, 0, 0); // reminders land at the start of the working day
  return d;
}

/** "Remind me in…" for a contact or company. Fires as a notification
 * under the bell (and an email, if ticked) at the chosen time. */
export function RemindMeDialog({
  contactId,
  companyId,
  about,
  trigger,
}: {
  contactId?: string;
  companyId?: string;
  about: string;
  trigger?: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [pending, startTransition] = useTransition();
  const [preset, setPreset] = useState<string>("1 week");
  const [when, setWhen] = useState(() => toLocalInput(presetDate(PRESETS[2])));
  const [note, setNote] = useState("");
  const [emailMe, setEmailMe] = useState(true);

  function pick(p: (typeof PRESETS)[number]) {
    setPreset(p.label);
    setWhen(toLocalInput(presetDate(p)));
  }

  function save() {
    const due = new Date(when);
    if (Number.isNaN(due.getTime())) {
      toast.error("Pick a date and time");
      return;
    }
    startTransition(async () => {
      try {
        await createReminder({
          due_at: due.toISOString(),
          note: note.trim() || undefined,
          contact_id: contactId ?? null,
          company_id: companyId ?? null,
          email_me: emailMe,
        });
        toast.success(
          `Reminder set for ${due.toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}`
        );
        setOpen(false);
        setNote("");
      } catch (e) {
        toast.error(friendlyError(e, "Couldn't set the reminder"));
      }
    });
  }

  return (
    <>
      <span onClick={() => setOpen(true)} className="contents">
        {trigger ?? (
          <Button variant="outline" size="sm" className="gap-1.5">
            <BellPlus className="size-3.5" />
            Remind me
          </Button>
        )}
      </span>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Remind me about {about}</DialogTitle>
            <DialogDescription>
              You&apos;ll get a notification under the bell at this time{emailMe ? ", and an email" : ""}.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label>When</Label>
              <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label="Quick picks">
                {PRESETS.map((p) => (
                  <button
                    key={p.label}
                    type="button"
                    role="radio"
                    aria-checked={preset === p.label}
                    onClick={() => pick(p)}
                    className={`rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ${
                      preset === p.label
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border text-muted-foreground hover:bg-accent/50"
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
              <Input
                type="datetime-local"
                aria-label="Date and time"
                value={when}
                onChange={(e) => {
                  setWhen(e.target.value);
                  setPreset("");
                }}
                className="mt-1 h-9 text-sm"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="rm-note">What about? (optional)</Label>
              <Textarea
                id="rm-note"
                rows={3}
                value={note}
                placeholder="e.g. Follow up on the media pack for the spring issue"
                onChange={(e) => setNote(e.target.value)}
              />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="size-4 accent-primary"
                checked={emailMe}
                onChange={(e) => setEmailMe(e.target.checked)}
              />
              Email me as well
            </label>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={save} disabled={pending || !when}>
              {pending ? "Saving…" : "Set reminder"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
