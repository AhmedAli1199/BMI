"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import {
  Calendar as CalendarIcon,
  PhoneCall,
  CheckSquare,
  Clock,
  MapPin,
  Paperclip,
  Lock,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  User,
  Building2,
  ExternalLink,
} from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { ActivityDoneToggle } from "@/components/activity-done-toggle";
import { ActivityDetailDialog } from "@/components/activity-detail-dialog";
import type { ActivityOut } from "@/lib/types";

type SortField = "date" | "priority" | "type" | "subject" | "contact" | "company" | "duration";
type SortDirection = "asc" | "desc";

function typeIcon(type: string | null) {
  const t = (type || "").toLowerCase();
  if (t.includes("call")) return <PhoneCall className="size-3.5 text-amber-600 dark:text-amber-400 shrink-0" />;
  if (t.includes("meet")) return <CalendarIcon className="size-3.5 text-blue-600 dark:text-blue-400 shrink-0" />;
  return <CheckSquare className="size-3.5 text-rose-600 dark:text-rose-400 shrink-0" />;
}

function formatDuration(mins?: number | null): string {
  if (!mins || mins <= 0) return "—";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  const remainingMins = mins % 60;
  if (remainingMins === 0) return `${hrs}h`;
  return `${hrs}h ${remainingMins}m`;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

function formatTime(iso: string, isTimeless: boolean): string {
  if (isTimeless) return "Timeless";
  const d = new Date(iso);
  return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

function isOverdue(iso: string, isCleared: boolean): boolean {
  if (isCleared) return false;
  const d = new Date(iso);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return d.getTime() < today.getTime();
}

function priorityWeight(p?: string): number {
  const priority = (p || "normal").toLowerCase();
  if (priority === "high") return 3;
  if (priority === "normal") return 2;
  return 1;
}

export function InteractiveActivityTable({ items }: { items: ActivityOut[] }) {
  const [sortField, setSortField] = useState<SortField>("date");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  const sortedItems = useMemo(() => {
    return [...items].sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case "date":
          cmp = new Date(a.start_at).getTime() - new Date(b.start_at).getTime();
          break;
        case "priority":
          cmp = priorityWeight(b.priority) - priorityWeight(a.priority);
          break;
        case "type":
          cmp = (a.activity_type || "").localeCompare(b.activity_type || "");
          break;
        case "subject":
          cmp = (a.subject || "").localeCompare(b.subject || "");
          break;
        case "contact":
          cmp = (a.contact_name || "").localeCompare(b.contact_name || "");
          break;
        case "company":
          cmp = (a.company_name || "").localeCompare(b.company_name || "");
          break;
        case "duration":
          cmp = (a.duration_minutes || 0) - (b.duration_minutes || 0);
          break;
      }
      return sortDirection === "asc" ? cmp : -cmp;
    });
  }, [items, sortField, sortDirection]);

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <ArrowUpDown className="ml-1 size-3 opacity-40 group-hover:opacity-100" />;
    }
    return sortDirection === "asc" ? (
      <ArrowUp className="ml-1 size-3 text-primary" />
    ) : (
      <ArrowDown className="ml-1 size-3 text-primary" />
    );
  };

  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border/80 p-12 text-center text-sm text-muted-foreground bg-card">
        <CheckSquare className="mx-auto mb-2 size-8 opacity-40" />
        <p className="font-semibold text-foreground">No activities found</p>
        <p className="text-xs mt-1">There are no calls, meetings or to-dos matching your current filters.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-card shadow-2xs">
      <Table className="w-full text-xs">
        <TableHeader className="bg-muted/50 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground select-none">
          <TableRow className="hover:bg-transparent border-b border-border/80">
            <TableHead className="w-10 px-3 py-3 text-center">Done</TableHead>
            <TableHead
              className="w-24 cursor-pointer py-3 hover:text-foreground group"
              onClick={() => handleSort("type")}
            >
              <div className="flex items-center">
                <span>Type</span>
                <SortIcon field="type" />
              </div>
            </TableHead>
            <TableHead
              className="w-28 cursor-pointer py-3 hover:text-foreground group"
              onClick={() => handleSort("date")}
            >
              <div className="flex items-center">
                <span>Date</span>
                <SortIcon field="date" />
              </div>
            </TableHead>
            <TableHead className="w-20 py-3">Time</TableHead>
            <TableHead
              className="w-20 cursor-pointer py-3 hover:text-foreground group"
              onClick={() => handleSort("priority")}
            >
              <div className="flex items-center">
                <span>Priority</span>
                <SortIcon field="priority" />
              </div>
            </TableHead>
            <TableHead
              className="min-w-[240px] cursor-pointer py-3 hover:text-foreground group"
              onClick={() => handleSort("subject")}
            >
              <div className="flex items-center">
                <span>Regarding / Details</span>
                <SortIcon field="subject" />
              </div>
            </TableHead>
            <TableHead
              className="w-36 cursor-pointer py-3 hover:text-foreground group"
              onClick={() => handleSort("contact")}
            >
              <div className="flex items-center">
                <span>Contact</span>
                <SortIcon field="contact" />
              </div>
            </TableHead>
            <TableHead
              className="w-36 cursor-pointer py-3 hover:text-foreground group"
              onClick={() => handleSort("company")}
            >
              <div className="flex items-center">
                <span>Company</span>
                <SortIcon field="company" />
              </div>
            </TableHead>
            <TableHead
              className="w-20 cursor-pointer py-3 hover:text-foreground group"
              onClick={() => handleSort("duration")}
            >
              <div className="flex items-center">
                <span>Duration</span>
                <SortIcon field="duration" />
              </div>
            </TableHead>
            <TableHead className="w-28 py-3">Location</TableHead>
            <TableHead className="w-10 px-2 py-3 text-center" title="Attachments">
              <Paperclip className="mx-auto size-3 opacity-60" />
            </TableHead>
            <TableHead className="w-32 py-3">Scheduled For</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedItems.map((item) => {
            const overdue = isOverdue(item.start_at, item.is_cleared);
            const priority = (item.priority || "normal").toLowerCase();
            const priorityBadge =
              priority === "high" ? (
                <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-red-500/15 text-red-700 dark:text-red-400 border border-red-500/30">
                  High
                </span>
              ) : priority === "low" ? (
                <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                  Low
                </span>
              ) : (
                <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground bg-muted/60">
                  Normal
                </span>
              );

            const organizer = item.organized_by_name || item.created_by?.name || "—";

            return (
              <TableRow
                key={item.id}
                className={`group border-b border-border/60 transition-colors hover:bg-accent/40 ${
                  item.is_cleared ? "opacity-60 bg-muted/10" : overdue ? "bg-red-500/5" : ""
                }`}
              >
                {/* 1. Done Checkbox */}
                <TableCell className="px-3 py-2.5 text-center">
                  <ActivityDoneToggle
                    id={item.id}
                    isCleared={item.is_cleared}
                    contactId={item.contact_id}
                    companyId={item.company_id}
                  />
                </TableCell>

                {/* 2. Type */}
                <TableCell className="py-2.5">
                  <div className="flex items-center gap-1.5 whitespace-nowrap">
                    {typeIcon(item.activity_type)}
                    <span className="font-medium text-foreground">{item.activity_type || "Activity"}</span>
                  </div>
                </TableCell>

                {/* 3. Date */}
                <TableCell className="py-2.5 whitespace-nowrap">
                  <div className="flex flex-col">
                    <span className={`font-mono text-xs ${overdue ? "font-semibold text-red-600 dark:text-red-400" : "text-foreground"}`}>
                      {formatDate(item.start_at)}
                    </span>
                    {overdue && (
                      <span className="text-[10px] font-bold uppercase tracking-tight text-red-600 dark:text-red-400">
                        Overdue
                      </span>
                    )}
                  </div>
                </TableCell>

                {/* 4. Time */}
                <TableCell className="py-2.5 whitespace-nowrap">
                  <span className="font-mono text-[11px] text-muted-foreground">
                    {formatTime(item.start_at, item.is_timeless)}
                  </span>
                </TableCell>

                {/* 5. Priority */}
                <TableCell className="py-2.5 whitespace-nowrap">{priorityBadge}</TableCell>

                {/* 6. Regarding / Subject (Clickable to open dialog) */}
                <TableCell className="py-2.5">
                  <ActivityDetailDialog item={item}>
                    <div className="group/title flex flex-col gap-0.5 max-w-[340px] text-left cursor-pointer">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`font-semibold transition-colors group-hover/title:text-primary truncate ${
                            item.is_cleared ? "line-through text-muted-foreground" : "text-foreground"
                          }`}
                        >
                          {item.subject || item.activity_type || "Untitled Activity"}
                        </span>
                        {item.is_private && <Lock className="size-2.5 text-muted-foreground shrink-0" />}
                      </div>
                      {item.details && (
                        <p className="truncate text-[11px] text-muted-foreground leading-tight">
                          {item.details}
                        </p>
                      )}
                    </div>
                  </ActivityDetailDialog>
                </TableCell>

                {/* 7. Contact Link */}
                <TableCell className="py-2.5 whitespace-nowrap">
                  {item.contact_name ? (
                    item.contact_id ? (
                      <Link
                        href={`/contacts/${item.contact_id}`}
                        className="inline-flex items-center gap-1 font-medium text-primary hover:underline"
                        title={item.contact_name}
                      >
                        <User className="size-3 opacity-60 shrink-0" />
                        <span className="truncate max-w-[120px]">{item.contact_name}</span>
                      </Link>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-muted-foreground">
                        <User className="size-3 opacity-40 shrink-0" />
                        <span className="truncate max-w-[120px]">{item.contact_name}</span>
                      </span>
                    )
                  ) : (
                    <span className="text-muted-foreground/40">—</span>
                  )}
                </TableCell>

                {/* 8. Company Link */}
                <TableCell className="py-2.5 whitespace-nowrap">
                  {item.company_name ? (
                    item.company_id ? (
                      <Link
                        href={`/companies/${item.company_id}`}
                        className="inline-flex items-center gap-1 font-medium text-primary hover:underline"
                        title={item.company_name}
                      >
                        <Building2 className="size-3 opacity-60 shrink-0" />
                        <span className="truncate max-w-[120px]">{item.company_name}</span>
                      </Link>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-muted-foreground">
                        <Building2 className="size-3 opacity-40 shrink-0" />
                        <span className="truncate max-w-[120px]">{item.company_name}</span>
                      </span>
                    )
                  ) : (
                    <span className="text-muted-foreground/40">—</span>
                  )}
                </TableCell>

                {/* 9. Duration */}
                <TableCell className="py-2.5 whitespace-nowrap font-mono text-[11px] text-muted-foreground">
                  {formatDuration(item.duration_minutes)}
                </TableCell>

                {/* 10. Location */}
                <TableCell className="py-2.5">
                  {item.location ? (
                    <div className="flex items-center gap-1 text-muted-foreground max-w-[120px] truncate" title={item.location}>
                      <MapPin className="size-3 opacity-60 shrink-0" />
                      <span className="truncate">{item.location}</span>
                    </div>
                  ) : (
                    <span className="text-muted-foreground/40">—</span>
                  )}
                </TableCell>

                {/* 11. Attachments indicator */}
                <TableCell className="py-2.5 px-2 text-center whitespace-nowrap">
                  {item.has_attachments ? (
                    <span title="Has attached files" className="inline-flex items-center justify-center">
                      <Paperclip className="size-3.5 text-primary" />
                    </span>
                  ) : (
                    <span className="text-muted-foreground/30 text-[10px]">—</span>
                  )}
                </TableCell>

                {/* 12. Scheduled For / Organizer */}
                <TableCell className="py-2.5 whitespace-nowrap">
                  <span className="text-xs text-muted-foreground truncate max-w-[120px]" title={organizer}>
                    {organizer}
                  </span>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
