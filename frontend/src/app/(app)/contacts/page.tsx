import Link from "next/link";
import { Download, Mail, Search, SlidersHorizontal, Upload, Users, X } from "lucide-react";
import { backendFetch } from "@/lib/backend";
import type { ContactListItem, Page } from "@/lib/types";
import { getPublicationFilter } from "@/lib/publication";
import { getSession } from "@/lib/session";
import { listPublications } from "@/lib/actions";
import { accessLabel, allowedSourceDbSlugs, resolveScope } from "@/lib/access";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ContactFormDialog } from "@/components/contact-form-dialog";
import { InteractiveContactTable } from "@/components/interactive-contact-table";
import { PublicationQuickFilter } from "@/components/publication-quick-filter";
import { AdvancedSearch } from "@/components/contacts/advanced-search";
import { parseConds } from "@/lib/search-conditions";
import { BulkUpdateDialog } from "@/components/contacts/bulk-update-dialog";
import { CopyEmailsButton } from "@/components/contacts/copy-emails-button";
import type { ContactField } from "@/lib/contact-tools-types";

const PAGE_SIZE = 50;

export default async function ContactsPage({
  searchParams,
}: {
  searchParams: Promise<{
    q?: string;
    page?: string;
    company?: string;
    city?: string;
    country?: string;
    title?: string;
    sort?: string;
    desc?: string;
    conds?: string;
    match?: string;
  }>;
}) {
  const sp = await searchParams;
  const { q, page: pageParam } = sp;
  const sort = sp.sort || "name";
  const desc = sp.desc === "1" || sp.desc === "true";
  // Act!-style lookup fields - each narrows the list further.
  const lookup = {
    company: sp.company?.trim() || "",
    city: sp.city?.trim() || "",
    country: sp.country?.trim() || "",
    title: sp.title?.trim() || "",
  };
  const conds = parseConds(sp.conds);
  const match = sp.match === "any" ? "any" : "all";
  const activeLookups = Object.values(lookup).filter(Boolean).length + (conds.length ? 1 : 0);
  const page = Math.max(1, Number(pageParam) || 1);
  const [rawSourceDb, session, allPublications, fields] = await Promise.all([
    getPublicationFilter(),
    getSession(),
    listPublications(),
    backendFetch<ContactField[]>("/api/contacts/fields").catch(() => [] as ContactField[]),
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
  for (const [k, v] of Object.entries(lookup)) if (v) params.set(k, v);
  if (conds.length) {
    params.set("conds", JSON.stringify(conds));
    if (match === "any") params.set("match", "any");
  }
  params.set("sort", sort);
  if (desc) params.set("desc", "true");

  const data = scope.source_db === "__no_access__"
    ? { items: [], total: 0, page: 1, page_size: PAGE_SIZE }
    : await backendFetch<Page<ContactListItem>>(`/api/contacts?${params}`);
  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  // Same filters as the list query above, minus pagination - carried onto
  // each row's link so the detail page's prev/next stepper walks this
  // exact filtered set (see InteractiveContactTable's `queryString` prop).
  // `filterParams` = what's being looked up (no sort/page) - shared by the
  // sort headers, "select all matching", export and mail merge.
  const filterParams: Record<string, string> = {};
  if (q) filterParams.q = q;
  if (source_db) filterParams.source_db = source_db;
  if (scope.group_id) filterParams.group_id = scope.group_id;
  for (const [k, v] of Object.entries(lookup)) if (v) filterParams[k] = v;
  if (conds.length) {
    filterParams.conds = JSON.stringify(conds);
    if (match === "any") filterParams.match = "any";
  }
  const rowQuery = new URLSearchParams(filterParams);
  if (sort !== "name") rowQuery.set("sort", sort);
  if (desc) rowQuery.set("desc", "true");
  const rowQueryString = rowQuery.toString();
  // Page links keep every filter and the sort.
  const pageHref = (n: number) => {
    const p = new URLSearchParams(filterParams);
    p.delete("source_db");
    p.delete("group_id");
    if (sort !== "name") p.set("sort", sort);
    if (desc) p.set("desc", "1");
    p.set("page", String(n));
    return `/contacts?${p}`;
  };
  const exportParams = new URLSearchParams(filterParams);
  exportParams.set("sort", sort);
  if (desc) exportParams.set("desc", "true");
  const mergeParams = new URLSearchParams({ source: "lookup", ...filterParams, sort });
  if (desc) mergeParams.set("desc", "1");
  // On the mail-merge page `company` means a company id - the lookup's
  // "company contains" text travels as company_name.
  if (lookup.company) {
    mergeParams.delete("company");
    mergeParams.set("company_name", lookup.company);
  }
  const lookupBits = [q, lookup.company, lookup.title, lookup.city, lookup.country, conds.length ? "advanced search" : ""].filter(Boolean);
  const lookupLabel = lookupBits.length ? `Lookup: ${lookupBits.join(", ")}` : "All contacts";
  const inputCls = "h-8 text-xs";

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
            {data.total.toLocaleString()} {q || activeLookups ? "contacts match this lookup" : "contacts across all titles"}
          </p>
          {scope.group_name && (
            <p className="mt-0.5 text-[11px] font-medium text-primary">
              Showing {accessLabel({ source_db, group_id: scope.group_id, group_name: scope.group_name })} only
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" nativeButton={false} render={<Link href="/contacts/import" />} title="Add contacts from an Excel sheet, CSV or PDF">
            <Upload className="size-3.5" />
            Import
          </Button>
          <CopyEmailsButton scope={{ ...filterParams, label: lookupLabel }} />
          <BulkUpdateDialog scope={{ ...filterParams, label: lookupLabel }} fields={fields} count={data.total} />
          <Button
            variant="outline"
            size="sm"
            nativeButton={false}
            render={<a href={`/api/files/contacts/export?${exportParams}`} download />}
            title="Download this lookup as an Excel sheet (up to 50,000 rows)"
          >
            <Download className="size-3.5" />
            Export
          </Button>
          <Button
            variant="outline"
            size="sm"
            nativeButton={false}
            render={<Link href={`/mail-merge?${mergeParams}`} />}
            title="Write to everyone in this lookup"
          >
            <Mail className="size-3.5" />
            Mail merge
          </Button>
          <ContactFormDialog defaultSourceDb={source_db} />
        </div>
      </div>

      {/* Lookup: Act!'s "Lookup > Company / City / Country / Title". Plain
          GET form, so every lookup is a shareable, bookmarkable URL. */}
      <form action="/contacts" className="rounded-lg border border-border bg-card p-3 shadow-2xs">
        <input type="hidden" name="sort" value={sort} />
        {desc && <input type="hidden" name="desc" value="1" />}
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-[2fr_1.3fr_1fr_1fr_1.3fr_auto]">
          <div className="relative col-span-2 sm:col-span-3 lg:col-span-1">
            <Search className="absolute left-2.5 top-2 size-3.5 text-muted-foreground" />
            <Input
              name="q"
              aria-label="Search"
              placeholder="Name, email, phone, address, company…"
              defaultValue={q ?? ""}
              className={`pl-8 ${inputCls}`}
            />
          </div>
          <Input name="company" aria-label="Company" placeholder="Company" defaultValue={lookup.company} className={inputCls} />
          <Input name="city" aria-label="City or town" placeholder="City / town" defaultValue={lookup.city} className={inputCls} />
          <Input name="country" aria-label="Country" placeholder="Country" defaultValue={lookup.country} className={inputCls} />
          <Input name="title" aria-label="Job title" placeholder="Job title" defaultValue={lookup.title} className={inputCls} />
          <div className="col-span-2 flex gap-1.5 sm:col-span-1">
            <Button type="submit" size="sm" className="h-8 flex-1 gap-1.5">
              <SlidersHorizontal className="size-3.5" />
              Look up
            </Button>
            {(q || activeLookups > 0) && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8"
                nativeButton={false}
                render={<Link href="/contacts" aria-label="Clear lookup" />}
              >
                <X className="size-3.5" />
              </Button>
            )}
          </div>
          <AdvancedSearch fields={fields} initial={conds} match={match} />
        </div>
        <p className="mt-2 text-[11px] text-muted-foreground">
          The search box looks in names, job titles, companies, emails, phone numbers, addresses and the custom fields - type several words in any order.
          The other boxes narrow it further. Click a column heading to sort; tick contacts to group, export, copy their emails or mail-merge them.
        </p>
      </form>

      {/* Publication Segmentation Strip - same global filter as the header
          switcher (lib/publication.ts); setting it here also applies to
          Companies, Groups and the Dashboard until changed back. */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <PublicationQuickFilter current={source_db} publications={publications} />
        <span className="text-xs text-muted-foreground">
          Tip: Click any contact to open their full record
        </span>
      </div>

      <InteractiveContactTable
        items={data.items}
        queryString={rowQueryString}
        filterParams={filterParams}
        sort={sort}
        desc={desc}
        total={data.total}
        sourceDb={source_db}
        lookupLabel={lookupLabel}
        fields={fields}
      />

      {/* Pagination Controls */}
      <div className="flex items-center justify-between text-xs text-muted-foreground pt-2">
        <span>
          Showing page {data.page} of {totalPages.toLocaleString()} ({data.total.toLocaleString()} total contacts)
        </span>
        <div className="flex gap-2">
          {page > 1 && (
            <Link
              className="rounded-md border border-border bg-card px-3 py-1.5 hover:bg-muted font-medium"
              href={pageHref(page - 1)}
            >
              &larr; Previous
            </Link>
          )}
          {page < totalPages && (
            <Link
              className="rounded-md border border-border bg-card px-3 py-1.5 hover:bg-muted font-medium"
              href={pageHref(page + 1)}
            >
              Next &rarr;
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
