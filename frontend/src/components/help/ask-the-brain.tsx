"use client";

import { Button } from "@/components/ui/button";
import { BrainBuddy } from "@/components/brain/brain-buddy";
import { useBrain } from "@/components/brain/brain-provider";

/** Opens the Ask the Brain panel from a help page, with the question already typed if there is one. */
export function AskTheBrain({ question, label = "Ask the Brain" }: { question?: string; label?: string }) {
  const { ask } = useBrain();
  return (
    <Button size="sm" variant="outline" className="gap-1.5" onClick={() => ask(question ? { question } : undefined)}>
      <BrainBuddy mood="happy" head size={16} still /> {label}
    </Button>
  );
}
