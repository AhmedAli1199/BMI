"use client";

import Link from "next/link";
import { Calendar, Lock, MapPin, PhoneCall, CheckSquare } from "lucide-react";
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
  const who = item.contact_name || item.company_name;
  const link = item.contact_id
    ? `/contacts/${item.contact_id}`
    : item.company_id
      ? `/companies/${item.company_id}`
      : null;

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
            {item.is_cleared && (
              <Badge variant="outline" className="text-xs border-[var(--ok)] text-[var(--ok)]">
                Done
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

          <div className="text-muted-foreground">
            {formatDateTime(item.start_at, item.is_timeless)}
            {item.end_at && !item.is_timeless && (
              <> &ndash; {new Date(item.end_at).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}</>
            )}
          </div>

          {item.location && (
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <MapPin className="size-3.5 shrink-0" />
              <span>{item.location}</span>
            </div>
          )}

          {who && (
            <div>
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Linked to</span>
              <div className="mt-0.5">
                {link ? (
                  <Link href={link} className="font-medium text-primary hover:underline">
                    {who}
                  </Link>
                ) : (
                  <span className="font-medium">{who}</span>
                )}
              </div>
            </div>
          )}

          {item.details && (
            <div>
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Details</span>
              <p className="mt-0.5 whitespace-pre-wrap leading-relaxed">{item.details}</p>
            </div>
          )}

          {item.created_by && (
            <div className="text-xs text-muted-foreground">Logged by {item.created_by.name}</div>
          )}

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
