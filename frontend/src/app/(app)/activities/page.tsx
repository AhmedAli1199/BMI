import Link from "next/link";
import { CalendarDays, PhoneCall, Calendar as CalendarIcon, CheckSquare, Lock } from "lucide-react";
import { getSession } from "@/lib/session";
import { getPublicationFilter } from "@/lib/publication";
import { listActivities, listPublications } from "@/lib/actions";
import { allowedSourceDbSlugs, resolveScope } from "@/lib/access";
import { ActivityDoneToggle } from "@/components/activity-done-toggle";
import { Badge } from "@/components/ui/badge";
import { PublicationQuickFilter } from "@/components/publication-quick-filter";
import type { ActivityOut } from "@/lib/types";

type Status = "open" | "done" | "all";

function typeIcon(type: string | null) {
  const t = (type || "").toLowerCase();
  if (t.includes("call")) return <PhoneCall className="size-3.5 text-amber-600 dark:text-amber-400" />;
  if (t.includes("meet")) return <CalendarIcon className="size-3.5 text-blue-600 dark:text-blue-400" />;
  return <CheckSquare className="size-3.5 text-rose-600 dark:text-rose-400" />;
}

function dayLabel(iso: string): string {
  const d = new Date(iso);
  const today = new Date();
  const startOfDay = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const diffDays = Math.round((startOfDay(d) - startOfDay(today)) / 86400000);
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Tomorrow";
  if (diffDays === -1) return "Yesterday";
  if (diffDays < 0) return `${d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })} (overdue)`;
  return d.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "short", year: "numeric" });
}

export default async function ActivitiesPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; mine?: string }>;
}) {
  const { status: statusParam, mine } = await searchParams;
  const status: Status = statusParam === "done" || statusParam === "all" ? statusParam : "open";

  const [rawSourceDb, session, allPublications] = await Promise.all([
    getPublicationFilter(),
    getSession(),
    listPublications(),
  ]);
  const scope = resolveScope(session, rawSourceDb);
  const source_db = scope.source_db === "__no_access__" ? "" : scope.source_db;
  const publications = session?.role === "admin"
    ? allPublications
    : allPublications.filter((p) => allowedSourceDbSlugs(session).includes(p.slug));

  const data = scope.source_db === "__no_access__"
    ? { items: [] as ActivityOut[], total: 0, page: 1, page_size: 100 }
    : await listActivities({
        source_db: source_db || undefined,
        is_cleared: status === "all" ? undefined : status === "done",
        assigned_user_id: mine === "1" && session ? session.sub : undefined,
      });

  const groups = new Map<string, ActivityOut[]>();
  for (const item of data.items) {
    const label = dayLabel(item.start_at);
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label)!.push(item);
  }

  const tabHref = (s: Status) => {
    const p = new URLSearchParams();
    if (s !== "open") p.set("status", s);
    if (mine === "1") p.set("mine", "1");
    const qs = p.toString();
    return `/activities${qs ? `?${qs}` : ""}`;
  };
  const mineHref = () => {
    const p = new URLSearchParams();
    if (status !== "open") p.set("status", status);
    if (mine !== "1") p.set("mine", "1");
    const qs = p.toString();
    return `/activities${qs ? `?${qs}` : ""}`;
  };

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-4 sm:p-6">
      <div className="border-b border-border/80 pb-4">
        <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
          <CalendarDays className="size-3.5" />
          <span>Calendar &amp; Task List</span>
        </div>
        <h1 className="editorial-title text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
          What&apos;s scheduled
        </h1>
        <p className="mt-1 text-xs text-muted-foreground sm:text-sm">
          Every call, meeting and to-do logged from a contact or company page, or scheduled directly
          from the &ldquo;Log or schedule&rdquo; button up top.
        </p>
      </div>

      <PublicationQuickFilter current={source_db} publications={publications} />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1.5">
          {(["open", "done", "all"] as Status[]).map((s) => (
            <Link
              key={s}
              href={tabHref(s)}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold capitalize transition-colors ${
                status === s
                  ? "bg-primary/15 text-primary border border-primary/30"
                  : "text-muted-foreground hover:bg-muted border border-transparent"
              }`}
            >
              {s === "open" ? "Open" : s === "done" ? "Done" : "All"}
            </Link>
          ))}
        </div>
        {session && (
          <Link
            href={mineHref()}
            className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
              mine === "1"
                ? "bg-primary/15 text-primary border border-primary/30"
                : "text-muted-foreground hover:bg-muted border border-transparent"
            }`}
          >
            {mine === "1" ? "Showing: mine only" : "Show mine only"}
          </Link>
        )}
      </div>

      {data.items.length === 0 ? (
        <div className="rounded-lg border border-dashed p-12 text-center text-sm text-muted-foreground">
          <CheckSquare className="mx-auto mb-2 size-8 opacity-40" />
          <p className="font-medium">Nothing here.</p>
          <p className="text-xs mt-1">Use &ldquo;Log or schedule&rdquo; up top to add a call, meeting or to-do.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {[...groups.entries()].map(([label, items]) => (
            <div key={label} className="flex flex-col gap-2">
              <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{label}</h2>
              <div className="overflow-hidden rounded-lg border border-border bg-card">
                {items.map((item) => {
                  const who = item.contact_name || item.company_name;
                  const link = item.contact_id
                    ? `/contacts/${item.contact_id}`
                    : item.company_id
                      ? `/companies/${item.company_id}`
                      : null;
                  return (
                    <div
                      key={item.id}
                      className="flex items-center gap-3 border-b border-border/60 p-3 last:border-b-0 hover:bg-muted/20"
                    >
                      <ActivityDoneToggle
                        id={item.id}
                        isCleared={item.is_cleared}
                        contactId={item.contact_id}
                        companyId={item.company_id}
                      />
                      {typeIcon(item.activity_type)}
                      <div className="min-w-0 flex-1">
                        <div className={`truncate text-sm font-medium ${item.is_cleared ? "text-muted-foreground line-through" : "text-foreground"}`}>
                          {item.subject || item.activity_type || "Activity"}
                        </div>
                        <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                          {who && link ? (
                            <Link href={link} className="font-medium text-primary hover:underline">
                              {who}
                            </Link>
                          ) : who ? (
                            <span>{who}</span>
                          ) : null}
                          {item.is_private && (
                            <span className="inline-flex items-center gap-0.5">
                              <Lock className="size-2.5" /> Private
                            </span>
                          )}
                          {item.created_by && <span>· logged by {item.created_by.name}</span>}
                        </div>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <Badge variant="outline" className="text-[10px]">
                          {item.activity_type}
                        </Badge>
                        <time className="text-[11px] font-mono text-muted-foreground">
                          {item.is_timeless
                            ? "No time"
                            : new Date(item.start_at).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}
                        </time>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
