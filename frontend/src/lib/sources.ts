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
