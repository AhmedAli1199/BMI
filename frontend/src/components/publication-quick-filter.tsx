"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { setPublicationFilter } from "@/lib/actions";
import { styleForColor } from "@/lib/publication-style";
import type { Publication } from "@/lib/types";

/** Same global cookie-backed filter as the header PublicationSwitcher (see
 * lib/publication.ts) - this is just a second, in-page place to set it, so
 * a list page's own "All / Onboard / Selling Travel / Prospects / ..." chips
 * and the header dropdown always agree instead of tracking separate state.
 * Renders from `publications` (fetched server-side) so a newly added
 * database appears as its own chip immediately. */
export function PublicationQuickFilter({
  current,
  publications,
}: {
  current: string;
  publications: Publication[];
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function select(id: string) {
    startTransition(async () => {
      await setPublicationFilter(id);
      router.refresh();
    });
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Badge
        variant={!current ? "default" : "outline"}
        onClick={() => select("")}
        className={`cursor-pointer text-xs font-medium px-3 py-1 ${pending ? "opacity-60" : ""}`}
      >
        All Titles
      </Badge>
      {publications.map((pub) => {
        const isActive = current === pub.slug;
        const style = styleForColor(pub.color);
        return (
          <Badge
            key={pub.slug}
            variant={isActive ? "default" : "outline"}
            onClick={() => select(pub.slug)}
            className={`cursor-pointer text-xs font-medium px-3 py-1 ${isActive ? style.activeBadge : ""} ${
              pending ? "opacity-60" : ""
            }`}
          >
            {pub.name}
          </Badge>
        );
      })}
    </div>
  );
}
