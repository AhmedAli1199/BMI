import Link from "next/link";
import { Users } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { GroupListItem, Page } from "@/lib/types";
import { getPublicationFilter } from "@/lib/publication";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

      {/* Groups tend to be few and meaningful (a segment, a mailing list) -
          tiles you can scan read better here than a table with two mostly-
          empty columns would. */}
      {data.items.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.items.map((g) => (
            <Link key={g.id} href={`/groups/${g.id}`}>
              <Card className="h-full transition-colors hover:border-primary/40 hover:bg-accent/40">
                <CardHeader className="flex-row items-start justify-between gap-2 space-y-0">
                  <CardTitle className="text-base font-semibold">{g.name}</CardTitle>
                  <span className="flex shrink-0 items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground">
                    <Users className="size-3.5" />
                    {g.member_count.toLocaleString()}
                  </span>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {g.description || "No description."}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
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
