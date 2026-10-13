import Link from "next/link";

/** The two views of Call notes: upcoming meetings on the shared calendar, and recorded calls. */
export function CallsTabs({ active }: { active: "meetings" | "calls" }) {
  const tab = (href: string, label: string, on: boolean) => (
    <Link href={href} aria-current={on ? "page" : undefined}
      className={`border-b-2 px-1 pb-2 text-sm font-semibold ${on ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
      {label}
    </Link>
  );
  return (
    <nav aria-label="Call notes" className="flex gap-5 border-b border-border/70">
      {tab("/calls/meetings", "Meetings", active === "meetings")}
      {tab("/calls", "Recorded calls", active === "calls")}
    </nav>
  );
}
