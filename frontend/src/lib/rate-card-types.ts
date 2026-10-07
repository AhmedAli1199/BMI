export type PriceType = "fixed" | "from" | "poa";
export type PriceUnit = "each" | "month" | "week" | "year" | "event" | "entry";
export type OfferKind = "volume" | "series" | "early_bird" | "note";

export type RateItem = {
  id: string; title_id: string; title_name: string; year: number; section: string; product: string;
  price_type: PriceType; price_gbp: number | null; unit: PriceUnit; specs: string | null; aliases: string[]; notes: string | null;
  valid_until: string | null; sort_order: number; needs_check: boolean; source: string | null; archived: boolean; price_label: string; updated_at: string;
};
export type OfferTier = { qty: number; discount_pct?: number; unit_price?: number; total?: number };
export type RateOffer = {
  id: string; brand: string; year: number; kind: OfferKind; label: string; details: string | null; rules: { tiers?: OfferTier[] };
  rate_ids: string[]; section: string | null; valid_until: string | null; needs_check: boolean;
};
export type RateSection = { key: string; label: string; hint: string; default_title_id: string | null; items: RateItem[] };
export type BrandSummary = {
  key: string; name: string; short: string; website: string; can_edit: boolean; products: number; needs_check: number; on_request: number;
  offers: number; last_updated: string | null; seed_available: number; sections: string[];
};
export type BrandTitle = { id: string; slug: string; name: string; digital_page_url: string | null; digital_issue_url: string | null };
export type BrandPage = {
  brand: BrandSummary; year: number; years: number[]; sections: RateSection[]; offers: RateOffer[]; archived: RateItem[]; titles: BrandTitle[]; has_next_year: boolean;
};
export type RateOverview = { year: number; years: number[]; brands: BrandSummary[] };
export type RateHistoryRow = {
  id: string; entity_type: string; entity_id: string; what: string; field: string; old_value: string | null; new_value: string | null;
  by: string | null; at: string; can_put_back: boolean;
};
export type NextYearRow = { id: string; section: string; product: string; old_label: string; old: number | null; new: number | null; price_type: PriceType; unit: PriceUnit };
export type NextYearPreview = { to_year: number; rows: NextYearRow[]; already_there: number; offers: number };

export const UNIT_LABELS: Record<PriceUnit, string> = {
  each: "per advert / item", month: "per month", week: "per week", year: "per year", event: "per event", entry: "per entry",
};
export const PRICE_TYPE_LABELS: Record<PriceType, { label: string; hint: string }> = {
  fixed: { label: "A set price", hint: "The price is the same for everyone, e.g. Full page £2,990." },
  from: { label: "Starts from", hint: "The lowest price - the final price depends on the details, e.g. Loose inserts from £495." },
  poa: { label: "Price on request", hint: "There's no list price - it's quoted case by case." },
};
export const OFFER_KIND_LABELS: Record<OfferKind, { label: string; hint: string }> = {
  volume: { label: "Discount for booking more", hint: "e.g. Book 2 adverts save 10%, 3 save 20%." },
  series: { label: "Lower price for a series", hint: "e.g. 4 dinners at £3,250 each, or 2 emails at £1,750 each." },
  early_bird: { label: "Early-bird price", hint: "Prices that end on a date, e.g. until 1 February." },
  note: { label: "Just a note", hint: "Anything else sellers should know, e.g. discounts on monthly bookings." },
};
