import Link from "next/link";
import type { Deadline } from "@/lib/editorial-types";
import { issueLabel } from "@/lib/editorial-types";
import { brandColor } from "@/components/rate-card/brand-style";
import { TYPE_META, countdownColor, daysLabel, fmtDay } from "@/components/editorial/editorial-ui";

function groupName(days: number, iso: string): string {
  if (days < 0) return "Just gone";
  if (days === 0) return "Today";
  const d = new Date(iso + "T00:00:00");
  const now = new Date();
  const dow = (now.getDay() + 6) % 7; // Monday = 0
  if (days <= 6 - dow) return "This week";
  if (days <= 13 - dow) return "Next week";
  return d.toLocaleDateString("en-GB", { month: "long", year: "numeric" });
}

/** What's due, soonest first, grouped by week then month. */
export function DeadlinesList({ items }: { items: Deadline[] }) {
  if (!items.length) {
    return <p className="rounded-xl border border-dashed border-border/80 bg-card/60 px-6 py-10 text-center text-sm text-muted-foreground">Nothing due in this period. Add issue dates in the year planner and their deadlines will show here.</p>;
  }
  const groups: { name: string; items: Deadline[] }[] = [];
  for (const it of items) {
    const name = groupName(it.days, it.date);
    if (groups.at(-1)?.name !== name) groups.push({ name, items: [] });
    groups.at(-1)!.items.push(it);
  }
  return (
    <div className="flex flex-col gap-5">
      {groups.map((g) => (
        <section key={g.name} aria-labelledby={`g-${g.name}`} className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-2xs">
          <h2 id={`g-${g.name}`} className="border-b border-border/70 px-4 py-2.5 text-sm font-bold">{g.name}</h2>
          <ul className="divide-y divide-border/60">
            {g.items.map((it, k) => {
              const meta = TYPE_META[it.type];
              const urgent = it.type !== "publication" && it.type !== "event";
              return (
                <li key={`${it.issue.id}-${it.type}-${k}`} className="grid grid-cols-[6.5rem_minmax(0,1fr)_auto] items-center gap-3 px-4 py-2.5 sm:grid-cols-[7.5rem_14rem_minmax(0,1fr)_auto]">
                  <span className="text-sm font-semibold tabular-nums">{fmtDay(it.date)}</span>
                  <span className="hidden items-center gap-1.5 text-xs font-medium sm:flex"><meta.Icon className="size-3.5 shrink-0" style={{ color: meta.color }} aria-hidden="true" />{it.what}</span>
                  <span className="min-w-0">
                    <span className="flex items-center gap-2">
                      <span className="masthead-rule w-3 shrink-0" style={{ background: brandColor(it.issue.brand) }} aria-hidden="true" />
                      <Link href={`/editorial/issues/${it.issue.id}`} className="truncate text-sm font-semibold hover:underline">{it.issue.brand_name}: {issueLabel(it.issue)}</Link>
                    </span>
                    <span className="block truncate text-xs text-muted-foreground sm:hidden">{it.what}</span>
                    {it.issue.theme && <span className="hidden truncate text-xs text-muted-foreground sm:block">{it.issue.theme}</span>}
                  </span>
                  <span className="text-right text-xs font-semibold whitespace-nowrap" style={{ color: urgent ? countdownColor(it.days) : undefined }}>{daysLabel(it.days)}</span>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
