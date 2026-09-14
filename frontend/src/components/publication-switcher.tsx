"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { BookOpen, Check, ChevronDown } from "lucide-react";
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
import { iconForKey, styleForColor } from "@/lib/publication-style";
import type { Publication } from "@/lib/types";

const ALL: Publication = {
  id: "all",
  slug: "",
  name: "All BMI Publications",
  description: "Combined across all magazine titles",
  color: "amber",
  icon: "book",
};

/**
 * The single control for "which publication's data am I looking at" -
 * persists via a cookie (lib/publication.ts), not a URL search param, so it
 * survives navigating to a completely different tab (Dashboard -> Contacts
 * -> Groups) instead of resetting on every route change. Selecting a
 * publication never navigates - it just re-filters whatever page you're
 * already on, including the dashboard itself.
 *
 * Renders entirely from `publications` (fetched server-side from
 * /api/publications by the app layout) - adding a database via
 * PublicationFormDialog shows up here with no code change.
 */
export function PublicationSwitcher({
  current,
  publications,
}: {
  current: string;
  publications: Publication[];
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  const options = [ALL, ...publications];
  const active = options.find((p) => p.slug === current) || ALL;
  const activeDot = styleForColor(active.color).dot;

  function selectPublication(slug: string) {
    startTransition(async () => {
      await setPublicationFilter(slug);
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
            <span className={`size-2 rounded-full ${activeDot}`} />
            <span className="max-w-[140px] truncate text-xs font-semibold sm:max-w-none">
              {active.slug ? active.name : "All Titles"}
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
          {options.map((pub) => {
            const isSelected = pub.slug === current;
            const Icon = pub.slug ? iconForKey(pub.icon) : BookOpen;
            const style = styleForColor(pub.color);
            return (
              <DropdownMenuItem
                key={pub.slug || "all"}
                onClick={() => selectPublication(pub.slug)}
                className="flex items-start gap-3 py-2.5 cursor-pointer"
              >
                <div className={`mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md border ${style.chipBg}`}>
                  <Icon className="size-3.5" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold">{pub.name}</span>
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
