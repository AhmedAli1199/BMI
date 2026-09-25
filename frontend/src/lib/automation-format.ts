/** Shared number/time formatting for the Automations Hub pages, so every
 * page says "4h", "62%", "1,204" the same way. */

export function fmtCount(n: number): string {
  return n.toLocaleString("en-GB");
}

export function fmtPercent(rate: number | null): string {
  return rate === null ? "—" : `${Math.round(rate * 100)}%`;
}

/** Seconds -> the single largest sensible unit: "45s", "12m", "4h", "3d". */
export function fmtDuration(seconds: number | null): string {
  if (seconds === null || Number.isNaN(seconds)) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = seconds / 60;
  if (mins < 60) return `${Math.round(mins)}m`;
  const hours = mins / 60;
  if (hours < 48) return `${Math.round(hours)}h`;
  return `${Math.round(hours / 24)}d`;
}

export function fmtAgo(iso: string | null): string {
  if (!iso) return "—";
  const secs = (Date.now() - new Date(iso).getTime()) / 1000;
  if (secs < 60) return "just now";
  return `${fmtDuration(secs)} ago`;
}

/** % change vs the previous period. null when there's no previous
 * period to compare against (all-time range) or it was zero. */
export function pctChange(current: number, previous: number | null): number | null {
  if (previous === null || previous === 0) return null;
  return (current - previous) / previous;
}

export const WORKSTREAM_IDS = ["sales", "capture", "business-cards", "hygiene"] as const;
export type WorkstreamId = (typeof WORKSTREAM_IDS)[number];
