/** Human labels for the three Act! source databases plus manually-created
 * CRM rows - shown wherever a raw source_db value would otherwise leak
 * through as "onboard" or "sellingtravel". */
export const SOURCE_LABELS: Record<string, string> = {
  onboard: "OnBoard Hospitality",
  prospects: "Prospects",
  sellingtravel: "Selling Travel",
  manual: "Added in CRM",
};

export function sourceLabel(source_db: string): string {
  return SOURCE_LABELS[source_db] ?? source_db;
}

/** Outlined badge colour per source database, using the same masthead
 * palette as everywhere else (see publication-style.tsx) rather than raw
 * Tailwind -500/10 rainbow swatches. Deliberately no fill - a thin coloured
 * border + text, matching BMI's own print/web housestyle. */
const SOURCE_BADGE_STYLES: Record<string, string> = {
  onboard: "border-[#0099e5] text-[#0077b3]",
  sellingtravel: "border-[#1e7a52] text-[#1e7a52]",
  prospects: "border-[#b8791a] text-[#96620f]",
};

export function sourceBadgeStyle(source_db: string): string {
  return SOURCE_BADGE_STYLES[source_db] ?? "border-border text-muted-foreground";
}
