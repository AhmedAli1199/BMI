"use server";

import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";
import type { BookingForm, BookingFormInput, Deal, DealEmailDraft, DealInput, DealIssue, DealPreview, DealSettings } from "@/lib/deals-types";

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

/** For a booking accounts has checked: ask them to make a change, or cancel it. Nothing changes until they approve. */
export async function requestDealChange(id: string, input: { reason: string; booking?: DealInput; cancel?: boolean; cancel_reason?: string; keep_run?: boolean }): Promise<Deal> {
  const d = await backendFetch<Deal>(`/api/sales/deals/${id}/change-request`, { method: "POST", headers: json, body: JSON.stringify(input) });
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

export async function saveBookingForm(id: string | null, input: BookingFormInput): Promise<BookingForm> {
  const f = await backendFetch<BookingForm>(id ? `/api/sales/booking-forms/${id}` : "/api/sales/booking-forms",
    { method: id ? "PUT" : "POST", headers: json, body: JSON.stringify(input) });
  revalidatePath("/sales/deals");
  return f;
}

export async function deleteBookingForm(id: string): Promise<void> {
  await backendFetch(`/api/sales/booking-forms/${id}`, { method: "DELETE" });
  revalidatePath("/sales/deals");
}

/** Accounts: let the salesperson change a locked booking. It locks again (and comes back for checking) when they save. */
export async function unlockDeal(id: string, note: string | null): Promise<Deal> {
  const d = await backendFetch<Deal>(`/api/sales/deals/${id}/unlock`, { method: "POST", headers: json, body: JSON.stringify({ note }) });
  refresh(d);
  return d;
}

export async function relockDeal(id: string): Promise<Deal> {
  const d = await backendFetch<Deal>(`/api/sales/deals/${id}/relock`, { method: "POST" });
  refresh(d);
  return d;
}

/** Accounts' own "remind me on" date for items (null = back to the booking's rule). */
export async function setInvoiceDate(id: string, orderIds: string[], dueOn: string | null): Promise<Deal> {
  const d = await backendFetch<Deal>(`/api/sales/deals/${id}/invoice-date`, { method: "POST", headers: json, body: JSON.stringify({ order_ids: orderIds, due_on: dueOn }) });
  refresh(d);
  return d;
}

/** An advert in the printed issue with no booking: record it as a filler, or ask the salesperson to make the booking. */
export async function reportUnbookedAd(input: { edition_id: string; client_name: string; company_id?: string | null; rep_id?: string | null; page?: string | null;
  outcome: "filler" | "needs_booking"; note?: string | null }): Promise<{ ok: boolean; message: string }> {
  const r = await backendFetch<{ ok: boolean; message: string }>("/api/sales/deals/unbooked-ad", { method: "POST", headers: json, body: JSON.stringify(input) });
  revalidatePath(`/sales/editions/${input.edition_id}`);
  return r;
}

/** Send (again) the hand-off emails to editorial / production for some lines and teams (empty = whatever is due). */
export async function sendHandoffs(id: string, lines: string[] = [], teams: string[] = []): Promise<Deal & { notes_after_save?: string[] }> {
  const d = await backendFetch<Deal & { notes?: string[] }>(`/api/sales/deals/${id}/handoffs/send`, { method: "POST", headers: json, body: JSON.stringify({ lines, teams }) });
  refresh(d);
  return { ...d, notes_after_save: d.notes };
}

/** Who works on an item, its format and where else it appears - allowed on a locked booking (it doesn't change the invoice). */
export async function setLineHandoff(id: string, lineKey: string, input: { handoff?: import("@/lib/deals-types").DealHandoff; activities?: import("@/lib/deals-types").DealActivity[] }): Promise<Deal> {
  const d = await backendFetch<Deal>(`/api/sales/deals/${id}/lines/${encodeURIComponent(lineKey)}/handoff`, { method: "PUT", headers: json, body: JSON.stringify(input) });
  refresh(d);
  return d;
}
