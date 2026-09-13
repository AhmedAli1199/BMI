import Link from "next/link";
import { backendFetch } from "@/lib/backend";
import type { CompanyListItem, Page } from "@/lib/types";
import { getPublicationFilter } from "@/lib/publication";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ClickableTableRow } from "@/components/clickable-table-row";
import { EntityAvatar } from "@/components/entity-avatar";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { sourceLabel } from "@/lib/sources";
import { CompanyFormDialog } from "@/components/company-form-dialog";
import { PublicationQuickFilter } from "@/components/publication-quick-filter";

const PAGE_SIZE = 50;

export default async function CompaniesPage({
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

  const data = await backendFetch<Page<CompanyListItem>>(`/api/companies?${params}`);
  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div className="flex w-full flex-col gap-5 p-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Companies</h1>
          <p className="text-sm text-muted-foreground">
            {data.total.toLocaleString()} accounts across every BMI title
          </p>
        </div>
        <div className="flex items-center gap-3">
          <form action="/companies" className="w-72">
            <Input name="q" placeholder="Search company name..." defaultValue={q ?? ""} />
          </form>
          <CompanyFormDialog />
        </div>
      </div>

      <PublicationQuickFilter current={source_db} />

      <div className="overflow-hidden rounded-lg border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Company</TableHead>
              <TableHead>Industry</TableHead>
              <TableHead>Contacts</TableHead>
              <TableHead>Source</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.items.map((c) => (
              <ClickableTableRow key={c.id} href={`/companies/${c.id}`}>
                <TableCell>
                  <Link href={`/companies/${c.id}`} className="flex items-center gap-3">
                    <EntityAvatar name={c.name || "(no name)"} square />
                    <span className="font-medium hover:underline">{c.name || "(no name)"}</span>
                  </Link>
                </TableCell>
                <TableCell>{c.industry || <span className="text-muted-foreground">—</span>}</TableCell>
                <TableCell>
                  {c.contact_count > 0 ? (
                    c.contact_count.toLocaleString()
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </TableCell>
                <TableCell>
                  <Badge variant="secondary">{sourceLabel(c.source_db)}</Badge>
                </TableCell>
              </ClickableTableRow>
            ))}
            {data.items.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="py-10 text-center text-sm text-muted-foreground">
                  No companies match this view.
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
