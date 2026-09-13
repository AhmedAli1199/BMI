import { cn } from "@/lib/utils";

// A handful of accent tints pulled from the theme's chart palette so avatars
// stay in-gamut across all three themes instead of hardcoding colors that'd
// clash at night. Picked deterministically per name so the same person/
// company always gets the same color - a small thing, but it's what makes a
// list of rows start reading as *records* instead of a spreadsheet.
const PALETTE = [
  "bg-chart-1/15 text-chart-1",
  "bg-chart-2/15 text-chart-2",
  "bg-chart-3/15 text-chart-3",
  "bg-chart-4/15 text-chart-4",
  "bg-chart-5/15 text-chart-5",
];

function hashIndex(seed: string, mod: number) {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  return h % mod;
}

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function EntityAvatar({
  name,
  className,
  square = false,
}: {
  name: string;
  className?: string;
  /** Companies get a rounded-square mark, people get a circle - a common
   * CRM convention (Salesforce, HubSpot) that lets you tell record types
   * apart at a glance even before reading the row. */
  square?: boolean;
}) {
  const label = name || "?";
  const color = PALETTE[hashIndex(label, PALETTE.length)];
  return (
    <span
      className={cn(
        "flex size-8 shrink-0 items-center justify-center text-xs font-semibold",
        square ? "rounded-md" : "rounded-full",
        color,
        className
      )}
      aria-hidden="true"
    >
      {initialsOf(label)}
    </span>
  );
}
