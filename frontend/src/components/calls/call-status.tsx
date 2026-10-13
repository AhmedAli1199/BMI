import { CheckCircle2, CircleAlert, Clock, Loader2, Mic } from "lucide-react";

/** A small coloured status label for a call. Colours come from the theme tokens. */
export function CallStatus({ status, label }: { status: string; label: string }) {
  const tone =
    status === "completed" ? { Icon: CheckCircle2, color: "var(--ok)" }
    : status === "failed" || status === "not_admitted" ? { Icon: CircleAlert, color: "var(--destructive)" }
    : status === "recording" ? { Icon: Mic, color: "var(--warn)" }
    : status === "scheduled" || status === "cancelled" ? { Icon: Clock, color: "var(--muted-foreground)" }
    : { Icon: Loader2, color: "var(--warn)" };
  const spin = !["completed", "failed", "not_admitted", "recording", "scheduled", "cancelled"].includes(status);
  return (
    <span className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold" style={{ color: tone.color, borderColor: `color-mix(in oklab, ${tone.color} 40%, transparent)` }}>
      <tone.Icon className={`size-3 ${spin ? "animate-spin" : ""}`} aria-hidden="true" /> {label}
    </span>
  );
}
