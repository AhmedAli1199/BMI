"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
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

export function PublicationSwitcher() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const currentSource = searchParams?.get("source_db") || "all";
  const active =
    PUBLICATIONS.find((p) => p.id === currentSource) || PUBLICATIONS[0];

  function selectPublication(id: string) {
    const params = new URLSearchParams(searchParams?.toString() ?? "");
    if (id === "all") {
      params.delete("source_db");
    } else {
      params.set("source_db", id);
    }
    params.delete("page");

    // If on contacts or companies page, keep path and append params
    if (pathname.startsWith("/contacts") || pathname.startsWith("/companies")) {
      const q = params.toString();
      router.push(`${pathname}${q ? `?${q}` : ""}`);
    } else {
      // Otherwise navigate to contacts filtered by that publication
      const q = params.toString();
      router.push(`/contacts${q ? `?${q}` : ""}`);
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="outline"
            size="sm"
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
            const isSelected = pub.id === currentSource;
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
