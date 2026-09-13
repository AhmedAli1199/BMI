import Link from "next/link";
import { Search, Sparkles, Users } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { ContactListItem, Page } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { sourceLabel } from "@/lib/sources";
import { ContactFormDialog } from "@/components/contact-form-dialog";
import { InteractiveContactTable } from "@/components/interactive-contact-table";

const PAGE_SIZE = 50;

export default async function ContactsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; page?: string; source_db?: string }>;
}) {
  const { q, page: pageParam, source_db } = await searchParams;
  const page = Math.max(1, Number(pageParam) || 1);

  const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (q) params.set("q", q);
  if (source_db) params.set("source_db", source_db);

  const data = await backendFetch<Page<ContactListItem>>(`/api/contacts?${params}`);
  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  const filterLink = (nextSource: string | undefined) => {
    const p = new URLSearchParams({ ...(q ? { q } : {}) });
    if (nextSource) p.set("source_db", nextSource);
    return `/contacts${p.toString() ? `?${p}` : ""}`;
  };

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 sm:p-6">
      {/* Editorial Title & Quick Actions Header */}
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/80 pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-primary uppercase tracking-wider mb-1">
            <Users className="size-3.5" />
            <span>Master Directory</span>
          </div>
          <h1 className="editorial-title text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            Publishing &amp; Sales Contacts
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-1">
            {data.total.toLocaleString()} media buyers, advertisers &amp; editorial contributors across all titles
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

      {/* Publication Segmentation Strip */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Link href={filterLink(undefined)}>
            <Badge
              variant={!source_db ? "default" : "outline"}
              className="cursor-pointer text-xs font-medium px-3 py-1"
            >
              All Titles
            </Badge>
          </Link>
          <Link href={filterLink("onboard")}>
            <Badge
              variant={source_db === "onboard" ? "default" : "outline"}
              className={`cursor-pointer text-xs font-medium px-3 py-1 ${
                source_db === "onboard" ? "bg-blue-600 text-white hover:bg-blue-700" : ""
              }`}
            >
              Onboard Hospitality
            </Badge>
          </Link>
          <Link href={filterLink("sellingtravel")}>
            <Badge
              variant={source_db === "sellingtravel" ? "default" : "outline"}
              className={`cursor-pointer text-xs font-medium px-3 py-1 ${
                source_db === "sellingtravel" ? "bg-emerald-600 text-white hover:bg-emerald-700" : ""
              }`}
            >
              Selling Travel
            </Badge>
          </Link>
          <Link href={filterLink("prospects")}>
            <Badge
              variant={source_db === "prospects" ? "default" : "outline"}
              className={`cursor-pointer text-xs font-medium px-3 py-1 ${
                source_db === "prospects" ? "bg-amber-600 text-white hover:bg-amber-700" : ""
              }`}
            >
              Prospects DB
            </Badge>
          </Link>
        </div>

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
              href={`/contacts?${new URLSearchParams({ ...(q ? { q } : {}), ...(source_db ? { source_db } : {}), page: String(page - 1) })}`}
            >
              &larr; Previous
            </Link>
          )}
          {page < totalPages && (
            <Link
              className="rounded-md border border-border bg-card px-3 py-1.5 hover:bg-muted font-medium"
              href={`/contacts?${new URLSearchParams({ ...(q ? { q } : {}), ...(source_db ? { source_db } : {}), page: String(page + 1) })}`}
            >
              Next &rarr;
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
