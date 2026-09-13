import Link from "next/link";
import { Inbox } from "lucide-react";
import { backendFetch } from "@/lib/backend";
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

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">Review queue</h1>
        <p className="text-sm text-muted-foreground">
          {totalPending.toLocaleString()} item{totalPending === 1 ? "" : "s"} waiting across every automation
        </p>
      </div>

      {/* Kind filter strip - built entirely from what's registered, so a
          new automation appears here (even with 0 items) with no frontend
          change needed. */}
      <div className="flex flex-wrap items-center gap-2">
        <Link href="/automations/review">
          <Badge variant={!activeKind ? "default" : "outline"} className="cursor-pointer text-xs font-medium px-3 py-1">
            All ({totalPending})
          </Badge>
        </Link>
        {kinds.map((k) => (
          <Link key={k.kind} href={`/automations/review?kind=${k.kind}`}>
            <Badge
              variant={activeKind === k.kind ? "default" : "outline"}
              className="cursor-pointer text-xs font-medium px-3 py-1"
            >
              {k.label} ({countFor(k.kind)})
            </Badge>
          </Link>
        ))}
      </div>

      <div className="flex flex-col gap-4">
        {page.items.length > 0 ? (
          page.items.map((item) => {
            const kind = kindByName.get(item.kind);
            if (!kind) return null; // Orphaned kind (automation removed/renamed) - fail quietly, don't crash the queue.
            return <ReviewItemCard key={item.id} item={item} kind={kind} />;
          })
        ) : (
          <Card>
            <CardContent className="flex flex-col items-center gap-2 py-14 text-center text-sm text-muted-foreground">
              <Inbox className="size-8 opacity-40" />
              <p className="font-medium text-foreground">Nothing waiting on you.</p>
              <p>Every automation is caught up{activeKind ? " for this filter" : ""}.</p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
