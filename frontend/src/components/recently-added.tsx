"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Sparkles, X } from "lucide-react";
import { listRecent, removeRecent, RECENT_CHANGED, type RecentAdd, type RecentKind } from "@/lib/recent-adds";

/** "You added today": what you've just added, above the A-Z list, so you can carry on editing without searching
 * for it (Craig, feedback #18). Only you see it; it clears when you sign out. */
export function RecentlyAdded({ kind }: { kind: RecentKind }) {
  const [items, setItems] = useState<RecentAdd[]>([]);
  useEffect(() => {
    const load = () => setItems(listRecent(kind));
    load();
    window.addEventListener(RECENT_CHANGED, load);
    window.addEventListener("storage", load);
    return () => {
      window.removeEventListener(RECENT_CHANGED, load);
      window.removeEventListener("storage", load);
    };
  }, [kind]);

  if (!items.length) return null;
  const base = kind === "company" ? "/companies" : "/contacts";
  return (
    <section aria-label="You added today" className="rounded-lg border border-primary/25 bg-primary/5 px-3 py-2.5">
      <h2 className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-primary">
        <Sparkles className="size-3.5" /> You added today
        <span className="font-normal text-muted-foreground">· just for you, until you sign out</span>
      </h2>
      <ul className="flex flex-wrap gap-1.5">
        {items.map((i) => (
          <li key={i.id} className="inline-flex items-center gap-1 rounded-full border border-border bg-card py-0.5 pl-2.5 pr-1 text-xs">
            <Link href={`${base}/${i.id}`} className="font-medium text-foreground hover:underline">{i.name}</Link>
            <span className="rounded bg-primary/10 px-1 text-[10px] font-semibold text-primary">new</span>
            <button type="button" onClick={() => removeRecent(kind, i.id)} aria-label={`Hide ${i.name} from this list`} className="rounded-full p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground">
              <X className="size-3" />
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
