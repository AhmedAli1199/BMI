import Link from "next/link";
import { backendFetch } from "@/lib/backend";
import type { GroupListItem, Page } from "@/lib/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { GroupFormDialog } from "@/components/group-form-dialog";

const PAGE_SIZE = 50;

export default async function GroupsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; page?: string }>;
}) {
  const { q, page: pageParam } = await searchParams;
  const page = Math.max(1, Number(pageParam) || 1);

  const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (q) params.set("q", q);

  const data = await backendFetch<Page<GroupListItem>>(`/api/groups?${params}`);
  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div className="flex w-full flex-col gap-4 p-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Groups</h1>
          <p className="text-sm text-muted-foreground">
            {data.total.toLocaleString()} total &middot; segments, lists and tags for contacts
          </p>
        </div>
        <div className="flex items-center gap-3">
          <form action="/groups" className="w-72">
            <Input name="q" placeholder="Search group name..." defaultValue={q ?? ""} />
          </form>
          <GroupFormDialog />
        </div>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Members</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.items.map((g) => (
              <TableRow key={g.id}>
                <TableCell>
                  <Link href={`/groups/${g.id}`} className="font-medium hover:underline">
                    {g.name}
                  </Link>
                </TableCell>
                <TableCell>{g.description || <span className="text-muted-foreground">—</span>}</TableCell>
                <TableCell>{g.member_count.toLocaleString()}</TableCell>
              </TableRow>
            ))}
            {data.items.length === 0 && (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-muted-foreground">
                  No groups yet.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

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
