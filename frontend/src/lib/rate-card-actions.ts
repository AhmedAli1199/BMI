"use server";

import { revalidatePath } from "next/cache";
import { backendFetch } from "@/lib/backend";
import type { NextYearPreview, OfferKind, OfferTier, PriceType, PriceUnit, RateHistoryRow, RateItem, RateOffer } from "@/lib/rate-card-types";

const json = (body: unknown, method = "POST") => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
const refresh = () => revalidatePath("/sales/rate-card", "layout");

export type ItemInput = {
  section?: string; title_id?: string | null; product?: string; price_type?: PriceType; price_gbp?: number | null; unit?: PriceUnit;
  specs?: string | null; aliases?: string[]; notes?: string | null; valid_until?: string | null; needs_check?: boolean;
};

export async function addRateItem(brand: string, year: number, input: ItemInput): Promise<RateItem> {
  const r = await backendFetch<RateItem>("/api/rate-card/items", json({ brand, year, ...input }));
  refresh();
  return r;
}

export async function editRateItem(id: string, input: ItemInput): Promise<RateItem> {
  const r = await backendFetch<RateItem>(`/api/rate-card/items/${id}`, json(input, "PATCH"));
  refresh();
  return r;
}

export async function archiveRateItem(id: string, restore = false): Promise<RateItem> {
  const r = await backendFetch<RateItem>(`/api/rate-card/items/${id}/archive${restore ? "?restore=true" : ""}`, { method: "POST" });
  refresh();
  return r;
}

export async function reorderRateItems(ids: string[]): Promise<void> {
  await backendFetch("/api/rate-card/items/reorder", json({ ids }));
  refresh();
}

export async function confirmAllRates(brand: string, year: number): Promise<{ confirmed: number }> {
  const r = await backendFetch<{ confirmed: number }>("/api/rate-card/confirm-all", json({ brand, year }));
  refresh();
  return r;
}

export async function loadMediaPack(brand: string, year: number): Promise<{ added: number }> {
  const r = await backendFetch<{ added: number }>(`/api/rate-card/brands/${brand}/load-media-pack?year=${year}`, { method: "POST" });
  refresh();
  return r;
}

export type OfferInput = {
  kind: OfferKind; label: string; details?: string | null; rules?: { tiers?: OfferTier[] }; rate_ids?: string[]; section?: string | null; valid_until?: string | null;
};

export async function saveOffer(brand: string, year: number, input: OfferInput, id?: string): Promise<RateOffer> {
  const r = await backendFetch<RateOffer>(id ? `/api/rate-card/offers/${id}` : "/api/rate-card/offers", json({ brand, year, ...input }, id ? "PUT" : "POST"));
  refresh();
  return r;
}

export async function deleteOffer(id: string): Promise<void> {
  await backendFetch(`/api/rate-card/offers/${id}`, { method: "DELETE" });
  refresh();
}

export async function previewNextYear(input: { brand: string; from_year: number; raise_pct: number; round_to: number }): Promise<NextYearPreview> {
  return backendFetch<NextYearPreview>("/api/rate-card/next-year/preview", json(input));
}

export async function applyNextYear(input: { brand: string; from_year: number; raise_pct: number; round_to: number; overrides: Record<string, number | null> }): Promise<{ copied: number; year: number }> {
  const r = await backendFetch<{ copied: number; year: number }>("/api/rate-card/next-year", json(input));
  refresh();
  return r;
}

export async function getRateHistory(brand: string, year: number): Promise<RateHistoryRow[]> {
  return backendFetch<RateHistoryRow[]>(`/api/rate-card/history?brand=${brand}&year=${year}`);
}

export async function putBackChange(id: string): Promise<RateItem> {
  const r = await backendFetch<RateItem>(`/api/rate-card/history/${id}/put-back`, { method: "POST" });
  refresh();
  return r;
}
