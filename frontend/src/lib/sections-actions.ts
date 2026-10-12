"use server";

import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";
import type { SectionKey, SectionsInfo } from "@/lib/sections";

export async function saveHiddenSections(hidden: Record<string, SectionKey[]>, users: Record<string, SectionKey[]>): Promise<SectionsInfo> {
  const out = await backendFetch<SectionsInfo>("/api/ui/sections", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ hidden, users }),
  });
  revalidatePath("/", "layout");
  return out;
}
