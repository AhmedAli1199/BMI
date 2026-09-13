import Link from "next/link";
import { Search, Users } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { ContactListItem, Page } from "@/lib/types";
import { getPublicationFilter } from "@/lib/publication";
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
  const source_db = await getPublicationFilter();

  const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (q) params.set("q", q);
  if (source_db) params.set("source_db", source_db);

  const data = await backendFetch<Page<ContactListItem>>(`/api/contacts?${params}`);
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
          <ContactFormDialog />
        </div>
      </div>

      {/* Publication Segmentation Strip - same global filter as the header
          switcher (lib/publication.ts); setting it here also applies to
          Companies, Groups and the Dashboard until changed back. */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <PublicationQuickFilter current={source_db} />
        <span className="text-xs text-muted-foreground">
          Tip: Click any contact to slide open quick inspection
        </span>
      </div>

      {/* Interactive Contact Table with Slide-Over Drawer */}
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
