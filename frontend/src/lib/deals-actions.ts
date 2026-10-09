"use server";

import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";
import type { Deal, DealEmailDraft, DealInput, DealIssue, DealPreview, DealSettings } from "@/lib/deals-types";

const json = { "Content-Type": "application/json" };

function refresh(d: { id: string; company_id?: string | null }) {
  revalidatePath("/sales/deals");
  revalidatePath(`/sales/deals/${d.id}`);
  revalidatePath("/sales/bookings");
  if (d.company_id) revalidatePath(`/companies/${d.company_id}`);
}

export async function createDeal(input: DealInput): Promise<Deal & { notes: string[] }> {
  const d = await backendFetch<Deal & { notes: string[] }>("/api/sales/deals", { method: "POST", headers: json, body: JSON.stringify(input) });
  refresh(d);
  return d;
}

export async function updateDeal(id: string, input: DealInput): Promise<Deal & { notes: string[] }> {
  const d = await backendFetch<Deal & { notes: string[] }>(`/api/sales/deals/${id}`, { method: "PUT", headers: json, body: JSON.stringify(input) });
  refresh(d);
  return d;
}

export async function setDealStatus(id: string, status: "pencilled" | "confirmed" | "cancelled", reason?: string, keepRun = true): Promise<Deal & { notes: string[] }> {
  const d = await backendFetch<Deal & { notes: string[] }>(`/api/sales/deals/${id}/status`, {
    method: "POST", headers: json, body: JSON.stringify({ status, reason: reason ?? null, keep_run: keepRun }),
  });
  refresh(d);
  return d;
}

export async function deleteDeal(id: string): Promise<void> {
  await backendFetch(`/api/sales/deals/${id}`, { method: "DELETE" });
  revalidatePath("/sales/deals");
}

export async function rebookDeal(id: string): Promise<(Deal & { notes: string[] }) | { id: null; notes: string[]; needs_issues: true; year: number }> {
  const d = await backendFetch<(Deal & { notes: string[] }) | { id: null; notes: string[]; needs_issues: true; year: number }>(`/api/sales/deals/${id}/rebook`, { method: "POST" });
  revalidatePath("/sales/deals");
  return d;
}

export async function previewDeal(input: Pick<DealInput, "pricing" | "package_price_gbp" | "package_split" | "discount_pct" | "lines"> & { agency_pct: number }): Promise<DealPreview> {
  return backendFetch<DealPreview>("/api/sales/deals/preview", { method: "POST", headers: json, body: JSON.stringify(input) });
}

export async function getDealIssues(titleId: string, include: string[] = []): Promise<DealIssue[]> {
  const q = new URLSearchParams({ title_id: titleId });
  include.forEach((i) => q.append("include", i));
  return backendFetch<DealIssue[]>(`/api/sales/deals/issues?${q}`);
}

export async function getDealPrefill(params: { company_id?: string; contact_id?: string }): Promise<Partial<DealInput> & { last_order?: { id: string; number: number } }> {
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v) as [string, string][]);
  return backendFetch(`/api/sales/deals/prefill?${q}`);
}

export async function getDealEmailDraft(id: string): Promise<DealEmailDraft> {
  return backendFetch<DealEmailDraft>(`/api/sales/deals/${id}/email-draft`);
}

export async function sendDeal(id: string, input: { to: string[]; cc: string[]; subject: string; body: string }): Promise<Deal> {
  const d = await backendFetch<Deal>(`/api/sales/deals/${id}/send`, { method: "POST", headers: json, body: JSON.stringify(input) });
  refresh(d);
  return d;
}

export async function markDealSent(id: string, to: string | null): Promise<Deal> {
  const d = await backendFetch<Deal>(`/api/sales/deals/${id}/mark-sent`, { method: "POST", headers: json, body: JSON.stringify({ to }) });
  refresh(d);
  return d;
}

export async function saveDealSettings(input: Omit<DealSettings, "can_edit">): Promise<DealSettings> {
  const r = await backendFetch<DealSettings>("/api/sales/deals/settings", { method: "PUT", headers: json, body: JSON.stringify(input) });
  revalidatePath("/sales/deals");
  return r;
}
