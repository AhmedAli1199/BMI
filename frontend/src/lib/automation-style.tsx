import {
  BookOpen,
  CalendarClock,
  CreditCard,
  Heart,
  MailQuestion,
  MailWarning,
  Sparkles,
  UserCheck,
  UserMinus,
  UserPlus,
  Users,
  Zap,
  type LucideIcon,
} from "lucide-react";

export type AutomationStyle = {
  icon: LucideIcon;
  color: string; // icon/accent text color
  chipBg: string; // icon chip background + border
  accent: string; // gradient stop classes for the card's top bar
  ring: string; // hover border color
};

// Which workstream each automation belongs to lives in the backend
// (app/automations/workstreams.py) - the Hub pages read it from the API.

// Keyed by the backend's registry `kind` string (see
// app/automations/registry.py). Purely cosmetic, never a source of truth.
//
// Token audit (BMI Brain rebrand, Phase 0): the 3 kinds below duplicated
// existing theme tokens exactly (chart-1/chart-2 in every one of morning/
// evening/night) and now reference them instead. The other 9 kinds still
// use one-off hex with no token equivalent - 12 automations genuinely
// need 12 visually distinct colors (more than the 5-slot --chart-* scale
// covers), and forcing them into 5 slots would lose the real distinction
// between automations that a rep relies on to tell cards apart at a
// glance. Promoting all 12 into proper theme-aware custom properties
// (defined per morning/evening/night, the way --chart-1..5 already are)
// is real design work - picking accessible, theme-consistent colors 12
// ways across 3 themes - scoped as a deliberate follow-up, not rushed
// into this pass.
const STYLES: Record<string, AutomationStyle> = {
  // Sales Acceleration
  followup_due: {
    icon: CalendarClock,
    color: "text-chart-2",
    chipBg: "border-chart-2/30 bg-chart-2/10",
    accent: "bg-chart-2",
    ring: "hover:border-chart-2/60",
  },
  signal_trigger: {
    icon: Zap,
    color: "text-chart-1",
    chipBg: "border-chart-1/30 bg-chart-1/10",
    accent: "bg-chart-1",
    ring: "hover:border-chart-1/60",
  },
  personal_touchpoint_due: {
    icon: Heart,
    color: "text-[#c2185b]",
    chipBg: "border-[#c2185b]/30 bg-[#c2185b]/10",
    accent: "bg-[#c2185b]",
    ring: "hover:border-[#c2185b]/60",
  },

  // Lead & Contact Capture
  inbound_contact_unmatched: {
    icon: UserPlus,
    color: "text-[#059669]",
    chipBg: "border-[#059669]/30 bg-[#059669]/10",
    accent: "bg-[#059669]",
    ring: "hover:border-[#059669]/60",
  },
  business_card_new: {
    icon: CreditCard,
    color: "text-[#7c3aed]",
    chipBg: "border-[#7c3aed]/30 bg-[#7c3aed]/10",
    accent: "bg-[#7c3aed]",
    ring: "hover:border-[#7c3aed]/60",
  },
  business_card_existing: {
    icon: UserCheck,
    color: "text-[#8b5cf6]",
    chipBg: "border-[#8b5cf6]/30 bg-[#8b5cf6]/10",
    accent: "bg-[#8b5cf6]",
    ring: "hover:border-[#8b5cf6]/60",
  },

  // CRM Data Hygiene & Intelligence
  ooo_ambiguous: {
    icon: CalendarClock,
    color: "text-[#0284c7]",
    chipBg: "border-[#0284c7]/30 bg-[#0284c7]/10",
    accent: "bg-[#0284c7]",
    ring: "hover:border-[#0284c7]/60",
  },
  departure_unconfirmed: {
    icon: UserMinus,
    color: "text-[#5b3e8f]",
    chipBg: "border-[#5b3e8f]/30 bg-[#5b3e8f]/10",
    accent: "bg-[#5b3e8f]",
    ring: "hover:border-[#5b3e8f]/60",
  },
  duplicate_contact: {
    icon: Users,
    color: "text-[#d97706]",
    chipBg: "border-[#d97706]/30 bg-[#d97706]/10",
    accent: "bg-[#d97706]",
    ring: "hover:border-[#d97706]/60",
  },
  bounce_uncertain: {
    icon: MailWarning,
    color: "text-chart-3",
    chipBg: "border-chart-3/30 bg-chart-3/10",
    accent: "bg-chart-3",
    ring: "hover:border-chart-3/60",
  },
  bounce_unmatched: {
    icon: MailQuestion,
    color: "text-[#c9611e]",
    chipBg: "border-[#c9611e]/30 bg-[#c9611e]/10",
    accent: "bg-[#c9611e]",
    ring: "hover:border-[#c9611e]/60",
  },
  returned_copy: {
    icon: BookOpen,
    color: "text-[#475569]",
    chipBg: "border-[#475569]/30 bg-[#475569]/10",
    accent: "bg-[#475569]",
    ring: "hover:border-[#475569]/60",
  },
};

const FALLBACK: AutomationStyle = {
  icon: Sparkles,
  color: "text-[#132c6b]",
  chipBg: "border-[#132c6b]/30 bg-[#132c6b]/10",
  accent: "bg-[#132c6b]",
  ring: "hover:border-[#132c6b]/60",
};

export function styleForKind(kind: string): AutomationStyle {
  return STYLES[kind] ?? FALLBACK;
}

/** Best-effort plain-English gloss for the handful of cron shapes this app
 * actually uses (see app/automations/scheduler.py's registered jobs) - not
 * a general cron parser. Falls back to the raw expression for anything it
 * doesn't recognize rather than guessing wrong. */
export function humanizeCron(cron: string): string {
  const everyNMinutes = cron.match(/^\*\/(\d+) \* \* \* \*$/);
  if (everyNMinutes) return `Every ${everyNMinutes[1]} minutes`;
  const everyNHours = cron.match(/^0 \*\/(\d+) \* \* \*$/);
  if (everyNHours) return `Every ${everyNHours[1]} hours`;
  if (cron === "0 0 * * *") return "Daily at midnight UTC";
  const hh = (h: string) => `${h.padStart(2, "0")}:00`;
  const daily = cron.match(/^0 (\d{1,2}) \* \* \*$/);
  if (daily) return `Daily at ${hh(daily[1])} UTC`;
  const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const weekly = cron.match(/^0 (\d{1,2}) \* \* ([0-6])$/);
  if (weekly) return `${DAYS[Number(weekly[2])]}s at ${hh(weekly[1])} UTC`;
  const weekdayHours = cron.match(/^0 (\d{1,2})-(\d{1,2}) \* \* 1-5$/);
  if (weekdayHours) return `Hourly, ${hh(weekdayHours[1])}–${hh(weekdayHours[2])} UTC weekdays`;
  return cron;
}
