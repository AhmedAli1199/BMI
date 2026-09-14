"use client";

import { useState, useTransition } from "react";
import { Check, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { updateUserPreferences } from "@/lib/actions";
import type { PreferenceDef } from "@/lib/types";

/**
 * Renders ANY preference definition purely from data - one card per
 * PreferenceDef, one selectable tile per option, each showing its own
 * label + full explanation so picking one never requires guessing what it
 * actually does. A brand-new preference (backend/app/preferences.py) gets
 * a working, on-brand UI here with zero frontend changes, same as the
 * automations review-queue's kind/action registry.
 */
export function PreferenceGroup({
  def,
  value,
  userId,
}: {
  def: PreferenceDef;
  value: string;
  userId: string | null;
}) {
  const [selected, setSelected] = useState(value);
  const [pending, startTransition] = useTransition();

  function choose(optionValue: string) {
    if (optionValue === selected || pending) return;
    if (!userId) {
      toast.error("Sign in to save preferences.");
      return;
    }
    const previous = selected;
    setSelected(optionValue); // optimistic - feels instant, matching the review queue's pattern
    startTransition(async () => {
      try {
        await updateUserPreferences(userId, { [def.key]: optionValue });
        toast.success(`${def.label} updated`);
      } catch (e) {
        setSelected(previous);
        toast.error(e instanceof Error ? e.message : "Couldn't save that - try again");
      }
    });
  }

  return (
    <Card className="editorial-card">
      <CardHeader className="pb-3">
        <p className="text-sm font-bold text-foreground">{def.label}</p>
        <p className="text-xs text-muted-foreground">{def.description}</p>
      </CardHeader>
      <CardContent className="grid gap-2.5 sm:grid-cols-2">
        {def.options.map((opt) => {
          const isSelected = opt.value === selected;
          return (
            <button
              key={opt.value}
              type="button"
              disabled={pending}
              onClick={() => choose(opt.value)}
              aria-pressed={isSelected}
              className={`flex flex-col gap-1 rounded-lg border p-3.5 text-left transition-colors disabled:cursor-wait ${
                isSelected
                  ? "border-primary/50 bg-primary/5 ring-1 ring-primary/30"
                  : "border-border hover:border-primary/30 hover:bg-accent/40"
              }`}
            >
              <span className="flex items-center justify-between gap-2">
                <span className={`text-sm font-semibold ${isSelected ? "text-primary" : "text-foreground"}`}>
                  {opt.label}
                </span>
                {isSelected && pending ? (
                  <Loader2 className="size-4 shrink-0 animate-spin text-primary" />
                ) : isSelected ? (
                  <Check className="size-4 shrink-0 text-primary" />
                ) : null}
              </span>
              <span className="text-xs leading-relaxed text-muted-foreground">{opt.description}</span>
            </button>
          );
        })}
      </CardContent>
    </Card>
  );
}
