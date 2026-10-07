"use server";

import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";
import { sourceLabel } from "@/lib/sources";
import type { BookingChoice, ClientSuggestion, CostLineInput, EditionCosts, EditionSummary, OrderInput, RenewalPassResult, SalesOrder, SalesRate, SalesTitle, XeroChoice } from "@/lib/sales-types";
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
  input: { status?: "open" | "closed"; target_gbp?: number | null; notes?: string | null; edition_date?: string | null; period_label?: string | null; name?: string; digital_url?: string | null }
): Promise<EditionSummary> {
  const ed = await backendFetch<EditionSummary>(`/api/sales/editions/${editionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  revalidateSales(editionId);
  return ed;
}

// ---- Renewals: rate card, online links, renewal pass (SALES-021) ----------

export async function startRenewalPass(editionId: string): Promise<RenewalPassResult> {
  const r = await backendFetch<RenewalPassResult>(`/api/sales/editions/${editionId}/renewal-pass`, { method: "POST" });
  revalidatePath("/automations", "layout");
  return r;
}

export async function saveRate(
  input: { title_id: string; year: number; product: string; price_gbp: number; notes?: string | null },
  id?: string
): Promise<SalesRate> {
  const r = await backendFetch<SalesRate>(id ? `/api/sales/rates/${id}` : "/api/sales/rates", {
    method: id ? "PUT" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  revalidatePath("/sales/rate-card");
  return r;
}

export async function deleteRate(id: string) {
  await backendFetch(`/api/sales/rates/${id}`, { method: "DELETE" });
  revalidatePath("/sales/rate-card");
}

export async function saveTitleLinks(titleId: string, links: { digital_page_url: string | null; digital_issue_url: string | null }): Promise<SalesTitle> {
  const t = await backendFetch<SalesTitle>(`/api/sales/titles/${titleId}/links`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(links),
  });
  revalidatePath("/sales/rate-card");
  return t;
}

// ---- Event costs ----------------------------------------------------------

export async function saveCostLine(editionId: string, input: CostLineInput, id?: string): Promise<EditionCosts> {
  const r = await backendFetch<EditionCosts>(`/api/sales/editions/${editionId}/costs${id ? `/${id}` : ""}`, {
    method: id ? "PUT" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  revalidatePath(`/sales/editions/${editionId}`);
  return r;
}

export async function deleteCostLine(editionId: string, id: string): Promise<EditionCosts> {
  const r = await backendFetch<EditionCosts>(`/api/sales/editions/${editionId}/costs/${id}`, { method: "DELETE" });
  revalidatePath(`/sales/editions/${editionId}`);
  return r;
}

/** Undo an invoice link the matcher made: clears the invoice number, value and date it filled in. */
export async function unlinkXeroInvoice(orderId: string): Promise<SalesOrder> {
  const order = await backendFetch<SalesOrder>(`/api/sales/orders/${orderId}/xero-unlink`, { method: "POST" });
  revalidateSales(order.edition_id, order.company?.id);
  revalidatePath("/automations/review");
  return order;
}

/** Xero invoices this booking could be linked to, most likely first. */
export async function getXeroChoices(orderId: string, q = ""): Promise<XeroChoice[]> {
  return backendFetch<XeroChoice[]>(`/api/sales/orders/${orderId}/xero-choices?q=${encodeURIComponent(q)}`);
}

/** Links a booking to the Xero invoice someone picked; the amount and date come from Xero. */
export async function linkXeroInvoice(orderId: string, invoiceId: string): Promise<SalesOrder> {
  const order = await backendFetch<SalesOrder>(`/api/sales/orders/${orderId}/xero-link`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ invoice_id: invoiceId }),
  });
  revalidateSales(order.edition_id, order.company?.id);
  revalidatePath("/automations/review");
  return order;
}

/** Bookings an unmatched Xero invoice could be for. */
export async function getInvoiceBookingChoices(invoiceId: string, q = ""): Promise<BookingChoice[]> {
  return backendFetch<BookingChoice[]>(`/api/sales/xero/invoices/${invoiceId}/choices?q=${encodeURIComponent(q)}`);
}

export async function linkInvoiceToBookings(invoiceId: string, orderIds: string[]): Promise<SalesOrder[]> {
  const orders = await backendFetch<SalesOrder[]>(`/api/sales/xero/invoices/${invoiceId}/link`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ order_ids: orderIds }),
  });
  for (const o of orders) revalidateSales(o.edition_id, o.company?.id);
  revalidatePath("/sales/invoicing");
  revalidatePath("/automations/review");
  return orders;
}
