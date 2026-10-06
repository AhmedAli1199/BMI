"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { ArrowDown, ArrowUp, ArrowUpDown, Building2, MapPin } from "lucide-react";
import { toast } from "sonner";
import type { ContactListItem } from "@/lib/types";
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
import { Badge } from "@/components/ui/badge";
import { ContactSelectionActions } from "@/components/contact-selection-actions";
import type { ContactField } from "@/lib/contact-tools-types";
import { lookupContactIds } from "@/lib/messaging-actions";
import { sourceLabel, sourceBadgeStyle as publicationBadgeStyle } from "@/lib/sources";

type SortKey = "name" | "first_name" | "company" | "city" | "country" | "title" | "email" | "added";

function SortHead({
  k,
  sort,
  desc,
  href,
  children,
  className,
}: {
  k: SortKey;
  sort: string;
  desc: boolean;
  href: string;
  children: React.ReactNode;
  className?: string;
}) {
  const active = sort === k;
  const Icon = active ? (desc ? ArrowDown : ArrowUp) : ArrowUpDown;
  return (
    <TableHead className={className} aria-sort={active ? (desc ? "descending" : "ascending") : "none"}>
      <Link
        href={href}
        scroll={false}
        className={`inline-flex items-center gap-1 hover:text-foreground ${active ? "text-foreground" : ""}`}
      >
        {children}
        <Icon className={`size-3 ${active ? "opacity-100" : "opacity-40"}`} />
      </Link>
    </TableHead>
  );
}

/** The contacts lookup. Click a row to open the record; tick rows (or
 * "select all N matching") to add them to a group, start a new group,
 * export or mail-merge them. Column headers sort (click again to reverse). */
export function InteractiveContactTable({
  items,
  queryString,
  filterParams = {},
  sort = "name",
  desc = false,
  total,
  sourceDb,
  lookupLabel = "Current lookup",
  fields,
}: {
  items: ContactListItem[];
  /** Current filters + sort, carried onto each row's link so the detail
   * page's record-stepper (prev/next) walks this exact list. */
  queryString?: string;
  /** Current filters without sort/page - the base for sort links and "select all". */
  filterParams?: Record<string, string>;
  sort?: string;
  desc?: boolean;
  total?: number;
  sourceDb?: string;
  lookupLabel?: string;
  fields?: ContactField[];
}) {
  const suffix = queryString ? `?${queryString}` : "";
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [allMatching, setAllMatching] = useState(false);
  const [pending, startTransition] = useTransition();

  const pageIds = items.map((c) => c.id);
  const pageAllSelected = pageIds.length > 0 && pageIds.every((id) => selected.has(id));

  function toggle(id: string) {
    setAllMatching(false);
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function togglePage() {
    setAllMatching(false);
    setSelected((prev) => {
      const next = new Set(prev);
      if (pageAllSelected) pageIds.forEach((id) => next.delete(id));
      else pageIds.forEach((id) => next.add(id));
      return next;
    });
  }

  function selectAllMatching() {
    startTransition(async () => {
      try {
        const ids = await lookupContactIds(filterParams);
        setSelected(new Set(ids));
        setAllMatching(true);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Couldn't select them all");
      }
    });
  }

  function sortHref(key: SortKey) {
    const p = new URLSearchParams(filterParams);
    p.set("sort", key);
    if (sort === key && !desc) p.set("desc", "1");
    return `/contacts?${p}`;
  }

  const selectedIds = [...selected];
  const moreAvailable = total !== undefined && total > items.length && pageAllSelected && !allMatching;

  return (
    <div className="flex flex-col gap-3">
      {selected.size > 0 && (
        <ContactSelectionActions
          ids={selectedIds}
          onClear={() => {
            setSelected(new Set());
            setAllMatching(false);
          }}
          sourceDb={sourceDb}
          fields={fields}
          label={allMatching ? lookupLabel : `${lookupLabel} – ${selected.size} selected`}
        >
          {moreAvailable && (
            <button
              type="button"
              onClick={selectAllMatching}
              disabled={pending}
              className="text-xs font-semibold text-primary underline-offset-2 hover:underline"
            >
              {pending ? "Selecting…" : `Select all ${total!.toLocaleString()} matching`}
            </button>
          )}
          {allMatching && <span className="text-xs text-muted-foreground">(every contact in this lookup)</span>}
        </ContactSelectionActions>
      )}

      <div className="overflow-x-auto rounded-lg border border-border bg-card shadow-2xs">
        <Table>
          <TableHeader className="bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-9">
                <input
                  type="checkbox"
                  className="size-3.5 accent-primary"
                  checked={pageAllSelected}
                  onChange={togglePage}
                  aria-label="Select every contact on this page"
                />
              </TableHead>
              <SortHead k="name" sort={sort} desc={desc} href={sortHref("name")} className="w-[30%] py-3">Contact &amp; Title</SortHead>
              <SortHead k="company" sort={sort} desc={desc} href={sortHref("company")} className="w-[24%]">Company</SortHead>
              <SortHead k="city" sort={sort} desc={desc} href={sortHref("city")} className="w-[16%]">Location</SortHead>
              <SortHead k="email" sort={sort} desc={desc} href={sortHref("email")} className="w-[20%]">Email</SortHead>
              <TableHead className="w-[10%]">Publication</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((c) => {
              const name =
                c.full_name ||
                [c.first_name, c.last_name].filter(Boolean).join(" ") ||
                "(no name)";
              const place = [c.city, c.country].filter(Boolean).join(", ");
              const checked = selected.has(c.id);

              return (
                <ClickableTableRow
                  key={c.id}
                  href={`/contacts/${c.id}${suffix}`}
                  className={`group hover:bg-accent/40 ${checked ? "bg-primary/5" : ""}`}
                >
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      className="size-3.5 accent-primary"
                      checked={checked}
                      onChange={() => toggle(c.id)}
                      aria-label={`Select ${name}`}
                    />
                  </TableCell>
                  <TableCell className="py-3">
                    <Link href={`/contacts/${c.id}${suffix}`} className="flex items-center gap-3">
                      <EntityAvatar
                        name={name}
                        className="size-8.5 text-xs font-medium border border-border shrink-0"
                      />
                      <div className="min-w-0">
                        <div className="font-semibold text-foreground group-hover:text-primary transition-colors truncate">
                          {name}
                        </div>
                        {c.job_title && (
                          <div className="truncate text-xs text-muted-foreground">
                            {c.job_title}
                          </div>
                        )}
                      </div>
                    </Link>
                  </TableCell>

                  <TableCell>
                    {c.company_name ? (
                      <span className="flex items-center gap-1.5 text-xs font-medium text-foreground">
                        <Building2 className="size-3 text-muted-foreground shrink-0" />
                        <span className="truncate">{c.company_name}</span>
                      </span>
                    ) : (
                      <span className="text-muted-foreground text-xs">—</span>
                    )}
                  </TableCell>

                  <TableCell>
                    {place ? (
                      <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <MapPin className="size-3 shrink-0" />
                        <span className="truncate">{place}</span>
                      </span>
                    ) : (
                      <span className="text-muted-foreground text-xs">—</span>
                    )}
                  </TableCell>

                  <TableCell>
                    {c.primary_email ? (
                      <span className="text-xs font-mono text-muted-foreground truncate block max-w-[220px]">
                        {c.primary_email}
                      </span>
                    ) : (
                      <span className="text-muted-foreground text-xs">—</span>
                    )}
                  </TableCell>

                  <TableCell>
                    <Badge
                      variant="outline"
                      className={`text-[11px] font-medium ${publicationBadgeStyle(c.source_db)}`}
                    >
                      {sourceLabel(c.source_db)}
                    </Badge>
                  </TableCell>
                </ClickableTableRow>
              );
            })}

            {items.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-12 text-center text-sm text-muted-foreground">
                  No contacts match this lookup. Try fewer filters.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
