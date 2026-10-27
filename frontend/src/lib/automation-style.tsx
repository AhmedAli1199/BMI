import {
  BookOpen,
  UserRoundCheck,
  Link2,
  ShieldCheck,
  GitPullRequestArrow,
  CalendarRange,
  Receipt,
  MailPlus,
  ClipboardCheck,
  FileInput,
  LifeBuoy,
  Mic,
  ReceiptText,
  RefreshCcw,
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

// Revenue & Orders (Sales Order Register)
Object.assign(STYLES, {
  renewal_due: {
    icon: RefreshCcw,
    color: "text-chart-2",
    chipBg: "border-chart-2/30 bg-chart-2/10",
    accent: "bg-chart-2",
    ring: "hover:border-chart-2/60",
  },
  sor_invoice_missing: {
    icon: ReceiptText,
    color: "text-[#b45309]",
    chipBg: "border-[#b45309]/30 bg-[#b45309]/10",
    accent: "bg-[#b45309]",
    ring: "hover:border-[#b45309]/60",
  },
  sor_client_match: {
    icon: Link2,
    color: "text-chart-1",
    chipBg: "border-chart-1/30 bg-chart-1/10",
    accent: "bg-chart-1",
    ring: "hover:border-chart-1/60",
  },
  sor_invoice_match: {
    icon: Link2,
    color: "text-chart-4",
    chipBg: "border-chart-4/30 bg-chart-4/10",
    accent: "bg-chart-4",
    ring: "hover:border-chart-4/60",
  },
  save_the_sale: {
    icon: LifeBuoy,
    color: "text-chart-2",
    chipBg: "border-chart-2/30 bg-chart-2/10",
    accent: "bg-chart-2",
    ring: "hover:border-chart-2/60",
  },
  call_notes: {
    icon: Mic,
    color: "text-chart-3",
    chipBg: "border-chart-3/30 bg-chart-3/10",
    accent: "bg-chart-3",
    ring: "hover:border-chart-3/60",
  },
  proposal_request: {
    icon: MailPlus,
    color: "text-chart-1",
    chipBg: "border-chart-1/30 bg-chart-1/10",
    accent: "bg-chart-1",
    ring: "hover:border-chart-1/60",
  },
  invoice_due: {
    icon: Receipt,
    color: "text-chart-2",
    chipBg: "border-chart-2/30 bg-chart-2/10",
    accent: "bg-chart-2",
    ring: "hover:border-chart-2/60",
  },
  allocation_due: {
    icon: CalendarRange,
    color: "text-chart-3",
    chipBg: "border-chart-3/30 bg-chart-3/10",
    accent: "bg-chart-3",
    ring: "hover:border-chart-3/60",
  },
  sor_issue_check: {
    icon: ClipboardCheck,
    color: "text-chart-2",
    chipBg: "border-chart-2/30 bg-chart-2/10",
    accent: "bg-chart-2",
    ring: "hover:border-chart-2/60",
  },
  subscription_signup: {
    icon: UserPlus,
    color: "text-chart-1",
    chipBg: "border-chart-1/30 bg-chart-1/10",
    accent: "bg-chart-1",
    ring: "hover:border-chart-1/60",
  },
  online_booking: {
    icon: FileInput,
    color: "text-chart-4",
    chipBg: "border-chart-4/30 bg-chart-4/10",
    accent: "bg-chart-4",
    ring: "hover:border-chart-4/60",
  },
  booking_change: {
    icon: GitPullRequestArrow,
    color: "text-chart-5",
    chipBg: "border-chart-5/30 bg-chart-5/10",
    accent: "bg-chart-5",
    ring: "hover:border-chart-5/60",
  },
  client_owner: {
    icon: UserRoundCheck,
    color: "text-chart-4",
    chipBg: "border-chart-4/30 bg-chart-4/10",
    accent: "bg-chart-4",
    ring: "hover:border-chart-4/60",
  },
  order_check: {
    icon: ShieldCheck,
    color: "text-chart-5",
    chipBg: "border-chart-5/30 bg-chart-5/10",
    accent: "bg-chart-5",
    ring: "hover:border-chart-5/60",
  },
} satisfies Record<string, AutomationStyle>);

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

const CRON_DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

/** A UTC time of day as UK clock time today (GMT in winter, BST in summer), plus how many days it moved. */
function ukTime(hour: number, minute: number, now: Date): { text: string; shift: number } {
  const at = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), hour, minute));
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/London", hour: "2-digit", minute: "2-digit", day: "numeric", hourCycle: "h23",
  }).formatToParts(at);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  const ukDay = Number(get("day"));
  const shift = ukDay === at.getUTCDate() ? 0 : 1; // the UK clock is level with UTC or an hour ahead
  return { text: `${get("hour")}:${get("minute")}`, shift };
}

function cronDays(dow: string, shift: number): string | null {
  const name = (d: string) => {
    const n = d === "7" ? 0 : Number(d);
    return Number.isInteger(n) && n >= 0 && n <= 6 ? CRON_DAYS[(n + shift + 7) % 7] : null;
  };
  const list = dow.includes("-") ? dow.split("-") : dow.split(",");
  const names = list.map(name);
  if (names.some((n) => n === null)) return null;
  if (dow.includes("-")) return `${names[0]} to ${names[1]}`;
  return names.length === 1 ? `every ${names[0]}` : `on ${names.join(", ")}`;
}

/** A job's schedule in plain words, in UK time. Jobs run on UTC cron times (see backend
 * app/automations/scheduler.py); this turns every shape the app uses into words and converts the
 * time to the UK clock for today's date (an hour later in summer). Mirrors the backend's
 * app/automations/status.py schedule_words. Never shows the raw code. */
export function humanizeCron(cron: string, now: Date = new Date()): string {
  const custom = "On a custom schedule";
  const fields = cron.trim().split(/\s+/);
  if (fields.length !== 5) return custom;
  const [minute, hour, dom, month, dow] = fields;
  if (month !== "*") return custom;
  const isNum = (v: string) => /^\d+$/.test(v);
  if (minute === "*" && hour === "*" && dom === "*" && dow === "*") return "Every minute";
  if (/^\*\/\d+$/.test(minute) && hour === "*" && dom === "*" && dow === "*") {
    const n = minute.slice(2);
    return n === "1" ? "Every minute" : `Every ${n} minutes`;
  }
  if (isNum(minute) && hour === "*" && dom === "*" && dow === "*") {
    return Number(minute) === 0 ? "Every hour, on the hour" : `Every hour at ${Number(minute)} minutes past`;
  }
  if (isNum(minute) && /^\*\/\d+$/.test(hour) && dom === "*" && dow === "*") return `Every ${hour.slice(2)} hours`;
  if (!isNum(minute)) return custom;
  const m = Number(minute);
  let when: string;
  let shift = 0;
  if (/^\d+(,\d+)*$/.test(hour)) {
    const times = hour.split(",").map((h) => ukTime(Number(h), m, now));
    shift = times[0].shift;
    when = `at ${times.map((t) => t.text).join(", ")} UK time`;
  } else if (/^\d+-\d+$/.test(hour)) {
    const [first, last] = hour.split("-").map(Number);
    const start = ukTime(first, m, now);
    shift = start.shift;
    when = `every hour from ${start.text} to ${ukTime(last, m, now).text} UK time`;
  } else {
    return custom;
  }
  let out: string;
  if (dow !== "*") {
    const days = cronDays(dow, shift);
    if (!days) return custom;
    out = `${when}, ${days}`;
  } else if (dom !== "*") {
    out = `${when}, on day ${dom} of the month`;
  } else {
    out = when.startsWith("at ") ? `Every day ${when}` : when;
  }
  return out.charAt(0).toUpperCase() + out.slice(1);
}
