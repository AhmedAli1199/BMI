import Link from "next/link";
import { ClipboardCheck, Sparkles } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { ReviewKind, ReviewQueueCounts } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default async function AutomationsPage() {
  const [kinds, counts] = await Promise.all([
    backendFetch<ReviewKind[]>("/api/review-queue/kinds"),
    backendFetch<ReviewQueueCounts[]>("/api/review-queue/counts"),
  ]);

  const countFor = (k: string) => counts.find((c) => c.kind === k)?.pending ?? 0;
  const totalPending = counts.reduce((sum, c) => sum + c.pending, 0);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary mb-1">
            <Sparkles className="size-3.5" />
            <span>Automations</span>
          </div>
          <h1 className="text-2xl font-semibold">Stage 1: Data hygiene</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Every automation drafts, nothing sends or writes on its own without a human confirming it here first.
          </p>
        </div>
        <Link href="/automations/review">
          <Badge variant={totalPending > 0 ? "default" : "outline"} className="cursor-pointer gap-1.5 px-3 py-1.5 text-xs font-semibold">
            <ClipboardCheck className="size-3.5" />
            {totalPending.toLocaleString()} waiting for review
          </Badge>
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {kinds.map((k) => (
          <Link key={k.kind} href={`/automations/review?kind=${k.kind}`}>
            <Card className="editorial-card h-full transition-colors hover:border-primary/40 hover:bg-accent/30">
              <CardHeader className="flex-row items-start justify-between gap-2 space-y-0">
                <CardTitle className="text-base font-semibold">{k.label}</CardTitle>
                <Badge variant={countFor(k.kind) > 0 ? "default" : "secondary"} className="shrink-0 text-xs">
                  {countFor(k.kind)} pending
                </Badge>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{k.description}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
        {kinds.length === 0 && (
          <Card className="sm:col-span-2">
            <CardContent className="py-10 text-center text-sm text-muted-foreground">
              No automations registered yet.
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
