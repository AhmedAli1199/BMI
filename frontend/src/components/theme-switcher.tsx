"use client";
/* eslint-disable react-hooks/set-state-in-effect -- standard hydration-safe
   "mounted" flag; the theme is only knowable client-side. */

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Sun, Sunset, Moon, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const THEMES = [
  { value: "morning", label: "Morning", description: "Bright & warm", icon: Sun },
  { value: "evening", label: "Evening", description: "Dusk & dimmed", icon: Sunset },
  { value: "night", label: "Night", description: "Dark & quiet", icon: Moon },
] as const;

export function ThemeSwitcher() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const current = THEMES.find((t) => t.value === theme) ?? THEMES[0];
  const Icon = current.icon;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button variant="outline" size="sm" className="gap-2">
            <Icon className="size-4" />
            {mounted ? current.label : ""}
          </Button>
        }
      />
      <DropdownMenuContent align="end" className="w-52">
        {THEMES.map((t) => {
          const ItemIcon = t.icon;
          const active = mounted && theme === t.value;
          return (
            <DropdownMenuItem key={t.value} onClick={() => setTheme(t.value)} className="gap-2">
              <ItemIcon className="size-4" />
              <div className="flex flex-col">
                <span className="text-sm">{t.label}</span>
                <span className="text-xs text-muted-foreground">{t.description}</span>
              </div>
              {active && <Check className="ml-auto size-4" />}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
