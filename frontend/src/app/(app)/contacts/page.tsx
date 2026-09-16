import Link from "next/link";
import { Search, Users } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { ContactListItem, Page } from "@/lib/types";
import { getPublicationFilter } from "@/lib/publication";
import { getSession } from "@/lib/session";
import { listPublications } from "@/lib/actions";
import { accessLabel, allowedSourceDbSlugs, resolveScope } from "@/lib/access";
import { Input } from "@/components/ui/input";
import { ContactFormDialog } from "@/components/contact-form-dialog";
import { InteractiveContactTable } from "@/components/interactive-contact-table";
import { PublicationQuickFilter } from "@/components/publication-quick-filter";

const PAGE_SIZE = 50;

export default async function ContactsPage({
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
  const source_db = scope.source_db === "__no_access__" ? "" : scope.source_db;
  const publications = session?.role === "admin"
    ? allPublications
    : allPublications.filter((p) => allowedSourceDbSlugs(session).includes(p.slug));

  const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (q) params.set("q", q);
  if (source_db) params.set("source_db", source_db);
  if (scope.group_id) params.set("group_id", scope.group_id);

  const data = scope.source_db === "__no_access__"
    ? { items: [], total: 0, page: 1, page_size: PAGE_SIZE }
    : await backendFetch<Page<ContactListItem>>(`/api/contacts?${params}`);
  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6">
      {/* Editorial Title & Quick Actions Header */}
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/80 pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-primary uppercase tracking-wider mb-1">
            <Users className="size-3.5" />
            <span>Contacts</span>
          </div>
          <h1 className="editorial-title text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            Contacts
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-1">
            {data.total.toLocaleString()} contacts across all titles
          </p>
          {scope.group_name && (
            <p className="mt-0.5 text-[11px] font-medium text-primary">
              Showing {accessLabel({ source_db, group_id: scope.group_id, group_name: scope.group_name })} only
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <form action="/contacts" className="relative w-64 sm:w-72">
            <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
            <Input
              name="q"
              placeholder="Search by name, company, email..."
              defaultValue={q ?? ""}
              className="pl-8 h-9 text-xs"
            />
          </form>
          <ContactFormDialog defaultSourceDb={source_db} />
        </div>
      </div>

      {/* Publication Segmentation Strip - same global filter as the header
          switcher (lib/publication.ts); setting it here also applies to
          Companies, Groups and the Dashboard until changed back. */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <PublicationQuickFilter current={source_db} publications={publications} />
        <span className="text-xs text-muted-foreground">
          Tip: Click any contact to open their full record
        </span>
      </div>

      <InteractiveContactTable items={data.items} />

      {/* Pagination Controls */}
      <div className="flex items-center justify-between text-xs text-muted-foreground pt-2">
        <span>
          Showing page {data.page} of {totalPages.toLocaleString()} ({data.total.toLocaleString()} total contacts)
        </span>
        <div className="flex gap-2">
          {page > 1 && (
            <Link
              className="rounded-md border border-border bg-card px-3 py-1.5 hover:bg-muted font-medium"
              href={`/contacts?${new URLSearchParams({ ...(q ? { q } : {}), page: String(page - 1) })}`}
            >
              &larr; Previous
            </Link>
          )}
          {page < totalPages && (
            <Link
              className="rounded-md border border-border bg-card px-3 py-1.5 hover:bg-muted font-medium"
              href={`/contacts?${new URLSearchParams({ ...(q ? { q } : {}), page: String(page + 1) })}`}
            >
              Next &rarr;
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
