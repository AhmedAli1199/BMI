import {
  CalendarClock,
  Heart,
  MailQuestion,
  MailWarning,
  Sparkles,
  UserMinus,
  type LucideIcon,
} from "lucide-react";

export type AutomationStyle = {
  icon: LucideIcon;
  color: string; // icon/accent text color
  chipBg: string; // icon chip background + border
  accent: string; // gradient stop classes for the card's top bar
  ring: string; // hover border color
};

// Keyed by the backend's registry `kind` string (see
// app/automations/registry.py). A kind not listed here (a brand-new
// automation someone just registered) still renders correctly via
// FALLBACK below - this is purely cosmetic, never a source of truth.
const STYLES: Record<string, AutomationStyle> = {
  bounce_uncertain: {
    icon: MailWarning,
    color: "text-[#c0392b]",
    chipBg: "border-[#c0392b]",
    accent: "bg-[#c0392b]",
    ring: "hover:border-[#c0392b]/60",
  },
  bounce_unmatched: {
    icon: MailQuestion,
    color: "text-[#c9611e]",
    chipBg: "border-[#c9611e]",
    accent: "bg-[#c9611e]",
    ring: "hover:border-[#c9611e]/60",
  },
  ooo_ambiguous: {
    icon: CalendarClock,
    color: "text-[#0099e5]",
    chipBg: "border-[#0099e5]",
    accent: "bg-[#0099e5]",
    ring: "hover:border-[#0099e5]/60",
  },
  departure_unconfirmed: {
    icon: UserMinus,
    color: "text-[#5b3e8f]",
    chipBg: "border-[#5b3e8f]",
    accent: "bg-[#5b3e8f]",
    ring: "hover:border-[#5b3e8f]/60",
  },
  personal_touchpoint_due: {
    icon: Heart,
    color: "text-[#c2185b]",
    chipBg: "border-[#c2185b]",
    accent: "bg-[#c2185b]",
    ring: "hover:border-[#c2185b]/60",
  },
};

const FALLBACK: AutomationStyle = {
  icon: Sparkles,
  color: "text-[#132c6b]",
  chipBg: "border-[#132c6b]",
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
