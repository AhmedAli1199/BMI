import type { FeedbackStatus } from "@/lib/feedback-types";

export function statusTone(s: FeedbackStatus): string {
  return {
    new: "bg-primary/10 text-primary",
    looking: "bg-[var(--warn-tint)] text-[var(--warn)]",
    fixed: "bg-[var(--ok-tint)] text-[var(--ok)]",
    wont_do: "bg-muted text-muted-foreground",
  }[s];
}

export function fmtWhen(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  const mins = Math.round((Date.now() - d.getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  if (mins < 60 * 24) return `${Math.round(mins / 60)} h ago`;
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: d.getFullYear() === new Date().getFullYear() ? undefined : "numeric" });
}
