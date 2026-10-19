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
  searchParams: Promise<{ q?: string; page?: string; missing?: string }>;
}) {
  const { q, page: pageParam, missing: missingParam } = await searchParams;
  // Data Health's "Fix" link for companies without an industry.
  const missing = missingParam === "industry" ? "industry" : "";
  const page = Math.max(1, Number(pageParam) || 1);
  const [rawSourceDb, session] = await Promise.all([getPublicationFilter(), getSession()]);
  const scope = resolveScope(session, rawSourceDb);
  // A group-limited session only sees the companies its group's contacts
  // work for - the backend applies that (core/visibility.py company_clause).
  const source_db = scope.source_db === "__no_access__" ? "" : scope.source_db;

  const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (q) params.set("q", q);
  if (source_db) params.set("source_db", source_db);
  if (missing) params.set("missing", missing);

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
  if (missing) rowQuery.set("missing", missing);
  const rowSuffix = rowQuery.toString() ? `?${rowQuery}` : "";

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6">
      <PageHeader
        section="Clients"
        title="Companies"
        description={`${data.total.toLocaleString()} ${q || missing ? "companies match" : "accounts across every BMI title"}`}
        below={scope.group_name || missing ? (
          <div className="flex flex-col gap-1">
            {missing && (
              <p className="text-[11px] font-medium text-muted-foreground">
                Showing only companies without an industry.{" "}
                <Link href={`/companies${q ? `?${new URLSearchParams({ q })}` : ""}`} className="font-semibold text-primary hover:underline">
                  Show all companies
                </Link>
              </p>
            )}
            {scope.group_name && (
              <p className="text-[11px] font-medium" style={{ color: "var(--warn)" }}>
                Your access is limited to the &ldquo;{scope.group_name}&rdquo; group of contacts, so this list shows only the
                companies those contacts work for.
              </p>
            )}
          </div>
        ) : undefined}
        actions={<>
          <form action="/companies" className="w-64 sm:w-72">
            {missing && <input type="hidden" name="missing" value={missing} />}
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
              href={`/companies?${new URLSearchParams({ ...(q ? { q } : {}), ...(missing ? { missing } : {}), page: String(page - 1) })}`}
            >
              Previous
            </Link>
          )}
          {page < totalPages && (
            <Link
              className="rounded border px-3 py-1 hover:bg-muted"
              href={`/companies?${new URLSearchParams({ ...(q ? { q } : {}), ...(missing ? { missing } : {}), page: String(page + 1) })}`}
            >
              Next
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
