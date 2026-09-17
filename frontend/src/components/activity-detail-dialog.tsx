"use client";

import Link from "next/link";
import { Calendar, Lock, MapPin, PhoneCall, CheckSquare, Clock, Paperclip, User } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { ActivityDoneToggle } from "@/components/activity-done-toggle";
import type { ActivityOut } from "@/lib/types";

function typeIcon(type: string | null) {
  const t = (type || "").toLowerCase();
  if (t.includes("call")) return <PhoneCall className="size-4 text-amber-600 dark:text-amber-400" />;
  if (t.includes("meet")) return <Calendar className="size-4 text-blue-600 dark:text-blue-400" />;
  return <CheckSquare className="size-4 text-rose-600 dark:text-rose-400" />;
}

function formatDuration(mins?: number | null): string | null {
  if (!mins || mins <= 0) return null;
  if (mins < 60) return `${mins} min${mins === 1 ? "" : "s"}`;
  const hrs = Math.floor(mins / 60);
  const remainingMins = mins % 60;
  if (remainingMins === 0) return `${hrs} hr${hrs === 1 ? "" : "s"}`;
  return `${hrs} hr ${remainingMins} min`;
}

function formatDateTime(iso: string, isTimeless: boolean): string {
  const d = new Date(iso);
  const datePart = d.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  if (isTimeless) return datePart;
  const timePart = d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  return `${datePart} at ${timePart}`;
}

export function ActivityDetailDialog({
  item,
  children,
}: {
  item: ActivityOut;
  children: React.ReactNode;
}) {
  const priority = (item.priority || "normal").toLowerCase();
  const priorityColor =
    priority === "high"
      ? "border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-400"
      : priority === "low"
        ? "border-blue-500/40 bg-blue-500/10 text-blue-700 dark:text-blue-400"
        : "border-border bg-muted/50 text-muted-foreground";

  const durationStr = formatDuration(item.duration_minutes);

  return (
    <Dialog>
      <DialogTrigger render={<button type="button" className="contents text-left" />}>
        {children}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            {typeIcon(item.activity_type)}
            <DialogTitle className="text-base">{item.subject || item.activity_type || "Activity"}</DialogTitle>
          </div>
        </DialogHeader>

        <div className="flex flex-col gap-3 text-sm">
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="outline" className="text-xs">{item.activity_type}</Badge>
            <Badge variant="outline" className={`text-xs capitalize font-medium ${priorityColor}`}>
              {priority} Priority
            </Badge>
            {item.is_cleared && (
              <Badge variant="outline" className="text-xs border-[var(--ok)] text-[var(--ok)]">
                Done
              </Badge>
            )}
            {item.has_attachments && (
              <Badge variant="outline" className="text-xs gap-1 border-primary/40 text-primary">
                <Paperclip className="size-2.5" /> Attachment
              </Badge>
            )}
            {item.is_private && (
              <Badge variant="outline" className="text-xs gap-1">
                <Lock className="size-2.5" /> Private
              </Badge>
            )}
            {item.recurrence !== "never" && (
              <Badge variant="outline" className="text-xs capitalize">{item.recurrence}</Badge>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-3 text-muted-foreground text-xs sm:text-sm">
            <span>
              {formatDateTime(item.start_at, item.is_timeless)}
              {item.end_at && !item.is_timeless && (
                <> &ndash; {new Date(item.end_at).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}</>
              )}
            </span>
            {durationStr && (
              <span className="inline-flex items-center gap-1 font-mono text-xs">
                <Clock className="size-3" /> {durationStr}
              </span>
            )}
          </div>

          {item.location && (
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <MapPin className="size-3.5 shrink-0" />
              <span>{item.location}</span>
            </div>
          )}

          {(item.contact_name || item.company_name) && (
            <div className="grid grid-cols-2 gap-2 rounded-md border border-border/80 bg-muted/20 p-2.5">
              {item.contact_name && (
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Contact</span>
                  <div className="mt-0.5">
                    {item.contact_id ? (
                      <Link href={`/contacts/${item.contact_id}`} className="font-semibold text-primary hover:underline text-xs">
                        {item.contact_name}
                      </Link>
                    ) : (
                      <span className="font-medium text-xs">{item.contact_name}</span>
                    )}
                  </div>
                </div>
              )}
              {item.company_name && (
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Company</span>
                  <div className="mt-0.5">
                    {item.company_id ? (
                      <Link href={`/companies/${item.company_id}`} className="font-semibold text-primary hover:underline text-xs">
                        {item.company_name}
                      </Link>
                    ) : (
                      <span className="font-medium text-xs">{item.company_name}</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {item.details && (
            <div>
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Details</span>
              <p className="mt-0.5 whitespace-pre-wrap leading-relaxed text-xs sm:text-sm">{item.details}</p>
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground border-t pt-2">
            {(item.organized_by_name || item.created_by?.name) && (
              <div className="flex items-center gap-1">
                <User className="size-3 text-muted-foreground" />
                <span>Organized by {item.organized_by_name || item.created_by?.name}</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 border-t pt-3">
            <ActivityDoneToggle
              id={item.id}
              isCleared={item.is_cleared}
              contactId={item.contact_id}
              companyId={item.company_id}
            />
            <span className="text-xs text-muted-foreground">
              {item.is_cleared ? "Marked done" : "Mark as done"}
            </span>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
