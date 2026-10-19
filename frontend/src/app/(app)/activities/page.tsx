import Link from "next/link";
import { Search, Plus, Clock } from "lucide-react";
import { getSession } from "@/lib/session";
import { getPublicationFilter } from "@/lib/publication";
import { listActivities } from "@/lib/actions";
import { resolveScope } from "@/lib/access";
import { CalendarRemindersHeader } from "@/components/calendar-reminders-header";
import { InteractiveActivityTable } from "@/components/interactive-activity-table";
import { LogInteractionDialog } from "@/components/log-interaction-dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { ActivityOut } from "@/lib/types";

type Status = "open" | "overdue" | "done" | "all";

const PAGE_SIZE = 100;

export default async function ActivitiesPage({
  searchParams,
}: {
  searchParams: Promise<{
    status?: string;
    mine?: string;
    type?: string;
    priority?: string;
    q?: string;
    page?: string;
  }>;
}) {
  const { status: statusParam, mine: rawMine, type: typeParam, priority: priorityParam, q: qParam, page: pageParam } =
    await searchParams;
  const page = Math.max(1, Number.parseInt(pageParam ?? "1", 10) || 1);

  const status: Status =
    statusParam === "overdue" || statusParam === "done" || statusParam === "all"
      ? statusParam
      : "open";

  const selectedType = typeParam && typeParam !== "all" ? typeParam : undefined;
  const selectedPriority = priorityParam && priorityParam !== "all" ? priorityParam : undefined;
  const searchQuery = qParam?.trim() || undefined;

  const [rawSourceDb, session] = await Promise.all([getPublicationFilter(), getSession()]);
  const scope = resolveScope(session, rawSourceDb);
  const source_db = scope.source_db === "__no_access__" ? "" : scope.source_db;
  // The database filter above scopes by title, not by person - by
  // default this grid shows everyone's activities in that database
  // (matches Act!'s own shared-calendar model), with "Mine only" as an
  // opt-in toggle. For a sales rep, defaulting to everyone else's
  // scheduling (an admin/data manager's own admin tasks included) isn't
  // useful day to day, so "Mine only" starts ON for that role - still
  // just a default, not a restriction: rawMine=0 explicitly turns it
  // back off, same as anyone else can toggle it either way.
  const mine =
    rawMine === "1" ? "1" : rawMine === "0" ? undefined : session?.role === "sales" ? "1" : undefined;

  const isCleared =
    status === "done" ? true : status === "open" || status === "overdue" ? false : undefined;

  // "Overdue" = not done and due before today. The list and the count both
  // come from the server, so they cover every activity, not just one page.
  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);

  const data =
    scope.source_db === "__no_access__"
      ? { items: [] as ActivityOut[], total: 0, page: 1, page_size: PAGE_SIZE, overdue_total: 0 }
      : await listActivities({
          source_db: source_db || undefined,
          is_cleared: isCleared,
          priority: selectedPriority,
          activity_type: selectedType,
          q: searchQuery,
          assigned_user_id: mine === "1" && session ? session.sub : undefined,
          start_before: status === "overdue" ? new Date(todayStart.getTime() - 1).toISOString() : undefined,
          overdue_before: todayStart.toISOString(),
          page,
          page_size: PAGE_SIZE,
        });

  const displayItems = data.items;
  const overdueCount = data.overdue_total ?? 0;
  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  const createFilterHref = (updates: Record<string, string | undefined | null>) => {
    const p = new URLSearchParams();
    const current: Record<string, string | undefined> = {
      status: status !== "open" ? status : undefined,
      // Keep the person's own choice. A salesperson starts on "Mine only", so
      // when they turn it off that has to stay off ("0") as they click about.
      mine: mine === "1" ? (session?.role === "sales" ? undefined : "1") : session?.role === "sales" ? "0" : undefined,
      type: selectedType,
      priority: selectedPriority,
      q: searchQuery,
    };

    // Any filter change starts again from page 1.
    const merged = { ...current, page: undefined, ...updates };
    for (const [k, v] of Object.entries(merged)) {
      if (v) p.set(k, v);
    }
    const qs = p.toString();
    return `/activities${qs ? `?${qs}` : ""}`;
  };

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6">
      <CalendarRemindersHeader active="calendar" actions={<>
          {/* Quick Search */}
          <form action="/activities" className="relative w-64 sm:w-72">
            <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
            <Input
              name="q"
              placeholder="Search regarding, details, names..."
              defaultValue={searchQuery ?? ""}
              className="h-9 pl-8 text-xs"
            />
            {status !== "open" && <input type="hidden" name="status" value={status} />}
            {selectedType && <input type="hidden" name="type" value={selectedType} />}
            {selectedPriority && <input type="hidden" name="priority" value={selectedPriority} />}
            {mine === "1" && session?.role !== "sales" && <input type="hidden" name="mine" value="1" />}
            {mine !== "1" && session?.role === "sales" && <input type="hidden" name="mine" value="0" />}
          </form>

          {/* Log or schedule dialog trigger */}
          <LogInteractionDialog
            global={true}
            sourceDb={source_db || undefined}
            trigger={
              <Button size="sm" className="h-9 gap-1.5 text-xs font-semibold shadow-xs">
                <Plus className="size-3.5" />
                <span>Log or schedule</span>
              </Button>
            }
          />
        </>} />


      {/* Filter Control Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/80 bg-muted/20 p-2.5">
        {/* Status Tabs */}
        <div className="flex flex-wrap items-center gap-1.5">
          <Link
            href={createFilterHref({ status: null })}
            className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
              status === "open"
                ? "border border-primary/40 bg-primary/15 text-primary"
                : "border border-transparent text-muted-foreground hover:bg-muted"
            }`}
          >
            Open
          </Link>
          <Link
            href={createFilterHref({ status: "overdue" })}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
              status === "overdue"
                ? "border border-[var(--bad)]/40 bg-[var(--bad-tint)] text-[var(--bad)]"
                : "border border-transparent text-muted-foreground hover:bg-muted"
            }`}
          >
            <span>Overdue</span>
            {overdueCount > 0 && (
              <span className="rounded-full bg-[var(--bad-tint)] px-1.5 py-0.5 text-[10px] font-bold tabular-nums text-[var(--bad)]">
                {overdueCount.toLocaleString("en-GB")}
              </span>
            )}
          </Link>
          <Link
            href={createFilterHref({ status: "done" })}
            className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
              status === "done"
                ? "border border-[var(--ok)]/40 bg-[var(--ok)]/15 text-[var(--ok)]"
                : "border border-transparent text-muted-foreground hover:bg-muted"
            }`}
          >
            Done
          </Link>
          <Link
            href={createFilterHref({ status: "all" })}
            className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
              status === "all"
                ? "border border-primary/40 bg-primary/15 text-primary"
                : "border border-transparent text-muted-foreground hover:bg-muted"
            }`}
          >
            All
          </Link>
        </div>

        {/* Secondary filters: Type, Priority, Mine */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {/* Type Filter */}
          <div className="flex items-center gap-1">
            <span className="text-[11px] font-medium text-muted-foreground">Type:</span>
            {(["all", "call", "meeting", "to-do"] as const).map((t) => {
              const active = (!selectedType && t === "all") || selectedType === t;
              return (
                <Link
                  key={t}
                  href={createFilterHref({ type: t === "all" ? null : t })}
                  className={`rounded px-2 py-1 text-[11px] font-medium capitalize transition-colors ${
                    active
                      ? "bg-primary text-primary-foreground font-semibold"
                      : "text-muted-foreground hover:bg-muted"
                  }`}
                >
                  {t === "to-do" ? "To-do" : t}
                </Link>
              );
            })}
          </div>

          <div className="h-4 w-px bg-border/80" />

          {/* Priority Filter */}
          <div className="flex items-center gap-1">
            <span className="text-[11px] font-medium text-muted-foreground">Priority:</span>
            {(["all", "high", "normal", "low"] as const).map((p) => {
              const active = (!selectedPriority && p === "all") || selectedPriority === p;
              return (
                <Link
                  key={p}
                  href={createFilterHref({ priority: p === "all" ? null : p })}
                  className={`rounded px-2 py-1 text-[11px] font-medium capitalize transition-colors ${
                    active
                      ? "bg-primary text-primary-foreground font-semibold"
                      : "text-muted-foreground hover:bg-muted"
                  }`}
                >
                  {p}
                </Link>
              );
            })}
          </div>

          {session && (
            <>
              <div className="h-4 w-px bg-border/80" />
              <Link
                href={createFilterHref({ mine: mine === "1" ? "0" : "1" })}
                className={`rounded px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                  mine === "1"
                    ? "border border-primary/40 bg-primary/15 text-primary"
                    : "border border-border text-muted-foreground hover:bg-muted"
                }`}
              >
                {mine === "1" ? "Showing mine only" : "Mine only"}
              </Link>
            </>
          )}
        </div>
      </div>

      {/* Main High-Density Act! Data Grid Table */}
      <InteractiveActivityTable items={displayItems} />

      {/* Bottom Summary Strip */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {data.total > PAGE_SIZE
            ? `Showing ${((page - 1) * PAGE_SIZE + 1).toLocaleString("en-GB")}-${((page - 1) * PAGE_SIZE + displayItems.length).toLocaleString("en-GB")} of ${data.total.toLocaleString("en-GB")} activities`
            : `Showing ${displayItems.length} ${displayItems.length === 1 ? "activity" : "activities"}`}
          {searchQuery ? ` matching "${searchQuery}"` : ""}
        </span>
        <div className="flex items-center gap-4">
          {totalPages > 1 && (
            <div className="flex items-center gap-2">
              {page > 1 && (
                <Link
                  className="rounded-md border border-border bg-card px-3 py-1.5 font-medium hover:bg-muted"
                  href={createFilterHref({ page: String(page - 1) })}
                >
                  &larr; Previous
                </Link>
              )}
              <span className="tabular-nums">Page {page} of {totalPages.toLocaleString("en-GB")}</span>
              {page < totalPages && (
                <Link
                  className="rounded-md border border-border bg-card px-3 py-1.5 font-medium hover:bg-muted"
                  href={createFilterHref({ page: String(page + 1) })}
                >
                  Next &rarr;
                </Link>
              )}
            </div>
          )}
          <span className="inline-flex items-center gap-1">
            <Clock className="size-3 text-primary" />
            <span>Times in London / BST</span>
          </span>
        </div>
      </div>
    </div>
  );
}
