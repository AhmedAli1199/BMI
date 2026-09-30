import Link from "next/link";
import { backendFetch } from "@/lib/backend";
import type { CompanyListItem, Page } from "@/lib/types";
import { getPublicationFilter } from "@/lib/publication";
import { getSession } from "@/lib/session";
import { listPublications } from "@/lib/actions";
import { allowedSourceDbSlugs, resolveScope } from "@/lib/access";
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
import { PublicationQuickFilter } from "@/components/publication-quick-filter";

const PAGE_SIZE = 50;

export default async function CompaniesPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; page?: string }>;
}) {
  const { q, page: pageParam } = await searchParams;
  const page = Math.max(1, Number(pageParam) || 1);
  const [rawSourceDb, session, allPublications] = await Promise.all([
    getPublicationFilter(),
    getSession(),
    listPublications(),
  ]);
  const scope = resolveScope(session, rawSourceDb);
  // Companies aren't group-scoped (a group is a contact-level concept -
  // see backend/app/models/user_access.py's docstring) - a group-scoped
  // session still only sees its assigned database's companies broadly,
  // not filtered down to the group's own contacts' companies.
  const source_db = scope.source_db === "__no_access__" ? "" : scope.source_db;
  const publications = session?.role === "admin"
    ? allPublications
    : allPublications.filter((p) => allowedSourceDbSlugs(session).includes(p.slug));

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
    <div className="flex w-full flex-col gap-5 p-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Companies</h1>
          <p className="text-sm text-muted-foreground">
            {data.total.toLocaleString()} accounts across every BMI title
          </p>
          {scope.group_name && (
            <p className="mt-0.5 text-[11px] font-medium text-amber-600">
              Your access is scoped to the &ldquo;{scope.group_name}&rdquo; group of contacts - companies aren&apos;t
              group-scoped, so this list shows all of {source_db}.
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          <form action="/companies" className="w-72">
            <Input name="q" placeholder="Search company name..." defaultValue={q ?? ""} />
          </form>
          <CompanyFormDialog defaultSourceDb={source_db} />
        </div>
      </div>

      <PublicationQuickFilter current={source_db} publications={publications} />

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
