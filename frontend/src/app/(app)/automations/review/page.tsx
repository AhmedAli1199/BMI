import Link from "next/link";
import {
  ArrowDownWideNarrow,
  ArrowLeft,
  ArrowUpNarrowWide,
  Building2,
  Check,
  ChevronDown,
  ChevronUp,
  Clock,
  ExternalLink,
  Mail,
  PartyPopper,
  Phone,
  Sparkles,
  UserCircle,
} from "lucide-react";
import { backendFetch } from "@/lib/backend";
import { styleForKind } from "@/lib/automation-style";
import { cleanNoteBody } from "@/lib/notes";
import type { Page, ReviewKind, ReviewQueueCounts, ReviewQueueInsights, ReviewQueueItem } from "@/lib/types";
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
  searchParams: Promise<{ kind?: string; status?: string; sort?: string; q?: string; bucket?: string }>;
}) {
  const { kind: activeKind, status: rawStatus, sort: rawSort, q: rawQ, bucket: activeBucket } = await searchParams;
  const activeStatus = STATUS_TABS.some((t) => t.value === rawStatus) ? rawStatus! : "pending";
  const activeSort = SORT_OPTIONS.some((s) => s.value === rawSort) ? rawSort! : "recent";
  const activeQuery = (rawQ || "").trim();

  const [kinds, counts, page, insights] = await Promise.all([
    backendFetch<ReviewKind[]>("/api/review-queue/kinds"),
    backendFetch<ReviewQueueCounts[]>("/api/review-queue/counts"),
    backendFetch<Page<ReviewQueueItem>>(
      `/api/review-queue?status=${activeStatus}&sort=${activeSort}&page_size=100${activeKind ? `&kind=${activeKind}` : ""}${
        activeQuery ? `&q=${encodeURIComponent(activeQuery)}` : ""
      }${activeBucket ? `&bucket=${activeBucket}` : ""}`
    ),
    // Queue Insights only has buckets for a handful of kinds (see backend's
    // _INSIGHT_BUCKETS) - fetching it with no kind selected would be
    // meaningless (which kind's buckets?), so it's skipped entirely until
    // the queue is filtered to one. Never blocks the main list: a failed
    // insights call just means the panel doesn't render, not a broken page.
    activeKind
      ? backendFetch<ReviewQueueInsights>(`/api/review-queue/insights?kind=${activeKind}&status=${activeStatus}`).catch(
          () => ({ kind: activeKind, buckets: [] })
        )
      : Promise.resolve(null),
  ]);

  const countFor = (k: string) => counts.find((c) => c.kind === k)?.pending ?? 0;
  const totalPending = counts.reduce((sum, c) => sum + c.pending, 0);
  const kindByName = new Map(kinds.map((k) => [k.kind, k]));
  const activeStyle = activeKind ? styleForKind(activeKind) : null;
  const statusHref = (status: string) =>
    `/automations/review?status=${status}${activeKind ? `&kind=${activeKind}` : ""}${activeSort !== "recent" ? `&sort=${activeSort}` : ""}${activeBucket ? `&bucket=${activeBucket}` : ""}`;
  // Deliberately drops any active bucket - a bucket key only means
  // something for the kind it came from (e.g. "high" is a confidence
  // band for duplicate_contact, meaningless for ooo_ambiguous), so
  // switching kind must not carry it over.
  const kindHref = (kind?: string) =>
    `/automations/review?status=${activeStatus}${kind ? `&kind=${kind}` : ""}${activeSort !== "recent" ? `&sort=${activeSort}` : ""}`;
  const sortHref = (sort: string) =>
    `/automations/review?status=${activeStatus}${activeKind ? `&kind=${activeKind}` : ""}${sort !== "recent" ? `&sort=${sort}` : ""}${activeBucket ? `&bucket=${activeBucket}` : ""}`;
  const bucketHref = (bucket?: string) =>
    `/automations/review?status=${activeStatus}${activeKind ? `&kind=${activeKind}` : ""}${activeSort !== "recent" ? `&sort=${activeSort}` : ""}${
      bucket ? `&bucket=${bucket}` : ""
    }`;

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
          change needed. Deliberately restrained: every chip shares one
          neutral outline (a saturated per-kind border on every chip at
          once read as noise, not signal - the icon's own tint is enough
          to keep each automation recognizable). Selection is the one
          splash of color, so the eye finds it instantly. Kinds with
          nothing pending sort to the end and sit at lower opacity - with
          most automations idle most of the time, a wall of "(0)" chips
          otherwise buries the ones actually waiting on you. */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1.5">
          <Link href={kindHref()}>
            <Badge
              variant={!activeKind ? "default" : "outline"}
              className={`cursor-pointer gap-1 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                !activeKind ? "" : "border-border/60 text-muted-foreground hover:border-border hover:text-foreground"
              }`}
            >
              All
              <span className={!activeKind ? "opacity-80" : "opacity-60"}>{totalPending}</span>
            </Badge>
          </Link>
          {[...kinds]
            .sort((a, b) => (countFor(b.kind) > 0 ? 1 : 0) - (countFor(a.kind) > 0 ? 1 : 0))
            .map((k) => {
              const style = styleForKind(k.kind);
              const Icon = style.icon;
              const isActive = activeKind === k.kind;
              const count = countFor(k.kind);
              return (
                <Link key={k.kind} href={kindHref(k.kind)}>
                  <Badge
                    variant={isActive ? "default" : "outline"}
                    className={`cursor-pointer gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                      isActive
                        ? ""
                        : count > 0
                        ? "border-border/60 text-foreground hover:border-border"
                        : "border-border/40 text-muted-foreground/70 hover:border-border/60 hover:text-muted-foreground"
                    }`}
                  >
                    <Icon className={`size-3.5 ${isActive ? "" : count > 0 ? style.color : ""}`} />
                    {k.label}
                    <span className={isActive ? "opacity-80" : count > 0 ? "text-muted-foreground" : "opacity-70"}>{count}</span>
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

      {/* Queue Insights - a bucketed breakdown of the CURRENT kind's
          pending items, using a value the automation already computes at
          ingestion time (confidence / severity / replacements - see
          backend's _INSIGHT_BUCKETS). Only renders when the backend
          actually has buckets for this kind, so it's zero weight on every
          other automation's queue - never a panel with nothing in it. */}
      {insights && insights.buckets.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-border/60 bg-muted/30 px-3 py-2">
          <span className="text-xs font-semibold text-muted-foreground">Queue Insights:</span>
          {insights.buckets.map((b) => {
            const isActive = activeBucket === b.key;
            return (
              <Link key={b.key} href={bucketHref(isActive ? undefined : b.key)}>
                <Badge
                  variant={isActive ? "default" : "outline"}
                  className={`cursor-pointer gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                    isActive ? "" : "border-border/60 text-foreground hover:border-border"
                  }`}
                >
                  {b.label}
                  <span className={isActive ? "opacity-80" : "text-muted-foreground"}>{b.count}</span>
                </Badge>
              </Link>
            );
          })}
          {activeBucket && (
            <Link href={bucketHref()} className="text-[11px] font-semibold text-primary hover:underline">
              Clear
            </Link>
          )}
        </div>
      )}

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
        {activeBucket && <input type="hidden" name="bucket" value={activeBucket} />}
        <input
          type="search"
          name="q"
          defaultValue={activeQuery}
          placeholder="Search by contact or company..."
          className="w-full max-w-xs rounded-lg border border-border/70 bg-background px-3 py-1.5 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary sm:text-sm"
        />
        {activeQuery && (
          <Link
            href={`/automations/review?status=${activeStatus}${activeKind ? `&kind=${activeKind}` : ""}${activeSort !== "recent" ? `&sort=${activeSort}` : ""}${activeBucket ? `&bucket=${activeBucket}` : ""}`}
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
/** The audit-trail view for an already-resolved (approved/rejected) item.
 * Reads back three things the flat summary row used to lose entirely:
 * who resolved it (reviewed_by - now actually recorded, see backend's
 * resolve_review_item), a way to open the linked contact/company
 * directly (entity_summary + item.entity_id/entity_type), and the
 * original source material (payload.original_text/source_context) so a
 * reviewer double-checking a past decision doesn't have to take the
 * summary's word for it. */
function ResolvedItemRow({ item, kind }: { item: ReviewQueueItem; kind: ReviewKind }) {
  const style = styleForKind(kind.kind);
  const Icon = style.icon;
  const action = kind.actions.find((a) => a.id === item.resolved_action);
  const entity = item.entity_summary;
  const hasSourceMaterial = Boolean(item.payload.original_text || item.payload.source_context);
  const hasDetails = Boolean(item.payload.details && item.payload.details.length > 0);

  return (
    <Card className="editorial-card overflow-hidden">
      <div className={`masthead-rule w-full ${style.accent}`} />
      <CardContent className="flex flex-col gap-3 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <span className={`mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg border ${style.chipBg} ${style.color}`}>
              <Icon className="size-4" />
            </span>
            <div className="min-w-0">
              <p className="text-sm font-bold text-foreground">{item.payload.summary || "Review item"}</p>
              <p className="text-xs text-muted-foreground">
                <span className={item.status === "approved" ? "font-semibold text-emerald-600" : "font-semibold text-rose-600"}>
                  {item.status === "approved" ? <Check className="mr-0.5 inline size-3" /> : null}
                  {action?.label || item.resolved_action || item.status}
                </span>
                {item.reviewed_by ? ` by ${item.reviewed_by.name}` : " · no reviewer recorded"}
                {item.reviewed_at ? ` · ${new Date(item.reviewed_at).toLocaleString()}` : ""}
                {item.review_note ? ` · "${item.review_note}"` : ""}
              </p>
              {item.entity_type && item.entity_id && (
                <Link
                  href={`/${item.entity_type === "contact" ? "contacts" : "companies"}/${item.entity_id}`}
                  className="mt-0.5 inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
                >
                  Open {item.entity_type} record
                  <ExternalLink className="size-3" />
                </Link>
              )}
            </div>
          </div>
          {item.status === "rejected" && <ReopenReviewItemButton itemId={item.id} />}
        </div>

        {/* Contact/company identity strip - enough to confirm who this is
            about without leaving the list. */}
        {entity && (
          <Link
            href={`/${entity.type === "contact" ? "contacts" : "companies"}/${entity.id}`}
            className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-lg border border-border/70 bg-muted/20 px-3 py-2 text-xs transition-colors hover:border-primary/40 hover:bg-muted/40"
          >
            <span className="flex items-center gap-1.5 font-semibold text-foreground">
              <UserCircle className="size-3.5 text-muted-foreground" />
              {entity.label}
              {entity.job_title ? <span className="font-normal text-muted-foreground">· {entity.job_title}</span> : null}
            </span>
            {entity.company_name && (
              <span className="flex items-center gap-1 text-muted-foreground">
                <Building2 className="size-3.5" />
                {entity.company_name}
              </span>
            )}
            {entity.email && (
              <span className="flex items-center gap-1 text-muted-foreground">
                <Mail className="size-3.5" />
                {entity.email}
              </span>
            )}
            {entity.phone && (
              <span className="flex items-center gap-1 text-muted-foreground">
                <Phone className="size-3.5" />
                {entity.phone}
              </span>
            )}
          </Link>
        )}

        {hasDetails && (
          <dl className="grid grid-cols-1 gap-x-4 gap-y-1.5 rounded-lg bg-muted/30 p-3 text-xs sm:grid-cols-2">
            {item.payload.details!.map((d, i) => (
              <div key={d.key ?? i} className="flex items-baseline justify-between gap-2 sm:justify-start">
                <dt className="shrink-0 text-muted-foreground">{d.label}</dt>
                <dd className="whitespace-pre-wrap break-words text-right font-medium text-foreground sm:text-left">{d.value}</dd>
              </div>
            ))}
          </dl>
        )}

        {hasSourceMaterial && (
          <details className="group rounded-lg border border-border/70">
            <summary className="flex cursor-pointer list-none items-center gap-1.5 px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground">
              <ChevronDown className="size-3.5 transition-transform group-open:hidden" />
              <ChevronUp className="hidden size-3.5 transition-transform group-open:block" />
              Original message
            </summary>
            <p className="whitespace-pre-wrap border-t border-border/70 bg-muted/20 px-3 py-2.5 text-xs text-muted-foreground">
              {cleanNoteBody(item.payload.original_text || item.payload.source_context || "")}
            </p>
          </details>
        )}
      </CardContent>
    </Card>
  );
}
