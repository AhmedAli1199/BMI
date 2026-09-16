"use client";

import { useState } from "react";
import {
  Calendar,
  FileSpreadsheet,
  FileText,
  Mail,
  MessageSquare,
  Phone,
  PhoneCall,
  Sparkles,
} from "lucide-react";
import type { NoteOut, HistoryOut } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { cleanNoteBody } from "@/lib/notes";
import { highlightMatch } from "@/lib/highlight";

type TimelineItem = {
  id: string;
  kind: "note" | "history";
  date: Date;
  isoString: string;
  category: "call" | "meeting" | "email" | "note" | "system";
  title: string;
  body?: string | null;
  badgeLabel?: string;
};

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

function categorizeItem(typeStr: string | null, text: string | null): "call" | "meeting" | "email" | "note" | "system" {
  const lower = `${typeStr || ""} ${text || ""}`.toLowerCase();
  if (lower.includes("call") || lower.includes("phone") || lower.includes("reach") || lower.includes("attempt")) return "call";
  if (lower.includes("meet") || lower.includes("tasting") || lower.includes("visit") || lower.includes("expo")) return "meeting";
  if (lower.includes("mail") || lower.includes("letter") || lower.includes("message")) return "email";
  if (lower.includes("note") || lower.includes("brief") || lower.includes("contract")) return "note";
  return "system";
}

export function UnifiedActivityTimeline({
  notes = [],
  history = [],
  searchTerm = "",
}: {
  notes: NoteOut[];
  history: HistoryOut[];
  /** When set, narrows to items whose title/body matches (case-insensitive)
   * and highlights the matched text - the same term driving the Notes and
   * History tabs, so this timeline stays in sync with them rather than
   * needing its own separate search box. */
  searchTerm?: string;
}) {
  const [filter, setFilter] = useState<"all" | "call" | "meeting" | "note" | "email">("all");

  const timelineItems: TimelineItem[] = [
    ...notes.map((n): TimelineItem => {
      const d = n.act_created_at ? new Date(n.act_created_at) : new Date();
      return {
        id: `note-${n.id}`,
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
        kind: "history",
        date: d,
        isoString: d.toISOString(),
        category: categorizeItem(h.history_type, h.subject),
        title: h.subject || h.history_type,
        body: null,
        badgeLabel: h.history_type,
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
        return <PhoneCall className="size-3.5 text-amber-600 dark:text-amber-400" />;
      case "meeting":
        return <Calendar className="size-3.5 text-blue-600 dark:text-blue-400" />;
      case "email":
        return <Mail className="size-3.5 text-purple-600 dark:text-purple-400" />;
      case "note":
        return <FileText className="size-3.5 text-emerald-600 dark:text-emerald-400" />;
      default:
        return <Sparkles className="size-3.5 text-primary" />;
    }
  };

  const getBorderColor = (category: string) => {
    switch (category) {
      case "call":
        return "border-amber-500/30 bg-amber-500/10";
      case "meeting":
        return "border-blue-500/30 bg-blue-500/10";
      case "email":
        return "border-purple-500/30 bg-purple-500/10";
      case "note":
        return "border-emerald-500/30 bg-emerald-500/10";
      default:
        return "border-primary/30 bg-primary/10";
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
                  </div>
                  <time className="text-[11px] font-medium text-muted-foreground">
                    {formatRelativeTime(item.date)}
                  </time>
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
