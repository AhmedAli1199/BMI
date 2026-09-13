import {
  CalendarClock,
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
    color: "text-rose-600 dark:text-rose-400",
    chipBg: "bg-rose-500/10 border-rose-500/20",
    accent: "from-rose-600 to-rose-700",
    ring: "hover:border-rose-500/50",
  },
  bounce_unmatched: {
    icon: MailQuestion,
    color: "text-orange-600 dark:text-orange-400",
    chipBg: "bg-orange-500/10 border-orange-500/20",
    accent: "from-orange-600 to-orange-700",
    ring: "hover:border-orange-500/50",
  },
  ooo_ambiguous: {
    icon: CalendarClock,
    color: "text-blue-600 dark:text-blue-400",
    chipBg: "bg-blue-500/10 border-blue-500/20",
    accent: "from-blue-600 to-blue-700",
    ring: "hover:border-blue-500/50",
  },
  departure_unconfirmed: {
    icon: UserMinus,
    color: "text-violet-600 dark:text-violet-400",
    chipBg: "bg-violet-500/10 border-violet-500/20",
    accent: "from-violet-600 to-violet-700",
    ring: "hover:border-violet-500/50",
  },
};

const FALLBACK: AutomationStyle = {
  icon: Sparkles,
  color: "text-amber-600 dark:text-amber-400",
  chipBg: "bg-amber-500/10 border-amber-500/20",
  accent: "from-amber-600 to-amber-700",
  ring: "hover:border-amber-500/50",
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
