"use server";

import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";
import { sourceLabel } from "@/lib/sources";
import type { ClientSuggestion, EditionSummary, OrderInput, SalesOrder } from "@/lib/sales-types";
import type { CompanyListItem, FieldChange } from "@/lib/types";

/** Server actions for the Sales Order Register - callable from client
 * components without exposing the backend API key (same pattern as
 * lib/actions.ts). */

function revalidateSales(editionId?: string, companyId?: string | null) {
  revalidatePath("/sales", "layout");
  if (editionId) revalidatePath(`/sales/editions/${editionId}`);
  if (companyId) revalidatePath(`/companies/${companyId}`);
}

export async function createOrder(editionId: string, input: OrderInput): Promise<SalesOrder> {
  const order = await backendFetch<SalesOrder>("/api/sales/orders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ edition_id: editionId, ...input }),
  });
  revalidateSales(editionId, order.company?.id);
  return order;
}

export async function updateOrder(orderId: string, input: OrderInput): Promise<SalesOrder> {
  const order = await backendFetch<SalesOrder>(`/api/sales/orders/${orderId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  revalidateSales(order.edition_id, order.company?.id);
  return order;
}

export async function deleteOrder(orderId: string, editionId: string) {
  await backendFetch(`/api/sales/orders/${orderId}`, { method: "DELETE" });
  revalidateSales(editionId);
}

export async function getOrderChanges(orderId: string): Promise<FieldChange[]> {
  return backendFetch<FieldChange[]>(`/api/sales/orders/${orderId}/changes`);
}

export async function suggestClients(q: string): Promise<ClientSuggestion[]> {
  if (!q.trim()) return [];
  return backendFetch<ClientSuggestion[]>(`/api/sales/clients?search=${encodeURIComponent(q)}`);
}

export async function searchCompaniesForOrder(q: string): Promise<{ id: string; label: string; sublabel?: string | null }[]> {
  if (!q.trim()) return [];
  const page = await backendFetch<{ items: CompanyListItem[] }>(`/api/companies?${new URLSearchParams({ q, page_size: "8" })}`);
  return page.items.map((c) => ({ id: c.id, label: c.name, sublabel: [sourceLabel(c.source_db), c.industry].filter(Boolean).join(" · ") }));
}

export async function listEditionsForTitle(titleId: string, year: number): Promise<EditionSummary[]> {
  return backendFetch<EditionSummary[]>(`/api/sales/editions?title_id=${titleId}&year=${year}`);
}

export async function createEdition(input: {
  title_id: string;
  year: number;
  name: string;
  period_label?: string | null;
  edition_date?: string | null;
  exchange_rate?: number | null;
  target_gbp?: number | null;
}): Promise<EditionSummary> {
  const ed = await backendFetch<EditionSummary>("/api/sales/editions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  revalidateSales(ed.id);
  return ed;
}

export async function updateEdition(
  editionId: string,
  input: { status?: "open" | "closed"; target_gbp?: number | null; notes?: string | null; edition_date?: string | null; period_label?: string | null; name?: string }
): Promise<EditionSummary> {
  const ed = await backendFetch<EditionSummary>(`/api/sales/editions/${editionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  revalidateSales(editionId);
  return ed;
}
