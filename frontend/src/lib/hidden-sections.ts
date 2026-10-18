import { CACHED, backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import type { SectionKey, SectionsInfo } from "@/lib/sections";

/** Sections an administrator has hidden for the signed-in person (Settings > Sections). Administrators see everything. */
export async function hiddenSections(): Promise<SectionKey[]> {
  const session = await getSession();
  if (!session || session.role === "admin") return [];
  return backendFetch<SectionsInfo>("/api/ui/sections", CACHED.sections).then((r) => r.mine).catch(() => [] as SectionKey[]);
}
