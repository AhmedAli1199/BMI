import Link from "next/link";
import { backendFetch } from "@/lib/backend";
import type { CompanyListItem, Page } from "@/lib/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ClickableTableRow } from "@/components/clickable-table-row";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { CompanyFormDialog } from "@/components/company-form-dialog";

const PAGE_SIZE = 50;

export default async function CompaniesPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; page?: string }>;
}) {
  const { q, page: pageParam } = await searchParams;
  const page = Math.max(1, Number(pageParam) || 1);

  const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (q) params.set("q", q);

  const data = await backendFetch<Page<CompanyListItem>>(`/api/companies?${params}`);
  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div className="flex w-full flex-col gap-4 p-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Companies</h1>
          <p className="text-sm text-muted-foreground">
            {data.total.toLocaleString()} total, across all three source databases
          </p>
        </div>
        <div className="flex items-center gap-3">
          <form action="/companies" className="w-72">
            <Input name="q" placeholder="Search company name..." defaultValue={q ?? ""} />
          </form>
          <CompanyFormDialog />
        </div>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Industry</TableHead>
              <TableHead>Contacts</TableHead>
              <TableHead>Source</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.items.map((c) => (
              <ClickableTableRow key={c.id} href={`/companies/${c.id}`}>
                <TableCell>
                  <Link href={`/companies/${c.id}`} className="font-medium hover:underline">
                    {c.name || "(no name)"}
                  </Link>
                </TableCell>
                <TableCell>{c.industry || <span className="text-muted-foreground">—</span>}</TableCell>
                <TableCell>{c.contact_count.toLocaleString()}</TableCell>
                <TableCell>
                  <Badge variant="secondary">{c.source_db}</Badge>
                </TableCell>
              </ClickableTableRow>
            ))}
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
              href={`/companies?${new URLSearchParams({ ...(q ? { q } : {}), page: String(page - 1) })}`}
            >
              Previous
            </Link>
          )}
          {page < totalPages && (
            <Link
              className="rounded border px-3 py-1 hover:bg-muted"
              href={`/companies?${new URLSearchParams({ ...(q ? { q } : {}), page: String(page + 1) })}`}
            >
              Next
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
