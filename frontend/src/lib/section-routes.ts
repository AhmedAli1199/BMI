import type { SectionKey } from "@/lib/sections";

/** Which hideable section (Settings > Sections) each page belongs to - the longest matching start wins. */
const ROUTES: [string, SectionKey][] = [
  ["/automations/today", "today"],
  ["/automations/review", "review_queue"],
  ["/automations", "automations_hub"],
  ["/activities", "calendar"],
  ["/reminders", "reminders"],
  ["/calls", "calls"],
  ["/contacts", "contacts"],
  ["/companies", "companies"],
  ["/groups", "groups"],
  ["/sales/dashboard", "sales_dashboard"],
  ["/sales/deals", "orders"],
  ["/sales/bookings", "bookings"],
  ["/sales/renewals", "renewals"],
  ["/sales/proposals", "proposals"],
  ["/sales/rate-card", "rate_card"],
  ["/sales/editions", "editions"],
  ["/sales/compare", "editions"],
  ["/sales/invoicing", "invoicing"],
  ["/sales/commissions", "commissions"],
  ["/editorial", "editorial"],
  ["/mail-merge/templates", "email_templates"],
  ["/mail-merge", "mail_merge"],
  ["/data-health", "data_health"],
];

export function sectionForPath(path: string): SectionKey | null {
  if (path === "/sales") return "sales_overview";
  let best: [string, SectionKey] | null = null;
  for (const r of ROUTES) {
    if ((path === r[0] || path.startsWith(r[0] + "/")) && (!best || r[0].length > best[0].length)) best = r;
  }
  return best ? best[1] : null;
}
