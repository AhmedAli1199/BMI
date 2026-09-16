"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Plus, Sparkles } from "lucide-react";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EntityPicker } from "@/components/entity-picker";
import {
  addContactNote,
  addCompanyNote,
  createActivity,
  logContactHistory,
  logCompanyHistory,
  searchCompanies,
  searchContacts,
} from "@/lib/actions";

type Mode = "log" | "schedule" | "note";

// Act!'s "History type" -> "Result" pairing (see backend's
// HISTORY_TYPES_KEPT) - picking a type narrows Result to what's actually
// valid for it, rather than showing all ~15 values at once.
const HISTORY_RESULTS: Record<string, string[]> = {
  Call: ["Call Attempted", "Call Completed", "Call Received", "Call Left Message"],
  Meeting: ["Meeting Held"],
  Email: ["E-mail Sent", "E-mail Not Sent"],
  Letter: ["Letter Sent"],
};

const ACTIVITY_TYPES = ["Call", "Meeting", "To-do"] as const;

function nowLocal(): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

type Target = { contactId?: string; companyId?: string; name: string; sourceDb: string };

/** One dialog for everything Act!'s Call/Meeting/Note/To-do buttons did
 * across four separate screens - a "what are you doing" tab switch instead,
 * so only the fields relevant to that choice ever show at once.
 *
 * Used two ways: pinned to a record (contactId/companyId/contactName/
 * sourceDb all passed in, no picker shown) or globally (global=true - the
 * user picks the contact/company as the first step). */
export function LogInteractionDialog({
  contactId,
  companyId,
  contactName,
  sourceDb,
  global = false,
  trigger,
}: {
  contactId?: string;
  companyId?: string;
  contactName?: string;
  sourceDb?: string;
  global?: boolean;
  trigger?: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [pending, startTransition] = useTransition();
  const router = useRouter();

  const [target, setTarget] = useState<Target | null>(
    contactId || companyId
      ? { contactId, companyId, name: contactName ?? "", sourceDb: sourceDb ?? "" }
      : null
  );

  const [mode, setMode] = useState<Mode>("log");

  // Log (History)
  const [historyType, setHistoryType] = useState("Call");
  const [result, setResult] = useState(HISTORY_RESULTS.Call[0]);
  const [logSubject, setLogSubject] = useState("");
  const [logDetails, setLogDetails] = useState("");
  const [duration, setDuration] = useState("10");
  const [occurredAt, setOccurredAt] = useState(nowLocal());
  const [logPrivate, setLogPrivate] = useState(false);

  // Schedule (Activity)
  const [activityType, setActivityType] = useState<(typeof ACTIVITY_TYPES)[number]>("Call");
  const [schedSubject, setSchedSubject] = useState("");
  const [schedDetails, setSchedDetails] = useState("");
  const [location, setLocation] = useState("");
  const [startAt, setStartAt] = useState(nowLocal());
  const [endAt, setEndAt] = useState("");
  const [isTimeless, setIsTimeless] = useState(false);
  const [recurrence, setRecurrence] = useState<"never" | "daily" | "weekly" | "monthly">("never");
  const [schedPrivate, setSchedPrivate] = useState(false);

  // Note
  const [noteBody, setNoteBody] = useState("");
  const [notePrivate, setNotePrivate] = useState(false);

  function resetAndClose() {
    setLogSubject("");
    setLogDetails("");
    setSchedSubject("");
    setSchedDetails("");
    setLocation("");
    setNoteBody("");
    setOpen(false);
    if (global) setTarget(null);
  }

  function submit() {
    if (!target) return;
    const { contactId: cid, companyId: coid } = target;

    startTransition(async () => {
      try {
        if (mode === "log") {
          const action = cid ? logContactHistory : logCompanyHistory;
          await action((cid ?? coid)!, {
            history_type: result,
            subject: logSubject || undefined,
            details: logDetails || undefined,
            duration_minutes: Number(duration) || undefined,
            is_private: logPrivate,
            occurred_at: new Date(occurredAt).toISOString(),
          });
          toast.success(`${historyType} logged`);
        } else if (mode === "schedule") {
          await createActivity({
            activity_type: activityType,
            subject: schedSubject || undefined,
            details: schedDetails || undefined,
            location: location || undefined,
            start_at: new Date(startAt).toISOString(),
            end_at: !isTimeless && endAt ? new Date(endAt).toISOString() : undefined,
            is_timeless: isTimeless,
            is_private: schedPrivate,
            recurrence,
            contact_id: cid ?? null,
            company_id: coid ?? null,
            source_db: target.sourceDb,
          });
          toast.success(`${activityType} scheduled`);
        } else {
          if (cid) await addContactNote(cid, noteBody, "Note", notePrivate);
          else await addCompanyNote(coid!, noteBody, notePrivate);
          toast.success("Note added");
        }
        resetAndClose();
        router.refresh();
      } catch {
        toast.error("Couldn't save that - try again");
      }
    });
  }

  const canSubmit =
    !!target &&
    (mode === "log"
      ? true
      : mode === "schedule"
        ? !!startAt
        : noteBody.trim().length > 0);

  return (
    <>
      {trigger ? (
        <span onClick={() => setOpen(true)}>{trigger}</span>
      ) : (
        <Button size="sm" onClick={() => setOpen(true)}>
          <Plus className="size-4" />
          Log or schedule
        </Button>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="size-4 text-primary" />
              {target ? `With ${target.name}` : "Log or schedule"}
            </DialogTitle>
            <DialogDescription>
              Something that already happened goes under Log. Something coming up goes under
              Schedule.
            </DialogDescription>
          </DialogHeader>

          {global && (
            <div className="flex flex-col gap-1.5">
              <Label>Contact or company</Label>
              <EntityPicker
                label="contact or company"
                placeholder="Search contacts or companies…"
                search={async (q) => {
                  const [contacts, companies] = await Promise.all([searchContacts(q), searchCompanies(q)]);
                  return [
                    ...contacts.map((c) => ({
                      id: `contact:${c.id}:${c.source_db}`,
                      label: c.full_name || [c.first_name, c.last_name].filter(Boolean).join(" ") || "(no name)",
                      sublabel: c.company_name ? `Contact · ${c.company_name}` : "Contact",
                    })),
                    ...companies.map((c) => ({
                      id: `company:${c.id}:${c.source_db}`,
                      label: c.name,
                      sublabel: "Company",
                    })),
                  ];
                }}
                value={target ? { id: "current", label: target.name } : null}
                onChange={(v) => {
                  if (!v) {
                    setTarget(null);
                    return;
                  }
                  const [kind, id, db] = v.id.split(":");
                  setTarget({
                    contactId: kind === "contact" ? id : undefined,
                    companyId: kind === "company" ? id : undefined,
                    name: v.label,
                    sourceDb: db,
                  });
                }}
              />
            </div>
          )}

          <Tabs value={mode} onValueChange={(v) => setMode(v as Mode)}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="log">Log</TabsTrigger>
              <TabsTrigger value="schedule">Schedule</TabsTrigger>
              <TabsTrigger value="note">Note</TabsTrigger>
            </TabsList>

            <TabsContent value="log" className="flex flex-col gap-3 pt-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1.5">
                  <Label>Type</Label>
                  <select
                    className="h-9 rounded-md border border-input bg-background px-2.5 text-sm"
                    value={historyType}
                    onChange={(e) => {
                      const t = e.target.value;
                      setHistoryType(t);
                      setResult(HISTORY_RESULTS[t][0]);
                    }}
                  >
                    {Object.keys(HISTORY_RESULTS).map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Result</Label>
                  <select
                    className="h-9 rounded-md border border-input bg-background px-2.5 text-sm"
                    value={result}
                    onChange={(e) => setResult(e.target.value)}
                  >
                    {HISTORY_RESULTS[historyType].map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="li-log-subject">Title</Label>
                <Input id="li-log-subject" value={logSubject} onChange={(e) => setLogSubject(e.target.value)} placeholder="What was it about?" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1.5">
                  <Label>Duration</Label>
                  <select
                    className="h-9 rounded-md border border-input bg-background px-2.5 text-sm"
                    value={duration}
                    onChange={(e) => setDuration(e.target.value)}
                  >
                    {["5", "10", "15", "30", "45", "60"].map((m) => (
                      <option key={m} value={m}>{m} minutes</option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="li-log-when">Date / time</Label>
                  <Input id="li-log-when" type="datetime-local" value={occurredAt} onChange={(e) => setOccurredAt(e.target.value)} />
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="li-log-details">Details</Label>
                <Textarea id="li-log-details" rows={3} value={logDetails} onChange={(e) => setLogDetails(e.target.value)} />
              </div>
              <PrivateCheckbox id="li-log-private" checked={logPrivate} onChange={setLogPrivate} />
            </TabsContent>

            <TabsContent value="schedule" className="flex flex-col gap-3 pt-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1.5">
                  <Label>Type</Label>
                  <select
                    className="h-9 rounded-md border border-input bg-background px-2.5 text-sm"
                    value={activityType}
                    onChange={(e) => setActivityType(e.target.value as (typeof ACTIVITY_TYPES)[number])}
                  >
                    {ACTIVITY_TYPES.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Repeats</Label>
                  <select
                    className="h-9 rounded-md border border-input bg-background px-2.5 text-sm"
                    value={recurrence}
                    onChange={(e) => setRecurrence(e.target.value as typeof recurrence)}
                  >
                    <option value="never">Never</option>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="li-sched-subject">Title</Label>
                <Input id="li-sched-subject" value={schedSubject} onChange={(e) => setSchedSubject(e.target.value)} />
              </div>
              {activityType === "Meeting" && (
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="li-sched-location">Location</Label>
                  <Input id="li-sched-location" value={location} onChange={(e) => setLocation(e.target.value)} />
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="li-sched-start">Start</Label>
                  <Input id="li-sched-start" type="datetime-local" value={startAt} onChange={(e) => setStartAt(e.target.value)} />
                </div>
                {!isTimeless && (
                  <div className="flex flex-col gap-1.5">
                    <Label htmlFor="li-sched-end">End</Label>
                    <Input id="li-sched-end" type="datetime-local" value={endAt} onChange={(e) => setEndAt(e.target.value)} />
                  </div>
                )}
              </div>
              {activityType === "To-do" && (
                <label className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <input type="checkbox" checked={isTimeless} onChange={(e) => setIsTimeless(e.target.checked)} className="size-3.5" />
                  Timeless (no specific time, just a date)
                </label>
              )}
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="li-sched-details">Details</Label>
                <Textarea id="li-sched-details" rows={3} value={schedDetails} onChange={(e) => setSchedDetails(e.target.value)} />
              </div>
              <PrivateCheckbox id="li-sched-private" checked={schedPrivate} onChange={setSchedPrivate} />
            </TabsContent>

            <TabsContent value="note" className="flex flex-col gap-3 pt-3">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="li-note-body">Note</Label>
                <Textarea id="li-note-body" rows={5} value={noteBody} onChange={(e) => setNoteBody(e.target.value)} autoFocus />
              </div>
              <PrivateCheckbox id="li-note-private" checked={notePrivate} onChange={setNotePrivate} />
            </TabsContent>
          </Tabs>

          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={submit} disabled={pending || !canSubmit}>
              {pending ? "Saving…" : mode === "schedule" ? "Schedule" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

function PrivateCheckbox({ id, checked, onChange }: { id: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label htmlFor={id} className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
      <input id={id} type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="size-3.5" />
      Make this private
    </label>
  );
}
