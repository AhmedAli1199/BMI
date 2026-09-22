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

export type AutomationCategory = "sales" | "capture" | "hygiene";

export type CategoryMeta = {
  id: AutomationCategory;
  label: string;
  tagline: string;
  badgeColor: string;
};

export const AUTOMATION_CATEGORIES: CategoryMeta[] = [
  {
    id: "sales",
    label: "Sales Acceleration & Follow-ups",
    tagline: "Drive deal velocity, timely reach-outs, and commercial revenue continuity",
    badgeColor: "bg-blue-500/10 text-blue-600 border-blue-500/20",
  },
  {
    id: "capture",
    label: "Lead & Contact Capture",
    tagline: "Ingest prospective advertisers and agency contacts from inbound mail and field events",
    badgeColor: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20",
  },
  {
    id: "hygiene",
    label: "CRM Data Hygiene & Intelligence",
    tagline: "Keep 70,000+ contact records accurate, deduplicated, and deliverable",
    badgeColor: "bg-purple-500/10 text-purple-600 border-purple-500/20",
  },
];

export function categoryForKind(kind: string): AutomationCategory {
  switch (kind) {
    case "followup_due":
    case "signal_trigger":
    case "personal_touchpoint_due":
      return "sales";
    case "inbound_contact_unmatched":
    case "business_card_new":
    case "business_card_existing":
      return "capture";
    default:
      return "hygiene";
  }
}

// Keyed by the backend's registry `kind` string (see
// app/automations/registry.py). Purely cosmetic, never a source of truth.
const STYLES: Record<string, AutomationStyle> = {
  // Sales Acceleration
  followup_due: {
    icon: CalendarClock,
    color: "text-[#0099e5]",
    chipBg: "border-[#0099e5]/30 bg-[#0099e5]/10",
    accent: "bg-[#0099e5]",
    ring: "hover:border-[#0099e5]/60",
  },
  signal_trigger: {
    icon: Zap,
    color: "text-[#132c6b]",
    chipBg: "border-[#132c6b]/30 bg-[#132c6b]/10",
    accent: "bg-[#132c6b]",
    ring: "hover:border-[#132c6b]/60",
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
    color: "text-[#c0392b]",
    chipBg: "border-[#c0392b]/30 bg-[#c0392b]/10",
    accent: "bg-[#c0392b]",
    ring: "hover:border-[#c0392b]/60",
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
  return cron;
}
