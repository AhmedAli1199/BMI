"use client";

import { useState } from "react";
import {
  Calendar,
  CheckSquare,
  FileText,
  Mail,
  MessageSquare,
  PhoneCall,
  Sparkles,
} from "lucide-react";
import type { NoteOut, HistoryOut, ActivityOut } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { cleanNoteBody } from "@/lib/notes";
import { highlightMatch } from "@/lib/highlight";
import { DeleteItemButton } from "@/components/delete-item-button";
import {
  deleteContactNote, deleteCompanyNote,
  deleteContactHistory, deleteCompanyHistory,
  deleteActivity,
} from "@/lib/actions";

type TimelineItem = {
  id: string;
  rawId: string;
  kind: "note" | "history" | "activity";
  date: Date;
  isoString: string;
  category: "call" | "meeting" | "email" | "note" | "task" | "system";
  title: string;
  body?: string | null;
  badgeLabel?: string;
  isScheduled?: boolean;
  isCleared?: boolean;
};

function isFuture(date: Date): boolean {
  return date.getTime() > Date.now();
}

function formatRelativeTime(date: Date): string {
  const diffMs = Date.now() - date.getTime();
  if (diffMs < 0) return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "Yesterday";
  if (days < 30) return `${days}d ago`;
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function categorizeItem(typeStr: string | null, text: string | null): "call" | "meeting" | "email" | "note" | "task" | "system" {
  const lower = `${typeStr || ""} ${text || ""}`.toLowerCase();
  if (lower.includes("to-do") || lower.includes("todo") || lower.includes("task")) return "task";
  if (lower.includes("call") || lower.includes("phone") || lower.includes("reach") || lower.includes("attempt")) return "call";
  if (lower.includes("meet") || lower.includes("tasting") || lower.includes("visit") || lower.includes("expo")) return "meeting";
  if (lower.includes("mail") || lower.includes("letter") || lower.includes("message")) return "email";
  if (lower.includes("note") || lower.includes("brief") || lower.includes("contract")) return "note";
  return "system";
}

export function UnifiedActivityTimeline({
  notes = [],
  history = [],
  activities = [],
  searchTerm = "",
  entityType,
  entityId,
}: {
  notes: NoteOut[];
  history: HistoryOut[];
  activities?: ActivityOut[];
  /** When set, narrows to items whose title/body matches (case-insensitive)
   * and highlights the matched text - the same term driving the Notes and
   * History tabs, so this timeline stays in sync with them rather than
   * needing its own separate search box. */
  searchTerm?: string;
  /** Which record this timeline belongs to - which delete endpoint a note/
   * history row's delete button calls (a note and a history entry are
   * each owned by exactly one contact or company, see backend's
   * delete_entity_row). Omit to render the timeline read-only (no delete
   * buttons) - not currently used anywhere, but keeps this component
   * usable for a future read-only context without a required prop. */
  entityType?: "contact" | "company";
  entityId?: string;
}) {
  const [filter, setFilter] = useState<"all" | "call" | "meeting" | "note" | "email" | "task">("all");

  const timelineItems: TimelineItem[] = [
    ...notes.map((n): TimelineItem => {
      const d = n.act_created_at ? new Date(n.act_created_at) : new Date();
      return {
        id: `note-${n.id}`,
        rawId: n.id,
        kind: "note",
        date: d,
        isoString: d.toISOString(),
        category: categorizeItem(n.note_type, n.body),
        title: n.note_type || "Note",
        body: cleanNoteBody(n.body),
        badgeLabel: n.note_type || "Note",
      };
    }),
    ...history.map((h): TimelineItem => {
      const d = new Date(h.occurred_at);
      return {
        id: `hist-${h.id}`,
        rawId: h.id,
        kind: "history",
        date: d,
        isoString: d.toISOString(),
        category: categorizeItem(h.history_type, h.subject),
        title: h.subject || h.history_type,
        body: h.details ? cleanNoteBody(h.details) : null,
        badgeLabel: h.history_type,
      };
    }),
    ...activities.map((a): TimelineItem => {
      const d = new Date(a.start_at);
      return {
        id: `act-${a.id}`,
        rawId: a.id,
        kind: "activity",
        date: d,
        isoString: d.toISOString(),
        category: categorizeItem(a.activity_type, a.subject),
        title: a.subject || a.activity_type || "Activity",
        body: a.details ? cleanNoteBody(a.details) : null,
        badgeLabel: a.activity_type ?? undefined,
        isScheduled: true,
        isCleared: a.is_cleared,
      };
    }),
  ].sort((a, b) => b.date.getTime() - a.date.getTime());

  const needle = searchTerm.trim().toLowerCase();
  const filteredItems = timelineItems.filter((item) => {
    if (filter !== "all" && item.category !== filter) return false;
    if (!needle) return true;
    return (
      item.title.toLowerCase().includes(needle) ||
      (item.body?.toLowerCase().includes(needle) ?? false) ||
      (item.badgeLabel?.toLowerCase().includes(needle) ?? false)
    );
  });

  const getIcon = (category: string) => {
    switch (category) {
      case "call":
        return <PhoneCall className="size-3.5 text-[#c9611e]" />;
      case "meeting":
        return <Calendar className="size-3.5 text-[#0099e5]" />;
      case "email":
        return <Mail className="size-3.5 text-[#5b3e8f]" />;
      case "note":
        return <FileText className="size-3.5 text-[#1e7a52]" />;
      case "task":
        return <CheckSquare className="size-3.5 text-[#c0392b]" />;
      default:
        return <Sparkles className="size-3.5 text-primary" />;
    }
  };

  /** Which delete action a given item's button should call - None when
   * this timeline has no entityType/entityId (read-only mode) or for a
   * kind this component can't attribute to a single contact/company
   * (there isn't one today, but keeps the switch exhaustive-safe). */
  function deleteHandlerFor(item: TimelineItem): (() => Promise<void>) | null {
    if (!entityType || !entityId) return null;
    if (item.kind === "note") {
      return () => (entityType === "contact" ? deleteContactNote(entityId, item.rawId) : deleteCompanyNote(entityId, item.rawId));
    }
    if (item.kind === "history") {
      return () => (entityType === "contact" ? deleteContactHistory(entityId, item.rawId) : deleteCompanyHistory(entityId, item.rawId));
    }
    if (item.kind === "activity") {
      return () => deleteActivity(item.rawId, entityType === "contact" ? { contactId: entityId } : { companyId: entityId });
    }
    return null;
  }

  const getBorderColor = (category: string) => {
    switch (category) {
      case "call":
        return "border-[#c9611e]";
      case "meeting":
        return "border-[#0099e5]";
      case "email":
        return "border-[#5b3e8f]";
      case "note":
        return "border-[#1e7a52]";
      case "task":
        return "border-[#c0392b]";
      default:
        return "border-primary";
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Category Filter Pills */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-3">
        <div className="flex items-center gap-1.5">
          <Badge
            variant={filter === "all" ? "default" : "outline"}
            className="cursor-pointer text-xs font-medium"
            onClick={() => setFilter("all")}
          >
            All Activity ({timelineItems.length})
          </Badge>
          <Badge
            variant={filter === "call" ? "default" : "outline"}
            className="cursor-pointer text-xs font-medium"
            onClick={() => setFilter("call")}
          >
            Calls
          </Badge>
          <Badge
            variant={filter === "meeting" ? "default" : "outline"}
            className="cursor-pointer text-xs font-medium"
            onClick={() => setFilter("meeting")}
          >
            Meetings
          </Badge>
          <Badge
            variant={filter === "note" ? "default" : "outline"}
            className="cursor-pointer text-xs font-medium"
            onClick={() => setFilter("note")}
          >
            Notes
          </Badge>
          <Badge
            variant={filter === "email" ? "default" : "outline"}
            className="cursor-pointer text-xs font-medium"
            onClick={() => setFilter("email")}
          >
            Emails
          </Badge>
          <Badge
            variant={filter === "task" ? "default" : "outline"}
            className="cursor-pointer text-xs font-medium"
            onClick={() => setFilter("task")}
          >
            Tasks
          </Badge>
        </div>

        <span className="text-xs text-muted-foreground">
          Chronological record
        </span>
      </div>

      {/* Timeline Stream */}
      {filteredItems.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-12 text-center text-sm text-muted-foreground">
          <MessageSquare className="size-8 opacity-40 mb-2" />
          <p className="font-medium">
            {needle ? `Nothing matches "${searchTerm.trim()}"` : "No activity matching this filter"}
          </p>
          <p className="text-xs">
            {needle
              ? "Try a shorter or different term."
              : "Use the touchpoint bar above to log an interaction."}
          </p>
        </div>
      ) : (
        <div className="timeline-spine relative flex flex-col gap-5 pt-1">
          {filteredItems.map((item) => (
            <div key={item.id} className="relative flex items-start gap-3.5">
              {/* Node Icon - a touch of depth (inset highlight + drop
                  shadow) so it reads as a raised bead the spine threads
                  through, not a flat sticker */}
              <div
                className={`z-10 flex size-8 shrink-0 items-center justify-center rounded-full border shadow-[inset_0_1px_1px_rgba(255,255,255,0.4),0_1px_3px_rgba(0,0,0,0.15)] dark:shadow-[inset_0_1px_1px_rgba(255,255,255,0.08),0_1px_3px_rgba(0,0,0,0.35)] ${getBorderColor(
                  item.category
                )}`}
              >
                {getIcon(item.category)}
              </div>

              {/* Event Content Card */}
              <div className="flex-1 rounded-lg border border-border bg-card p-3.5 shadow-2xs transition-colors hover:border-primary/40">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold tracking-tight text-foreground">
                      {highlightMatch(item.title, searchTerm)}
                    </span>
                    {item.badgeLabel && (
                      <Badge variant="outline" className="text-[10px] py-0 px-1.5 font-normal">
                        {item.badgeLabel}
                      </Badge>
                    )}
                    {item.isScheduled && (
                      <Badge
                        variant="outline"
                        className={`text-[10px] py-0 px-1.5 font-normal ${
                          item.isCleared
                            ? "border-[var(--ok)] text-[var(--ok)]"
                            : "border-[var(--warn)] text-[var(--warn)]"
                        }`}
                      >
                        {item.isCleared ? "Done" : "Scheduled"}
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <time className="text-[11px] font-medium text-muted-foreground">
                      {item.isScheduled && isFuture(item.date)
                        ? item.date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })
                        : formatRelativeTime(item.date)}
                    </time>
                    {deleteHandlerFor(item) && (
                      <DeleteItemButton
                        label={`Delete ${item.kind}`}
                        confirmMessage={`Delete this ${item.kind}? This can't be undone.`}
                        onDelete={deleteHandlerFor(item)!}
                      />
                    )}
                  </div>
                </div>

                {item.body && (
                  <p className="mt-2 text-xs leading-relaxed text-foreground/85 whitespace-pre-wrap font-sans">
                    {highlightMatch(item.body, searchTerm)}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
