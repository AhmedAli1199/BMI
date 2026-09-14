import {
  BookOpen,
  Building2,
  Compass,
  Globe2,
  Newspaper,
  Plane,
  Rss,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

/** A fixed, safe palette a Publication's `color`/`icon` key maps into -
 * never raw CSS, so a bad/unknown value from the database can't inject
 * anything, it just falls back gracefully (see COLOR_STYLES/ICONS below). */
export type PublicationColorStyle = {
  dot: string;
  chipBg: string; // icon chip background + border + text
  accent: string; // gradient stop classes for a card's top bar
  activeBadge: string; // solid badge classes when this publication is the active filter
};

export const COLOR_OPTIONS = [
  "blue",
  "emerald",
  "amber",
  "violet",
  "rose",
  "cyan",
  "orange",
  "slate",
] as const;

const COLOR_STYLES: Record<string, PublicationColorStyle> = {
  blue: {
    dot: "bg-blue-500",
    chipBg: "bg-blue-500/10 border-blue-500/20 text-blue-600",
    accent: "from-blue-600 to-blue-700",
    activeBadge: "bg-blue-600 text-white hover:bg-blue-700",
  },
  emerald: {
    dot: "bg-emerald-500",
    chipBg: "bg-emerald-500/10 border-emerald-500/20 text-emerald-600",
    accent: "from-emerald-600 to-emerald-700",
    activeBadge: "bg-emerald-600 text-white hover:bg-emerald-700",
  },
  amber: {
    dot: "bg-amber-500",
    chipBg: "bg-amber-500/10 border-amber-500/20 text-amber-600",
    accent: "from-amber-600 to-amber-700",
    activeBadge: "bg-amber-600 text-white hover:bg-amber-700",
  },
  violet: {
    dot: "bg-violet-500",
    chipBg: "bg-violet-500/10 border-violet-500/20 text-violet-600",
    accent: "from-violet-600 to-violet-700",
    activeBadge: "bg-violet-600 text-white hover:bg-violet-700",
  },
  rose: {
    dot: "bg-rose-500",
    chipBg: "bg-rose-500/10 border-rose-500/20 text-rose-600",
    accent: "from-rose-600 to-rose-700",
    activeBadge: "bg-rose-600 text-white hover:bg-rose-700",
  },
  cyan: {
    dot: "bg-cyan-500",
    chipBg: "bg-cyan-500/10 border-cyan-500/20 text-cyan-600",
    accent: "from-cyan-600 to-cyan-700",
    activeBadge: "bg-cyan-600 text-white hover:bg-cyan-700",
  },
  orange: {
    dot: "bg-orange-500",
    chipBg: "bg-orange-500/10 border-orange-500/20 text-orange-600",
    accent: "from-orange-600 to-orange-700",
    activeBadge: "bg-orange-600 text-white hover:bg-orange-700",
  },
  slate: {
    dot: "bg-slate-500",
    chipBg: "bg-slate-500/10 border-slate-500/20 text-slate-600",
    accent: "from-slate-600 to-slate-700",
    activeBadge: "bg-slate-600 text-white hover:bg-slate-700",
  },
};

export function styleForColor(color: string): PublicationColorStyle {
  return COLOR_STYLES[color] ?? COLOR_STYLES.slate;
}

export const ICON_OPTIONS = ["newspaper", "plane", "compass", "sparkles", "globe", "building", "rss", "book"] as const;

const ICONS: Record<string, LucideIcon> = {
  newspaper: Newspaper,
  plane: Plane,
  compass: Compass,
  sparkles: Sparkles,
  globe: Globe2,
  building: Building2,
  rss: Rss,
  book: BookOpen,
};

export function iconForKey(icon: string): LucideIcon {
  return ICONS[icon] ?? Newspaper;
}
