import Link from "next/link";
import { CalendarClock, Users } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { backendFetch } from "@/lib/backend";
import { getSession } from "@/lib/session";
import type { ReviewKind, TodayItem } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ReviewItemCard } from "@/components/review-item-card";
import { BrainBuddy } from "@/components/brain/brain-buddy";

/** SALES-013 (Morning Follow-Up Queue) - see backend's
 * app/automations/morning_queue.py for why this page has no producer of
 * its own: it's a grouped read of items SALES-012 and the Follow-up
 * Engine already queue, organized per salesperson via Contact.owner_user_id.
 * "My list" scopes to the signed-in rep; "Everyone" (any signed-in user,
 * not just admins - same visibility as the review queue itself) groups
 * across the whole team for a manager-style morning check. */
export default async function TodayPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const session = await getSession();
  // "Everyone" is a manager-style cross-team view - only meaningful for
  // someone who can actually see more than their own database/queue
  // (admin/data_manager; a sales identity's /today call is forced to
  // their own owner_user_id server-side regardless of what's asked for -
  // see backend/app/api/routes/automations.py's get_today_queue - so
  // offering the toggle to them would just silently do nothing when
  // clicked, same bug as the publication switcher).
  const canViewEveryone = session?.role === "admin" || session?.role === "data_manager";
  const { view: rawView } = await searchParams;
  const view = rawView === "all" && canViewEveryone ? "all" : "mine";

  const ownerParam = view === "mine" && session?.sub ? `?owner_user_id=${session.sub}` : "";

  const [items, kinds] = await Promise.all([
    backendFetch<TodayItem[]>(`/api/automations/today${ownerParam}`),
    backendFetch<ReviewKind[]>("/api/review-queue/kinds"),
  ]);

  const kindByName = new Map(kinds.map((k) => [k.kind, k]));

  const groups = new Map<string, TodayItem[]>();
  for (const item of items) {
    const key = item.owner_name || "Unassigned";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(item);
  }
  const orderedGroups = [...groups.entries()].sort(([a], [b]) => {
    if (a === "Unassigned") return 1;
    if (b === "Unassigned") return -1;
    return a.localeCompare(b);
  });

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        section="Everyday"
        title="Today"
        description={
          <>
            {view === "mine" ? "" : "Everyone's list. "}
            {items.length.toLocaleString()} item{items.length === 1 ? "" : "s"} - budget windows, renewals, promised
            call-backs and personal moments worth a note (like a birthday) that are due, plus overdue follow-ups.
          </>
        }
      />

      {canViewEveryone && (
        <div className="flex items-center gap-2">
          <Link href="/automations/today?view=mine">
            <Badge variant={view === "mine" ? "default" : "outline"} className="cursor-pointer gap-1.5 px-3 py-1.5 text-xs font-semibold">
              <CalendarClock className="size-3.5" />
              My list
            </Badge>
          </Link>
          <Link href="/automations/today?view=all">
            <Badge variant={view === "all" ? "default" : "outline"} className="cursor-pointer gap-1.5 px-3 py-1.5 text-xs font-semibold">
              <Users className="size-3.5" />
              Everyone
            </Badge>
          </Link>
        </div>
      )}

      {items.length === 0 ? (
        <Card className="editorial-card relative overflow-hidden">
          <CardContent className="relative flex flex-col items-center gap-2 py-16 text-center">
            <BrainBuddy mood="celebrating" size={96} />
            <p className="mt-1 text-base font-bold text-foreground">Nothing due right now.</p>
            <p className="max-w-xs text-sm text-muted-foreground">
              {view === "mine"
                ? "Nothing's assigned to you and due today. Check back tomorrow, or view everyone's list."
                : "No budget windows, renewals, call-backs, or follow-ups are due across the team right now."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-6">
          {orderedGroups.map(([ownerName, ownerItems]) => (
            <div key={ownerName} className="flex flex-col gap-3">
              {view === "all" && (
                <h2 className="text-sm font-bold text-foreground">
                  {ownerName} <span className="font-normal text-muted-foreground">({ownerItems.length})</span>
                </h2>
              )}
              <div className="flex flex-col gap-4">
                {ownerItems.map((item) => {
                  const kind = kindByName.get(item.kind);
                  if (!kind) return null;
                  return <ReviewItemCard key={item.id} item={item} kind={kind} />;
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
