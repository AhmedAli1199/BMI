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
  chipBg: string; // outlined icon mark - border + text colour, no fill
  accent: string; // solid masthead-rule colour for a card's top strip
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

/* Solid, print-masthead colours (not Tailwind's default /500 candy hues) -
   each one is deliberately closer to what you'd actually see on a BMI
   cover line than a generic SaaS palette swatch. */
const COLOR_STYLES: Record<string, PublicationColorStyle> = {
  blue: {
    dot: "bg-[#0099e5]",
    chipBg: "border-[#0099e5] text-[#0077b3]",
    accent: "bg-[#0099e5]",
    activeBadge: "bg-[#0099e5] text-white hover:bg-[#0084c9]",
  },
  emerald: {
    dot: "bg-[#1e7a52]",
    chipBg: "border-[#1e7a52] text-[#1e7a52]",
    accent: "bg-[#1e7a52]",
    activeBadge: "bg-[#1e7a52] text-white hover:bg-[#186142]",
  },
  amber: {
    dot: "bg-[#b8791a]",
    chipBg: "border-[#b8791a] text-[#96620f]",
    accent: "bg-[#b8791a]",
    activeBadge: "bg-[#b8791a] text-white hover:bg-[#966213]",
  },
  violet: {
    dot: "bg-[#5b3e8f]",
    chipBg: "border-[#5b3e8f] text-[#5b3e8f]",
    accent: "bg-[#5b3e8f]",
    activeBadge: "bg-[#5b3e8f] text-white hover:bg-[#4a3273]",
  },
  rose: {
    dot: "bg-[#c0392b]",
    chipBg: "border-[#c0392b] text-[#c0392b]",
    accent: "bg-[#c0392b]",
    activeBadge: "bg-[#c0392b] text-white hover:bg-[#a32f23]",
  },
  cyan: {
    dot: "bg-[#0a7f8c]",
    chipBg: "border-[#0a7f8c] text-[#0a7f8c]",
    accent: "bg-[#0a7f8c]",
    activeBadge: "bg-[#0a7f8c] text-white hover:bg-[#086671]",
  },
  orange: {
    dot: "bg-[#c9611e]",
    chipBg: "border-[#c9611e] text-[#a44f18]",
    accent: "bg-[#c9611e]",
    activeBadge: "bg-[#c9611e] text-white hover:bg-[#a44f18]",
  },
  slate: {
    dot: "bg-[#132c6b]",
    chipBg: "border-[#132c6b] text-[#132c6b]",
    accent: "bg-[#132c6b]",
    activeBadge: "bg-[#132c6b] text-white hover:bg-[#0e214f]",
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
