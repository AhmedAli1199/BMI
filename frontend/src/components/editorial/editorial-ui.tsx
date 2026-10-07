import { Circle, Diamond, FileText, Megaphone, Star, Triangle } from "lucide-react";
import type { Deadline } from "@/lib/editorial-types";

export const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function fmtDay(iso: string | null | undefined, withYear = false): string {
  if (!iso) return "—";
  return new Date(iso + "T00:00:00").toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short", ...(withYear ? { year: "numeric" } : {}) });
}

export function daysLabel(days: number): string {
  if (days === 0) return "Today";
  if (days === 1) return "Tomorrow";
  if (days === -1) return "Yesterday";
  if (days < 0) return `${-days} days ago`;
  if (days < 14) return `In ${days} days`;
  return `In ${Math.round(days / 7)} weeks`;
}

/** Colour for a countdown: red today/overdue-ish, amber within a week, quiet otherwise. */
export function countdownColor(days: number): string | undefined {
  if (days <= 2) return "var(--bad)";
  if (days <= 7) return "var(--warn)";
  return undefined;
}

export const TYPE_META: Record<Deadline["type"], { label: string; Icon: typeof Circle; color: string }> = {
  advertising: { label: "Advertising deadline", Icon: Diamond, color: "var(--warn)" },
  editorial: { label: "Editorial deadline", Icon: FileText, color: "var(--chart-4)" },
  copy: { label: "Copy & artwork deadline", Icon: Triangle, color: "var(--chart-5)" },
  milestone: { label: "Key date", Icon: Star, color: "var(--chart-2)" },
  publication: { label: "Publication", Icon: Circle, color: "var(--primary)" },
  event: { label: "Event day", Icon: Megaphone, color: "var(--primary)" },
};
