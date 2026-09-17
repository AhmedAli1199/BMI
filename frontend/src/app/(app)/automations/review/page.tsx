import Link from "next/link";
import { ArrowLeft, PartyPopper, Sparkles } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import { styleForKind } from "@/lib/automation-style";
import type { Page, ReviewKind, ReviewQueueCounts, ReviewQueueItem } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ReviewItemCard } from "@/components/review-item-card";

export default async function ReviewQueuePage({
  searchParams,
}: {
  searchParams: Promise<{ kind?: string }>;
}) {
  const { kind: activeKind } = await searchParams;

  const [kinds, counts, page] = await Promise.all([
    backendFetch<ReviewKind[]>("/api/review-queue/kinds"),
    backendFetch<ReviewQueueCounts[]>("/api/review-queue/counts"),
    backendFetch<Page<ReviewQueueItem>>(
      `/api/review-queue?status=pending&page_size=100${activeKind ? `&kind=${activeKind}` : ""}`
    ),
  ]);

  const countFor = (k: string) => counts.find((c) => c.kind === k)?.pending ?? 0;
  const totalPending = counts.reduce((sum, c) => sum + c.pending, 0);
  const kindByName = new Map(kinds.map((k) => [k.kind, k]));
  const activeStyle = activeKind ? styleForKind(activeKind) : null;

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

      {/* Kind filter strip - built entirely from what's registered, so a
          new automation appears here (even with 0 items) with no frontend
          change needed. Each chip carries the same icon/color used
          throughout the automations UI, so the queue and the overview
          read as one system. */}
      <div className="flex flex-wrap items-center gap-2">
        <Link href="/automations/review">
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
            <Link key={k.kind} href={`/automations/review?kind=${k.kind}`}>
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

      <div className="flex flex-col gap-4">
        {page.items.length > 0 ? (
          page.items.map((item) => {
            const kind = kindByName.get(item.kind);
            if (!kind) return null; // Orphaned kind (automation removed/renamed) - fail quietly, don't crash the queue.
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
              <p className="mt-1 text-base font-bold text-foreground">All caught up.</p>
              <p className="max-w-xs text-sm text-muted-foreground">
                Nothing is waiting on you{activeKind ? " for this automation" : ""} right now.
                New items will show up here the moment a scanner finds one.
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
