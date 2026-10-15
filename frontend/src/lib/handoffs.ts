/** The same suggestion the server makes (app/sales/handoffs.py), so the form can show it straight away. */
import type { HandoffRoutes } from "@/lib/deals-types";

const EDITORIAL = /sponsor|advertorial|partner content|feature|spotlight|interview|q\s*&\s*a|profile|guest|social|editorial|article|branded content|content|insight|meet the|ask the expert|news story|focus/i;
const PRODUCTION_ONLY = /banner|mpu|skyscraper|leaderboard|html|solus|display|full page|half page|quarter page|page advert|cover|insert|bellyband|dps/i;
const FORM_TITLES = /caribbean|visit\s*usa/i;

export function suggestTeam(titleName: string | null | undefined, words: string): "editorial" | "production" | "both" {
  const sponsored = EDITORIAL.test(words);
  if (sponsored && titleName && FORM_TITLES.test(titleName)) return "production";
  if (sponsored && PRODUCTION_ONLY.test(words) && /banner|html|solus|mpu/i.test(words)) return "both";
  return sponsored ? "editorial" : "production";
}

export function looksSponsored(words: string): boolean {
  return EDITORIAL.test(words);
}

/** The routing table's addresses for a magazine and team (falls back to the default row; production to the always-copied addresses). */
export function routeFor(routes: HandoffRoutes | undefined, titleId: string | null | undefined, team: "editorial" | "production", productionFallback = ""): string {
  const own = titleId ? routes?.titles?.[titleId]?.[team] : undefined;
  return own || routes?.default?.[team] || (team === "production" ? productionFallback : "") || "";
}

export const TEAM_LABEL = { editorial: "Editorial", production: "Production", both: "Editorial and production", none: "Nobody" } as const;
