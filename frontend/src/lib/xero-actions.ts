"use server";

import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";

export type XeroStatus = {
  configured: boolean;
  connected: boolean;
  organisation: string | null;
  connected_at: string | null;
  last_sync_at: string | null;
  last_error: string | null;
  invoices: number;
  bookings_matched: number;
  redirect_uri: string;
};

export async function syncXero(): Promise<{ invoices?: number; skipped?: string }> {
  const res = await backendFetch<{ invoices?: number; skipped?: string }>("/api/integrations/xero/sync", { method: "POST" });
  revalidatePath("/settings");
  return res;
}

export async function disconnectXero() {
  await backendFetch("/api/integrations/xero", { method: "DELETE" });
  revalidatePath("/settings");
}
