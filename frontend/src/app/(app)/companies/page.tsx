import Link from "next/link";
import { backendFetch } from "@/lib/backend";
import type { CompanyListItem, Page } from "@/lib/types";
import { getPublicationFilter } from "@/lib/publication";
import { getSession } from "@/lib/session";
import { resolveScope } from "@/lib/access";
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
import { sourceBadgeStyle, sourceLabel } from "@/lib/sources";
import { CompanyFormDialog } from "@/components/company-form-dialog";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";

const PAGE_SIZE = 50;

export default async function CompaniesPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; page?: string }>;
}) {
  const { q, page: pageParam } = await searchParams;
  const page = Math.max(1, Number(pageParam) || 1);
  const [rawSourceDb, session] = await Promise.all([getPublicationFilter(), getSession()]);
  const scope = resolveScope(session, rawSourceDb);
  // Companies aren't group-scoped (a group is a contact-level concept -
  // see backend/app/models/user_access.py's docstring) - a group-scoped
  // session still only sees its assigned database's companies broadly,
  // not filtered down to the group's own contacts' companies.
  const source_db = scope.source_db === "__no_access__" ? "" : scope.source_db;

  const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (q) params.set("q", q);
  if (source_db) params.set("source_db", source_db);

  const data = scope.source_db === "__no_access__"
    ? { items: [], total: 0, page: 1, page_size: PAGE_SIZE }
    : await backendFetch<Page<CompanyListItem>>(`/api/companies?${params}`);
  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  // Same filters as the list query above, minus pagination - carried onto
  // each row's link so the detail page's prev/next stepper walks this
  // exact filtered set.
  const rowQuery = new URLSearchParams();
  if (q) rowQuery.set("q", q);
  if (source_db) rowQuery.set("source_db", source_db);
  const rowSuffix = rowQuery.toString() ? `?${rowQuery}` : "";

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6">
      <PageHeader
        section="Clients"
        title="Companies"
        description={`${data.total.toLocaleString()} ${q ? "companies match this search" : "accounts across every BMI title"}`}
        below={scope.group_name ? (
          <p className="text-[11px] font-medium" style={{ color: "var(--warn)" }}>
            Your access is limited to the &ldquo;{scope.group_name}&rdquo; group of contacts - companies aren&apos;t split by
            group, so this list shows every company in {sourceLabel(source_db)}.
          </p>
        ) : undefined}
        actions={<>
          <form action="/companies" className="w-64 sm:w-72">
            <Input name="q" aria-label="Search companies" placeholder="Search company name..." defaultValue={q ?? ""} className="h-9" />
          </form>
          <CompanyFormDialog defaultSourceDb={source_db} />
        </>}
      />

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
              <ClickableTableRow key={c.id} href={`/companies/${c.id}${rowSuffix}`}>
                <TableCell>
                  <Link href={`/companies/${c.id}${rowSuffix}`} className="flex items-center gap-3">
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
                  <Badge variant="outline" className={`text-[11px] font-medium ${sourceBadgeStyle(c.source_db)}`}>
                    {sourceLabel(c.source_db)}
                  </Badge>
                </TableCell>
              </ClickableTableRow>
            ))}
            {data.items.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="p-0">
                  <EmptyState compact mood="puzzled" title="No companies match">Try another title, or clear the search.</EmptyState>
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
