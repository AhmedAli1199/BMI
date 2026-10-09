import { backendFetch } from "@/lib/backend";
import type { SalesMeta, SalesRate } from "@/lib/sales-types";
import type { DealInput } from "@/lib/deals-types";

/** What the order form needs: titles, salespeople and this year's and next year's rate cards. */
export async function formData() {
  const year = new Date().getFullYear();
  const [meta, rates] = await Promise.all([
    backendFetch<SalesMeta>("/api/sales/meta"),
    backendFetch<SalesRate[]>("/api/sales/rates").catch(() => [] as SalesRate[]),
  ]);
  return { meta, rates: rates.filter((r) => r.year >= year - 1 && r.year <= year + 1) };
}

export const EMPTY_DEAL: DealInput = {
  company_id: null, client_name: "", contact_id: null, contact_name: null, contact_email: null, confirmation_address: null,
  invoice_to: null, invoice_email: null, po_number: null, agency_name: null, agency_pct: 0, rep_id: null, split: [],
  booked_on: null, title_id: null, publication_label: null, insertions_label: null, document: "confirmation", pricing: "items",
  package_price_gbp: null, package_label: null, package_split: "rate_card", discount_pct: 0, lines: [], invoice_plan: "on_publication",
  special_instructions: null, copy_instructions: null, production_contact: null, show_artwork_specs: true, notes: null, proposal_id: null,
};
