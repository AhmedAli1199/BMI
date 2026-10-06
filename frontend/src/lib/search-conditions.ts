import type { SearchCondition } from "@/lib/contact-tools-types";

export function parseConds(raw: string | undefined | null): SearchCondition[] {
  if (!raw) return [];
  try {
    const v = JSON.parse(raw);
    return Array.isArray(v) ? v.filter((c) => c && typeof c.field === "string") : [];
  } catch {
    return [];
  }
}
