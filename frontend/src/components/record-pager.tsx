import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

/** "12 of 340" with previous / next: steps through the filtered, sorted list the person came from (the page works out
 * the neighbours). Sits with the page's other actions. */
export function RecordPager({ position, total, prevHref, nextHref, noun }: {
  position?: number | null; total?: number; prevHref: string | null; nextHref: string | null; noun: string;
}) {
  if (!position || !total || total < 2) return null;
  const step = (href: string | null, label: string, icon: React.ReactNode) => (
    <Button size="icon-sm" variant="outline" disabled={!href} title={label} aria-label={label}
      nativeButton={!href} render={href ? <Link href={href} /> : undefined}>
      {icon}
    </Button>
  );
  return (
    <div className="flex items-center gap-1" aria-label={`${noun} ${position} of ${total}`}>
      {step(prevHref, `Previous ${noun}`, <ChevronLeft className="size-4" />)}
      <span className="min-w-16 text-center text-xs tabular-nums text-muted-foreground">
        {position.toLocaleString("en-GB")} of {total.toLocaleString("en-GB")}
      </span>
      {step(nextHref, `Next ${noun}`, <ChevronRight className="size-4" />)}
    </div>
  );
}
