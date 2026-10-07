/** One colour per brand for its masthead rule - theme tokens, so it works in every theme. */
export const BRAND_COLOR: Record<string, string> = { obh: "var(--chart-1)", tbtm: "var(--chart-2)", stm: "var(--chart-3)" };
export const brandColor = (key: string) => BRAND_COLOR[key] ?? "var(--primary)";
