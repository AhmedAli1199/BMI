"use client";

import { useRouter } from "next/navigation";
import type { EditionSummary } from "@/lib/sales-types";
import { fmtDate } from "@/components/sales/sales-ui";

const selectCls = "h-9 w-full rounded-lg border border-input bg-card px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

/** Two pickers - any edition against any other, grouped by title, newest first. */
export function ComparePicker({ editions, a, b }: { editions: EditionSummary[]; a: string | null; b: string | null }) {
  const router = useRouter();
  const byTitle = new Map<string, { name: string; items: EditionSummary[] }>();
  for (const e of [...editions].sort((x, y) => (y.edition_date ?? "").localeCompare(x.edition_date ?? ""))) {
    const g = byTitle.get(e.title.id) ?? { name: e.title.name, items: [] };
    g.items.push(e);
    byTitle.set(e.title.id, g);
  }
  const go = (na: string | null, nb: string | null) => {
    const p = new URLSearchParams();
    if (na) p.set("a", na);
    if (nb) p.set("b", nb);
    router.push(`/sales/compare?${p}`);
  };
  const options = (
    <>
      <option value="">Choose an edition…</option>
      {[...byTitle.values()].map((g) => (
        <optgroup key={g.name} label={g.name}>
          {g.items.map((e) => (
            <option key={e.id} value={e.id}>
              {e.label}{e.edition_date ? ` - ${fmtDate(e.edition_date)}` : ""}
            </option>
          ))}
        </optgroup>
      ))}
    </>
  );
  return (
    <div className="grid gap-3 sm:grid-cols-[1fr_auto_1fr] sm:items-end">
      <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
        This edition
        <select className={selectCls} value={a ?? ""} onChange={(e) => go(e.target.value || null, b)}>{options}</select>
      </label>
      <span className="hidden pb-2 text-sm text-muted-foreground sm:block">against</span>
      <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
        Compared with
        <select className={selectCls} value={b ?? ""} onChange={(e) => go(a, e.target.value || null)}>{options}</select>
      </label>
    </div>
  );
}
