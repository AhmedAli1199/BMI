"use client";

import { useEffect, useState } from "react";

/** Ticking clock shown in the topbar across all three themes - the thing
 * that makes "morning/evening/night" feel like it's actually reading the
 * room, not just three static skins with different names.
 */
export function LiveClock({ className }: { className?: string }) {
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  // Render nothing until mounted - avoids a server/client time mismatch.
  if (!now) return <span className={className} suppressHydrationWarning />;

  const time = now.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  const day = now.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });

  return (
    <span className={className}>
      <span className="font-mono tabular-nums">{time}</span>
      <span className="text-muted-foreground"> · {day}</span>
    </span>
  );
}
