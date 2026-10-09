"use server";

import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";
import type { BookingNewBusiness, CommissionRule, CommissionRuleInput, CommissionSettings, CommissionStatement, EditionCommission } from "@/lib/commission-types";

const json = { "Content-Type": "application/json" };

export async function approveStatement(repId: string, period: string): Promise<CommissionStatement> {
  const s = await backendFetch<CommissionStatement>("/api/commission/statement/approve", { method: "POST", headers: json, body: JSON.stringify({ rep_id: repId, period }) });
  revalidatePath("/sales/commissions", "layout");
  return s;
}

export async function getBookingNewBusiness(orderId: string): Promise<BookingNewBusiness> {
  return backendFetch<BookingNewBusiness>(`/api/commission/orders/${orderId}/new-business`);
}

/** decision null = work it out from history again. */
export async function decideNewBusiness(orderId: string, decision: "new" | "returning" | null, reason?: string): Promise<BookingNewBusiness> {
  const r = await backendFetch<BookingNewBusiness>(`/api/commission/orders/${orderId}/new-business`, {
    method: "PUT", headers: json, body: JSON.stringify({ decision, reason: reason ?? null }),
  });
  revalidatePath("/sales/commissions", "layout");
  return r;
}

export async function loadCommissionStructure(replace = false): Promise<{ rules: number }> {
  const r = await backendFetch<{ rules: number }>(`/api/commission/plans/load?replace=${replace}`, { method: "POST" });
  revalidatePath("/sales/commissions", "layout");
  return r;
}

export async function saveCommissionRule(input: CommissionRuleInput, id?: string): Promise<CommissionRule> {
  const r = await backendFetch<CommissionRule>(id ? `/api/commission/rules/${id}` : "/api/commission/rules", {
    method: id ? "PATCH" : "POST", headers: json, body: JSON.stringify(input),
  });
  revalidatePath("/sales/commissions", "layout");
  return r;
}

export async function deleteCommissionRule(id: string): Promise<void> {
  await backendFetch(`/api/commission/rules/${id}`, { method: "DELETE" });
  revalidatePath("/sales/commissions", "layout");
}

export async function saveCommissionSettings(input: CommissionSettings): Promise<CommissionSettings> {
  const r = await backendFetch<CommissionSettings>("/api/commission/settings", { method: "PUT", headers: json, body: JSON.stringify(input) });
  revalidatePath("/sales/commissions", "layout");
  return r;
}

export async function getEditionCommission(editionId: string): Promise<EditionCommission> {
  return backendFetch<EditionCommission>(`/api/commission/editions/${editionId}`);
}

export async function markNewGuide(editionId: string, on: boolean, repId: string | null): Promise<EditionCommission> {
  const r = await backendFetch<EditionCommission>(`/api/commission/editions/${editionId}/new-guide`, { method: "PUT", headers: json, body: JSON.stringify({ on, rep_id: repId }) });
  revalidatePath(`/sales/editions/${editionId}`);
  return r;
}

export async function markCostsFinal(editionId: string, on: boolean): Promise<EditionCommission> {
  const r = await backendFetch<EditionCommission>(`/api/commission/editions/${editionId}/costs-final`, { method: "POST", headers: json, body: JSON.stringify({ on }) });
  revalidatePath(`/sales/editions/${editionId}`);
  return r;
}

export async function signOffCosts(editionId: string, on: boolean): Promise<EditionCommission> {
  const r = await backendFetch<EditionCommission>(`/api/commission/editions/${editionId}/costs-signoff`, { method: "POST", headers: json, body: JSON.stringify({ on }) });
  revalidatePath(`/sales/editions/${editionId}`);
  revalidatePath("/sales/commissions", "layout");
  return r;
}

export async function saveAdvances(repId: string, period: string, advances: number, note: string | null): Promise<CommissionStatement> {
  const r = await backendFetch<CommissionStatement>("/api/commission/statement/advances", {
    method: "PUT", headers: json, body: JSON.stringify({ rep_id: repId, period, advances_gbp: advances, note }),
  });
  revalidatePath("/sales/commissions", "layout");
  return r;
}

export async function saveAttendance(repId: string, editionId: string, count: number): Promise<{ count: number }> {
  const r = await backendFetch<{ count: number }>("/api/commission/attendance", {
    method: "PUT", headers: json, body: JSON.stringify({ rep_id: repId, edition_id: editionId, count }),
  });
  revalidatePath("/sales/commissions", "layout");
  return r;
}
