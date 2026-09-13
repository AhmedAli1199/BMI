"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { BookOpen, Check, ChevronDown, Compass, Plane, Sparkles } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { setPublicationFilter } from "@/lib/actions";

export const PUBLICATIONS = [
  {
    id: "all",
    label: "All BMI Publications",
    short: "All Titles",
    description: "Combined across all magazine titles",
    icon: BookOpen,
    accent: "bg-amber-500/20 text-amber-600 border-amber-500/30",
    dot: "bg-amber-500",
  },
  {
    id: "onboard",
    label: "Onboard Hospitality",
    short: "Onboard Hospitality",
    description: "Inflight catering, retail & passenger experience",
    icon: Plane,
    accent: "bg-blue-500/20 text-blue-500 border-blue-500/30",
    dot: "bg-blue-500",
  },
  {
    id: "sellingtravel",
    label: "Selling Travel",
    short: "Selling Travel",
    description: "UK travel trade, agents & destination guides",
    icon: Compass,
    accent: "bg-emerald-500/20 text-emerald-500 border-emerald-500/30",
    dot: "bg-emerald-500",
  },
  {
    id: "prospects",
    label: "Prospects & Intelligence",
    short: "Prospects DB",
    description: "Unclaimed prospects & automated lead discovery",
    icon: Sparkles,
    accent: "bg-orange-500/20 text-orange-500 border-orange-500/30",
    dot: "bg-orange-500",
  },
] as const;

/**
 * The single control for "which publication's data am I looking at" -
 * persists via a cookie (lib/publication.ts), not a URL search param, so it
 * survives navigating to a completely different tab (Dashboard -> Contacts
 * -> Groups) instead of resetting on every route change. Selecting a
 * publication never navigates - it just re-filters whatever page you're
 * already on, including the dashboard itself.
 */
export function PublicationSwitcher({ current }: { current: string }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  const active = PUBLICATIONS.find((p) => p.id === (current || "all")) || PUBLICATIONS[0];

  function selectPublication(id: string) {
    startTransition(async () => {
      await setPublicationFilter(id === "all" ? "" : id);
      router.refresh();
    });
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="outline"
            size="sm"
            disabled={pending}
            className="h-8 gap-2 border-sidebar-border bg-sidebar-accent/50 px-2.5 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground cursor-pointer"
          >
            <span className={`size-2 rounded-full ${active.dot}`} />
            <span className="max-w-[140px] truncate text-xs font-semibold sm:max-w-none">
              {active.short}
            </span>
            <ChevronDown className="size-3.5 opacity-60" />
          </Button>
        }
      />
      <DropdownMenuContent align="start" className="w-72">
        <DropdownMenuGroup>
          <DropdownMenuLabel className="text-xs text-muted-foreground px-2 py-1.5 font-medium">
            Publication Context
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          {PUBLICATIONS.map((pub) => {
            const isSelected = pub.id === (current || "all");
            const Icon = pub.icon;
            return (
              <DropdownMenuItem
                key={pub.id}
                onClick={() => selectPublication(pub.id)}
                className="flex items-start gap-3 py-2.5 cursor-pointer"
              >
                <div
                  className={`mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md border ${pub.accent}`}
                >
                  <Icon className="size-3.5" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold">{pub.label}</span>
                    {isSelected && <Check className="size-3.5 text-primary" />}
                  </div>
                  <p className="line-clamp-1 text-[11px] text-muted-foreground">
                    {pub.description}
                  </p>
                </div>
              </DropdownMenuItem>
            );
          })}
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
