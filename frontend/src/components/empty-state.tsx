import type { LucideIcon } from "lucide-react";
import { BrainBuddy, type BrainMood } from "@/components/brain/brain-buddy";

/** "Nothing here yet" for any list or panel: the Brain (sleepy by default; "puzzled" when a search finds nothing),
 * a plain title, a line on what to do next and, optionally, the button that does it. `icon` is still accepted from
 * older call sites but the Brain takes its place. `compact` is for small panels. */
export function EmptyState({ title, children, action, mood = "sleepy", compact = false }: {
  icon?: LucideIcon; title: string; children?: React.ReactNode; action?: React.ReactNode; mood?: BrainMood; compact?: boolean;
}) {
  return (
    <div className={`flex flex-col items-center text-center ${compact ? "gap-1.5 px-4 py-6" : "gap-2 rounded-xl border border-dashed border-border/80 bg-card/50 px-6 py-10"}`}>
      <BrainBuddy mood={mood} size={compact ? 52 : 76} />
      <div className="text-sm font-semibold text-foreground">{title}</div>
      {children && <div className="max-w-md text-xs text-muted-foreground">{children}</div>}
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}
