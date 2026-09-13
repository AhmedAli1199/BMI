"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { setPublicationFilter } from "@/lib/actions";

const OPTIONS = [
  { id: "", label: "All Titles", activeClass: "" },
  { id: "onboard", label: "Onboard Hospitality", activeClass: "bg-blue-600 text-white hover:bg-blue-700" },
  { id: "sellingtravel", label: "Selling Travel", activeClass: "bg-emerald-600 text-white hover:bg-emerald-700" },
  { id: "prospects", label: "Prospects DB", activeClass: "bg-amber-600 text-white hover:bg-amber-700" },
];

/** Same global cookie-backed filter as the header PublicationSwitcher (see
 * lib/publication.ts) - this is just a second, in-page place to set it, so
 * a list page's own "All / Onboard / Selling Travel / Prospects" chips and
 * the header dropdown always agree instead of tracking separate state. */
export function PublicationQuickFilter({ current }: { current: string }) {
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
      {OPTIONS.map((opt) => {
        const isActive = current === opt.id;
        return (
          <Badge
            key={opt.id || "all"}
            variant={isActive ? "default" : "outline"}
            onClick={() => select(opt.id)}
            className={`cursor-pointer text-xs font-medium px-3 py-1 ${isActive ? opt.activeClass : ""} ${
              pending ? "opacity-60" : ""
            }`}
          >
            {opt.label}
          </Badge>
        );
      })}
    </div>
  );
}
