import Link from "next/link";
import { ArrowDownWideNarrow, ArrowLeft, ArrowUpNarrowWide, Clock, PartyPopper, Sparkles } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import { styleForKind } from "@/lib/automation-style";
import type { Page, ReviewKind, ReviewQueueCounts, ReviewQueueItem } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ReviewItemCard } from "@/components/review-item-card";
import { ReopenReviewItemButton } from "@/components/reopen-review-item-button";
import { BulkReviewActions } from "@/components/bulk-review-actions";

const STATUS_TABS = [
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
] as const;

const SORT_OPTIONS = [
  { value: "recent", label: "Most recent", icon: Clock },
  { value: "confidence_asc", label: "Confidence: low → high", icon: ArrowUpNarrowWide },
  { value: "confidence_desc", label: "Confidence: high → low", icon: ArrowDownWideNarrow },
] as const;

export default async function ReviewQueuePage({
  searchParams,
}: {
  searchParams: Promise<{ kind?: string; status?: string; sort?: string; q?: string }>;
}) {
  const { kind: activeKind, status: rawStatus, sort: rawSort, q: rawQ } = await searchParams;
  const activeStatus = STATUS_TABS.some((t) => t.value === rawStatus) ? rawStatus! : "pending";
  const activeSort = SORT_OPTIONS.some((s) => s.value === rawSort) ? rawSort! : "recent";
  const activeQuery = (rawQ || "").trim();

  const [kinds, counts, page] = await Promise.all([
    backendFetch<ReviewKind[]>("/api/review-queue/kinds"),
    backendFetch<ReviewQueueCounts[]>("/api/review-queue/counts"),
    backendFetch<Page<ReviewQueueItem>>(
      `/api/review-queue?status=${activeStatus}&sort=${activeSort}&page_size=100${activeKind ? `&kind=${activeKind}` : ""}${
        activeQuery ? `&q=${encodeURIComponent(activeQuery)}` : ""
      }`
    ),
  ]);

  const countFor = (k: string) => counts.find((c) => c.kind === k)?.pending ?? 0;
  const totalPending = counts.reduce((sum, c) => sum + c.pending, 0);
  const kindByName = new Map(kinds.map((k) => [k.kind, k]));
  const activeStyle = activeKind ? styleForKind(activeKind) : null;
  const statusHref = (status: string) =>
    `/automations/review?status=${status}${activeKind ? `&kind=${activeKind}` : ""}${activeSort !== "recent" ? `&sort=${activeSort}` : ""}`;
  const kindHref = (kind?: string) =>
    `/automations/review?status=${activeStatus}${kind ? `&kind=${kind}` : ""}${activeSort !== "recent" ? `&sort=${activeSort}` : ""}`;
  const sortHref = (sort: string) =>
    `/automations/review?status=${activeStatus}${activeKind ? `&kind=${activeKind}` : ""}${sort !== "recent" ? `&sort=${sort}` : ""}`;

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <div>
        <Link
          href="/automations"
          className="mb-2 inline-flex items-center gap-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Automations
        </Link>
        <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
          <Sparkles className="size-3.5" />
          <span>Review queue</span>
        </div>
        <h1 className="editorial-title text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          {activeKind && kindByName.get(activeKind) ? kindByName.get(activeKind)!.label : "Everything waiting on you"}
        </h1>
        <p className="mt-1 text-xs text-muted-foreground sm:text-sm">
          {totalPending.toLocaleString()} item{totalPending === 1 ? "" : "s"} waiting
          {activeKind ? " in this filter" : " across every automation"} - work through them in any order.
        </p>
      </div>

      {/* Status tabs - Pending is the working queue (the only one
          ReviewItemCard renders full actions for); Approved/Rejected are
          a read-only audit trail so a reviewer who moved fast through a
          batch can go back and double-check what got dismissed, and
          reopen anything that looks like a mistake. */}
      <div className="flex items-center gap-1 border-b border-border/70">
        {STATUS_TABS.map((t) => (
          <Link key={t.value} href={statusHref(t.value)}>
            <span
              className={`inline-block border-b-2 px-3 py-2 text-xs font-semibold transition-colors ${
                activeStatus === t.value
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.label}
            </span>
          </Link>
        ))}
      </div>

      {/* Kind filter strip - built entirely from what's registered, so a
          new automation appears here (even with 0 items) with no frontend
          change needed. Each chip carries the same icon/color used
          throughout the automations UI, so the queue and the overview
          read as one system. */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Link href={kindHref()}>
            <Badge
              variant={!activeKind ? "default" : "outline"}
              className="cursor-pointer gap-1 px-3 py-1.5 text-xs font-semibold transition-colors"
            >
              All ({totalPending})
            </Badge>
          </Link>
          {kinds.map((k) => {
            const style = styleForKind(k.kind);
            const Icon = style.icon;
            const isActive = activeKind === k.kind;
            return (
              <Link key={k.kind} href={kindHref(k.kind)}>
                <Badge
                  variant={isActive ? "default" : "outline"}
                  className={`cursor-pointer gap-1.5 px-3 py-1.5 text-xs font-semibold transition-colors ${
                    isActive ? "" : style.color
                  }`}
                >
                  <Icon className="size-3.5" />
                  {k.label} ({countFor(k.kind)})
                </Badge>
              </Link>
            );
          })}
        </div>

        {/* Sort control - confidence lives on every kind's payload (a
            0-1 float, or absent for a kind that doesn't score itself), so
            this works uniformly across every automation without any
            per-kind special-casing. */}
        <div className="flex items-center gap-1 rounded-lg border border-border/70 p-0.5">
          {SORT_OPTIONS.map((s) => {
            const Icon = s.icon;
            const isActive = activeSort === s.value;
            return (
              <Link key={s.value} href={sortHref(s.value)} title={s.label}>
                <span
                  className={`flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-semibold transition-colors ${
                    isActive ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Icon className="size-3.5" />
                  <span className="hidden sm:inline">{s.label}</span>
                </span>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Bulk actions - only meaningful once the queue is filtered to one
          kind (an action's meaning is per-kind, so there's no single
          "approve all" across every automation at once) and only on the
          pending tab (approved/rejected have nothing left to act on).
          Always scoped to the current kind + pending, mirroring exactly
          what the kind chips above already filtered the list to. */}
      {activeStatus === "pending" && activeKind && kindByName.get(activeKind) && (
        <div className="flex justify-end">
          <BulkReviewActions kind={kindByName.get(activeKind)!} pendingCount={countFor(activeKind)} />
        </div>
      )}

      {/* Search by contact/company - matches against every kind's card
          headline (payload.summary), which always names who the item is
          about, so this works uniformly with no per-kind wiring. A plain
          GET form (not a client component) since this is a server
          component page and the URL is already the single source of
          truth for every other filter here. */}
      <form action="/automations/review" method="GET" className="flex items-center gap-2">
        {activeKind && <input type="hidden" name="kind" value={activeKind} />}
        <input type="hidden" name="status" value={activeStatus} />
        {activeSort !== "recent" && <input type="hidden" name="sort" value={activeSort} />}
        <input
          type="search"
          name="q"
          defaultValue={activeQuery}
          placeholder="Search by contact or company..."
          className="w-full max-w-xs rounded-lg border border-border/70 bg-background px-3 py-1.5 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary sm:text-sm"
        />
        {activeQuery && (
          <Link
            href={`/automations/review?status=${activeStatus}${activeKind ? `&kind=${activeKind}` : ""}${activeSort !== "recent" ? `&sort=${activeSort}` : ""}`}
            className="text-xs font-semibold text-muted-foreground hover:text-foreground"
          >
            Clear
          </Link>
        )}
      </form>

      <div className="flex flex-col gap-4">
        {page.items.length > 0 ? (
          page.items.map((item) => {
            const kind = kindByName.get(item.kind);
            if (!kind) return null; // Orphaned kind (automation removed/renamed) - fail quietly, don't crash the queue.
            if (activeStatus !== "pending") {
              return <ResolvedItemRow key={item.id} item={item} kind={kind} />;
            }
            return <ReviewItemCard key={item.id} item={item} kind={kind} />;
          })
        ) : (
          <Card className="editorial-card relative overflow-hidden">
            <div
              className={`absolute -right-8 -top-8 size-32 rounded-full opacity-10 blur-3xl ${
                activeStyle ? activeStyle.accent : "bg-primary"
              }`}
              aria-hidden="true"
            />
            <CardContent className="relative flex flex-col items-center gap-2 py-16 text-center">
              <span className="brand-icon size-14 rounded-full! border-[var(--ok)] text-[var(--ok)]">
                <PartyPopper className="size-6" />
              </span>
              <p className="mt-1 text-base font-bold text-foreground">
                {activeQuery ? "No matches." : activeStatus === "pending" ? "All caught up." : "Nothing here yet."}
              </p>
              <p className="max-w-xs text-sm text-muted-foreground">
                {activeQuery
                  ? `Nothing matching "${activeQuery}"${activeKind ? " in this automation" : ""}.`
                  : activeStatus === "pending"
                  ? `Nothing is waiting on you${activeKind ? " for this automation" : ""} right now. New items will show up here the moment a scanner finds one.`
                  : `No ${activeStatus} items${activeKind ? " for this automation" : ""} yet.`}
              </p>
              {activeKind && (
                <Link
                  href="/automations/review"
                  className="mt-2 text-xs font-semibold text-primary hover:underline"
                >
                  View every automation &rarr;
                </Link>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

/** Read-only row for an already-resolved (approved/rejected) item - the
 * audit trail view. Deliberately much lighter than ReviewItemCard (no
 * action buttons - the decision is already made), plus a Reopen button
 * on rejected items only, since that's the only status it's safe to undo
 * from here (see reopen-review-item-button.tsx). */
function ResolvedItemRow({ item, kind }: { item: ReviewQueueItem; kind: ReviewKind }) {
  const style = styleForKind(kind.kind);
  const Icon = style.icon;
  const action = kind.actions.find((a) => a.id === item.resolved_action);
  return (
    <Card className="editorial-card overflow-hidden">
      <div className={`masthead-rule w-full ${style.accent}`} />
      <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
        <div className="flex min-w-0 items-start gap-3">
          <span className={`mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg border ${style.chipBg} ${style.color}`}>
            <Icon className="size-4" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-bold text-foreground">{item.payload.summary || "Review item"}</p>
            <p className="text-xs text-muted-foreground">
              {action?.label || item.resolved_action || item.status}
              {item.reviewed_at ? ` · ${new Date(item.reviewed_at).toLocaleString()}` : ""}
              {item.review_note ? ` · "${item.review_note}"` : ""}
            </p>
          </div>
        </div>
        {item.status === "rejected" && <ReopenReviewItemButton itemId={item.id} />}
      </CardContent>
    </Card>
  );
}
