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

export const WORKSTREAM_IDS = ["sales", "capture", "business-cards", "hygiene", "revenue"] as const;
export type WorkstreamId = (typeof WORKSTREAM_IDS)[number];

/** Where a review card's "View … record" link goes. Contacts and companies have their own page; a follow-up card
 * is about a calendar activity, which has none, so it opens the contact (or company) the activity is for. */
export function reviewRecordLink(item: {
  entity_type: string | null;
  entity_id: string | null;
  payload: { related_entities?: { type: "contact" | "company"; id: string }[] };
}): { href: string; label: string } | null {
  if (!item.entity_type || !item.entity_id) return null;
  if (item.entity_type === "contact") return { href: `/contacts/${item.entity_id}`, label: "contact" };
  if (item.entity_type === "company") return { href: `/companies/${item.entity_id}`, label: "company" };
  const linked = item.payload.related_entities?.[0];
  if (!linked) return null;
  return { href: `/${linked.type === "contact" ? "contacts" : "companies"}/${linked.id}`, label: linked.type };
}
