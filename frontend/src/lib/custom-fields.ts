/** A record's custom fields ready to show: the real name from the field registry
 * (sent by the server as `custom_field_labels`), never our own internal keys (they
 * start with "_"), and no empty values. */
export type CustomFieldEntry = { key: string; label: string; value: string };

function tidyKey(key: string): string {
  const s = key.replace(/_/g, " ").trim();
  return s ? s[0].toUpperCase() + s.slice(1) : key;
}

export function customFieldEntries(
  fields: Record<string, unknown> | null | undefined,
  labels: Record<string, string> | null | undefined,
): CustomFieldEntry[] {
  return Object.entries(fields || {})
    .filter(([k, v]) => k && !k.startsWith("_") && v !== null && v !== undefined && String(v).trim() !== "")
    .map(([k, v]) => ({
      key: k,
      label: labels?.[k] || tidyKey(k),
      value: typeof v === "object" ? JSON.stringify(v) : String(v),
    }));
}

// Whole words only, so "address" doesn't count as an "ad".
const PUBLISHING_WORDS =
  /\b(issues?|ads?|adverts?|advertising|print|circulation|tier|sponsors?|sponsorship|expo|wtce|magazines?|publications?)\b/i;

/** The custom fields about magazines, issues and adverts - judged on the field's name. */
export function isPublishingField(entry: CustomFieldEntry): boolean {
  return PUBLISHING_WORDS.test(entry.label) || PUBLISHING_WORDS.test(entry.key.replace(/_/g, " "));
}
