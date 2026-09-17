import Link from "next/link";
import { CalendarDays, Search, Plus, Filter, AlertCircle, CheckCircle2, Clock } from "lucide-react";
import { getSession } from "@/lib/session";
import { getPublicationFilter } from "@/lib/publication";
import { listActivities, listPublications } from "@/lib/actions";
import { allowedSourceDbSlugs, resolveScope } from "@/lib/access";
import { PublicationQuickFilter } from "@/components/publication-quick-filter";
import { InteractiveActivityTable } from "@/components/interactive-activity-table";
import { LogInteractionDialog } from "@/components/log-interaction-dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { ActivityOut } from "@/lib/types";

type Status = "open" | "overdue" | "done" | "all";

export default async function ActivitiesPage({
  searchParams,
}: {
  searchParams: Promise<{
    status?: string;
    mine?: string;
    type?: string;
    priority?: string;
    q?: string;
  }>;
}) {
  const { status: statusParam, mine, type: typeParam, priority: priorityParam, q: qParam } =
    await searchParams;

  const status: Status =
    statusParam === "overdue" || statusParam === "done" || statusParam === "all"
      ? statusParam
      : "open";

  const selectedType = typeParam && typeParam !== "all" ? typeParam : undefined;
  const selectedPriority = priorityParam && priorityParam !== "all" ? priorityParam : undefined;
  const searchQuery = qParam?.trim() || undefined;

  const [rawSourceDb, session, allPublications] = await Promise.all([
    getPublicationFilter(),
    getSession(),
    listPublications(),
  ]);
  const scope = resolveScope(session, rawSourceDb);
  const source_db = scope.source_db === "__no_access__" ? "" : scope.source_db;
  const publications =
    session?.role === "admin"
      ? allPublications
      : allPublications.filter((p) => allowedSourceDbSlugs(session).includes(p.slug));

  const isCleared =
    status === "done" ? true : status === "open" || status === "overdue" ? false : undefined;

  const data =
    scope.source_db === "__no_access__"
      ? { items: [] as ActivityOut[], total: 0, page: 1, page_size: 100 }
      : await listActivities({
          source_db: source_db || undefined,
          is_cleared: isCleared,
          priority: selectedPriority,
          activity_type: selectedType,
          q: searchQuery,
          assigned_user_id: mine === "1" && session ? session.sub : undefined,
        });

  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);

  // If status is "overdue", further ensure start_at < today
  let displayItems = data.items;
  if (status === "overdue") {
    displayItems = displayItems.filter(
      (item) => !item.is_cleared && new Date(item.start_at).getTime() < todayStart.getTime()
    );
  }

  // Count overdues in the fetched set for the tab badge
  const overdueCount = data.items.filter(
    (item) => !item.is_cleared && new Date(item.start_at).getTime() < todayStart.getTime()
  ).length;

  const createFilterHref = (updates: Record<string, string | undefined | null>) => {
    const p = new URLSearchParams();
    const current: Record<string, string | undefined> = {
      status: status !== "open" ? status : undefined,
      mine: mine === "1" ? "1" : undefined,
      type: selectedType,
      priority: selectedPriority,
      q: searchQuery,
    };

    const merged = { ...current, ...updates };
    for (const [k, v] of Object.entries(merged)) {
      if (v) p.set(k, v);
    }
    const qs = p.toString();
    return `/activities${qs ? `?${qs}` : ""}`;
  };

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6">
      {/* Header & Quick Action */}
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/80 pb-4">
        <div>
          <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
            <CalendarDays className="size-3.5" />
            <span>Calendar &amp; Task List</span>
          </div>
          <h1 className="editorial-title text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            Calendar &amp; Tasks
          </h1>
          <p className="mt-1 text-xs text-muted-foreground sm:text-sm">
            High-density schedule and activities data grid across all contacts, companies and cadences.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
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
            {mine === "1" && <input type="hidden" name="mine" value="1" />}
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
        </div>
      </div>

      {/* Publication Segmentation Strip */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <PublicationQuickFilter current={source_db} publications={publications} />
        <span className="text-xs text-muted-foreground">
          Tip: Click any subject or row to open full activity details &amp; notes
        </span>
      </div>

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
                ? "border border-red-500/40 bg-red-500/15 text-red-600 dark:text-red-400"
                : "border border-transparent text-muted-foreground hover:bg-muted"
            }`}
          >
            <span>Overdue</span>
            {overdueCount > 0 && (
              <span className="rounded-full bg-red-500/20 px-1.5 py-0.2 text-[10px] font-bold text-red-700 dark:text-red-300">
                {overdueCount}
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
                href={createFilterHref({ mine: mine === "1" ? null : "1" })}
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
          Showing {displayItems.length} {displayItems.length === 1 ? "activity" : "activities"}
          {searchQuery ? ` matching "${searchQuery}"` : ""}
        </span>
        <div className="flex items-center gap-4">
          <span className="inline-flex items-center gap-1">
            <Clock className="size-3 text-primary" />
            <span>Times in London / BST</span>
          </span>
        </div>
      </div>
    </div>
  );
}
