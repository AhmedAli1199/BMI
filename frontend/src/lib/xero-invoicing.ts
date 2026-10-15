"use server";

import { backendFetch } from "@/lib/backend";

const json = { "Content-Type": "application/json" };

export type XeroProblem = { key: "contact" | "account" | "currency" | "connection" | "nothing" | "tracking" | "xero"; message: string };
export type XeroContact = { id: string; name: string; email?: string | null; score?: number };
export type XeroTracking = { name: string; option: string };
export type XeroDraftLine = {
  order_id: string; title_id: string; title: string; description: string; quantity: number; unit_amount: number; value_gbp: number;
  discount_rate: number | null; account_code: string | null; item_code: string | null; tracking: XeroTracking[]; amount_given: boolean;
};
export type XeroDraft = {
  deal_id: string; deal_number: number; client_name: string; contact: XeroContact | null; contact_candidates: XeroContact[];
  date: string; reference: string; currency: string; lines: XeroDraftLine[]; problems: XeroProblem[];
  invoice_to: string | null; invoice_email: string | null; po_number: string | null; instructions: string | null;
  agency: { name: string; pct: number } | null;
};
export type XeroInvoiceSummary = {
  id: string; number: string; status: string; url: string; contact: string; date: string; due_date: string | null; reference: string | null;
  currency: string; sub_total: number | null; tax: number | null; total: number | null;
  lines: { description: string; quantity: number; unit_amount: number; discount_rate: number | null; account_code: string | null; item_code: string | null;
    tax_type: string | null; tax: number | null; amount: number | null; tracking: string[] }[];
};
export type XeroCreateResult = { ok: true; invoice: XeroInvoiceSummary } | { ok: false; draft: XeroDraft; problems: XeroProblem[] };
export type XeroReference = {
  accounts: { code: string; name: string; type: string }[]; items: { code: string; name: string; account_code: string | null }[];
  tracking: { name: string; options: string[] }[]; currencies: string[];
};
export type XeroCodes = { default: { account_code?: string; item_code?: string; tracking?: XeroTracking[] };
  titles: Record<string, { account_code?: string; item_code?: string; tracking?: XeroTracking[] }> };
export type XeroCreateInput = {
  order_ids?: string[]; contact_id?: string | null; contact_name?: string | null; reference?: string | null; currency?: string | null;
  lines?: Record<string, { account_code?: string | null; item_code?: string | null; unit_amount?: number | null; description?: string | null; tracking?: XeroTracking[] }>;
};

export async function createXeroInvoice(dealId: string, input: XeroCreateInput): Promise<XeroCreateResult> {
  // No revalidatePath here: it would redraw the page under the "check it" dialog. The dialog refreshes on close.
  return backendFetch<XeroCreateResult>(`/api/xero-invoicing/deals/${dealId}`, { method: "POST", headers: json, body: JSON.stringify(input) });
}

export async function searchXeroContacts(q: string): Promise<XeroContact[]> {
  return backendFetch<XeroContact[]>(`/api/xero-invoicing/contacts?${new URLSearchParams({ q })}`);
}

export async function getXeroReference(fresh = false): Promise<XeroReference> {
  return backendFetch<XeroReference>(`/api/xero-invoicing/reference${fresh ? "?fresh=true" : ""}`);
}

export async function getXeroCodes(): Promise<XeroCodes> {
  return backendFetch<XeroCodes>("/api/xero-invoicing/codes");
}

export async function saveXeroCodes(codes: XeroCodes): Promise<XeroCodes> {
  return backendFetch<XeroCodes>("/api/xero-invoicing/codes", { method: "PUT", headers: json, body: JSON.stringify(codes) });
}
