import Link from "next/link";
import { CornerDownRight, Users } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { GroupListItem, Page } from "@/lib/types";
import { getPublicationFilter } from "@/lib/publication";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { GroupFormDialog } from "@/components/group-form-dialog";
import { PublicationQuickFilter } from "@/components/publication-quick-filter";

const PAGE_SIZE = 50;

export default async function GroupsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; page?: string }>;
}) {
  const { q, page: pageParam } = await searchParams;
  const page = Math.max(1, Number(pageParam) || 1);
  const source_db = await getPublicationFilter();

  const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (q) params.set("q", q);
  if (source_db) params.set("source_db", source_db);

  const data = await backendFetch<Page<GroupListItem>>(`/api/groups?${params}`);
  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div className="flex w-full flex-col gap-5 p-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Groups</h1>
          <p className="text-sm text-muted-foreground">
            {data.total.toLocaleString()} segments, lists and tags for contacts
          </p>
        </div>
        <div className="flex items-center gap-3">
          <form action="/groups" className="w-72">
            <Input name="q" placeholder="Search group name..." defaultValue={q ?? ""} />
          </form>
          <GroupFormDialog />
        </div>
      </div>

      <PublicationQuickFilter current={source_db} />

      {/* Act!'s groups are hierarchical (62 top-level groups + 183
          sub-groups in OnBoard alone) - a single indented list makes that
          structure legible; a wrapping card grid can't keep a parent and
          its children visually together. The backend already orders rows
          by hier_path so a page's rows come out parent-then-children. */}
      {data.items.length > 0 ? (
        <Card className="editorial-card overflow-hidden p-0">
          <div className="flex flex-col divide-y divide-border/70">
            {data.items.map((g) => {
              const isSubgroup = (g.hier_level ?? 0) > 0;
              return (
                <Link
                  key={g.id}
                  href={`/groups/${g.id}`}
                  className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-accent/40"
                  style={isSubgroup ? { paddingLeft: `${16 + (g.hier_level ?? 1) * 24}px` } : undefined}
                >
                  {isSubgroup && (
                    <CornerDownRight className="size-3.5 shrink-0 text-muted-foreground" />
                  )}
                  <div className="min-w-0 flex-1">
                    <div className={`truncate font-semibold ${isSubgroup ? "text-sm text-foreground/90" : "text-base text-foreground"}`}>
                      {g.name}
                    </div>
                    {g.description && (
                      <p className="truncate text-xs text-muted-foreground">{g.description}</p>
                    )}
                  </div>
                  <span className="flex shrink-0 items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground">
                    <Users className="size-3.5" />
                    {g.member_count.toLocaleString()}
                  </span>
                </Link>
              );
            })}
          </div>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No groups yet — create one to start segmenting contacts.
          </CardContent>
        </Card>
      )}

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          Page {data.page} of {totalPages.toLocaleString()}
        </span>
        <div className="flex gap-2">
          {page > 1 && (
            <Link
              className="rounded border px-3 py-1 hover:bg-muted"
              href={`/groups?${new URLSearchParams({ ...(q ? { q } : {}), page: String(page - 1) })}`}
            >
              Previous
            </Link>
          )}
          {page < totalPages && (
            <Link
              className="rounded border px-3 py-1 hover:bg-muted"
              href={`/groups?${new URLSearchParams({ ...(q ? { q } : {}), page: String(page + 1) })}`}
            >
              Next
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
