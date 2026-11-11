"use client";

import { useRouter, useSearchParams } from "next/navigation";

/** The Sales overview's Title drop-down (Craig, feedback #22): opens on the salesperson's own titles; any other title,
 * or all of them, is one pick away. The choice goes in the address, so the year switches keep it. */
export function TitleFilter({ titles, current, hasMine }: { titles: { id: string; name: string }[]; current: string; hasMine: boolean }) {
  const router = useRouter();
  const params = useSearchParams();
  return (
    <label className="flex shrink-0 items-center gap-1.5 text-xs font-semibold text-muted-foreground">
      Title
      <select
        aria-label="Title"
        className="h-8 w-48 max-w-full rounded-md border border-input bg-background px-2 text-xs font-semibold text-foreground"
        value={current}
        onChange={(e) => {
          const p = new URLSearchParams(params.toString());
          p.set("titles", e.target.value);
          router.push(`/sales?${p.toString()}`, { scroll: false });
        }}
      >
        {hasMine && <option value="mine">My titles</option>}
        <option value="all">All titles</option>
        {titles.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
      </select>
    </label>
  );
}
