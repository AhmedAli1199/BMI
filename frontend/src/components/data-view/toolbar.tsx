"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, Download, Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useDataView } from "@/components/data-view/data-view";
import { chips, paramKeys } from "@/lib/data-view/schema";

/** The table's main search box (the def with kind "search"). Updates the
 * URL 350ms after typing stops, so results follow as you type without a
 * reload per keystroke. */
export function DataSearch({ className = "" }: { className?: string }) {
  const { defs, values, update } = useDataView();
  const def = defs.find((d) => d.kind === "search");
  const current = def ? ((values[def.key] as string | undefined) ?? "") : "";
  const [draft, setDraft] = useState(current);
  const [seen, setSeen] = useState(current);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  if (current !== seen) {
    // Changed from outside (a chip removed, Back pressed) - follow it.
    setSeen(current);
    setDraft(current);
  }
  useEffect(() => () => clearTimeout(timer.current), []);
  if (!def || def.kind !== "search") return null;

  function change(v: string) {
    setDraft(v);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => update({ [def!.key]: v.trim() || undefined }), 350);
  }

  return (
    <div role="search" className={`relative min-w-48 flex-1 ${className}`}>
      <Search className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
      <Input
        type="search"
        value={draft}
        onChange={(e) => change(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            clearTimeout(timer.current);
            update({ [def.key]: draft.trim() || undefined });
          }
        }}
        placeholder={def.placeholder ?? "Search…"}
        aria-label={def.label}
        className="h-9 pl-8 text-sm"
      />
      {draft && (
        <button
          type="button"
          onClick={() => {
            clearTimeout(timer.current);
            setDraft("");
            update({ [def.key]: undefined });
          }}
          className="absolute top-1/2 right-2 -translate-y-1/2 rounded p-0.5 text-muted-foreground hover:text-foreground"
          aria-label="Clear search"
        >
          <X className="size-3.5" />
        </button>
      )}
    </div>
  );
}

/** Removable chips for every active filter, plus "Clear all". */
export function FilterChips() {
  const { defs, values, update } = useDataView();
  const list = chips(defs, values);
  if (list.length === 0) return null;
  const clearAll = Object.fromEntries(
    defs.filter((d) => !(d.kind === "single" && d.required)).flatMap((d) => paramKeys(d).map((k) => [k, undefined]))
  );
  return (
    <div className="flex flex-wrap items-center gap-1.5" aria-label="Active filters">
      {list.map((c) => (
        <span key={c.id} className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/5 py-0.5 pr-1 pl-2.5 text-xs font-medium text-foreground">
          {c.label}
          <button type="button" onClick={() => update(c.clear)} className="rounded-full p-0.5 text-muted-foreground hover:bg-primary/10 hover:text-foreground" aria-label={`Remove ${c.label}`}>
            <X className="size-3" />
          </button>
        </span>
      ))}
      {list.length > 1 && (
        <button type="button" onClick={() => update(clearAll)} className="px-1 text-xs font-semibold text-muted-foreground hover:text-foreground">
          Clear all
        </button>
      )}
    </div>
  );
}

/** A column header that sorts by `sortKey`: first click uses the column's
 * natural direction (`firstDir` - newest/highest first for dates and
 * money), the next click reverses it. */
export function SortableTh({
  sortKey,
  children,
  firstDir = "asc",
  align = "left",
  className = "",
}: {
  sortKey: string;
  children: React.ReactNode;
  firstDir?: "asc" | "desc";
  align?: "left" | "right";
  className?: string;
}) {
  const { sort, update } = useDataView();
  const active = sort.key === sortKey;
  const Icon = active ? (sort.dir === "asc" ? ArrowUp : ArrowDown) : ArrowUpDown;
  const next = active ? (sort.dir === "asc" ? "desc" : "asc") : firstDir;
  return (
    <th
      scope="col"
      aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
      className={`px-3 py-2.5 font-semibold ${align === "right" ? "text-right" : "text-left"} ${className}`}
    >
      <button
        type="button"
        onClick={() => update({ sort: sortKey, dir: next })}
        className={`group/sort inline-flex items-center gap-1 rounded transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring ${active ? "text-foreground" : ""} ${align === "right" ? "flex-row-reverse" : ""}`}
      >
        {children}
        <Icon className={`size-3 shrink-0 transition-opacity ${active ? "opacity-100" : "opacity-30 group-hover/sort:opacity-70"}`} aria-hidden="true" />
      </button>
    </th>
  );
}

/** "1–100 of 2,954" with previous/next, and page size. */
export function Pagination({ total, pageSize, sizes = [50, 100, 250] }: { total: number; pageSize: number; sizes?: number[] }) {
  const { params, update } = useDataView();
  const page = Math.max(1, Number(params.get("page")) || 1);
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (total <= sizes[0]) return null;
  const first = (page - 1) * pageSize + 1;
  const last = Math.min(total, page * pageSize);
  return (
    <nav aria-label="Pages" className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
      <label className="flex items-center gap-1.5">
        Rows per page
        <select
          value={pageSize}
          onChange={(e) => update({ size: e.target.value, page: undefined })}
          className="h-7 rounded-md border border-input bg-background px-1.5 text-xs text-foreground"
        >
          {sizes.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </label>
      <div className="flex items-center gap-2">
        <span className="tabular-nums">
          {first.toLocaleString("en-GB")}–{last.toLocaleString("en-GB")} of {total.toLocaleString("en-GB")}
        </span>
        <Button size="icon-sm" variant="outline" disabled={page <= 1} onClick={() => update({ page: page > 2 ? String(page - 1) : undefined })} aria-label="Previous page">
          <ChevronLeft className="size-4" />
        </Button>
        <span className="tabular-nums">
          Page {page} of {pages.toLocaleString("en-GB")}
        </span>
        <Button size="icon-sm" variant="outline" disabled={page >= pages} onClick={() => update({ page: String(page + 1) })} aria-label="Next page">
          <ChevronRight className="size-4" />
        </Button>
      </div>
    </nav>
  );
}

/** Downloads exactly the filtered, sorted rows as .xlsx. */
export function ExportButton({ href, label = "Export" }: { href: string; label?: string }) {
  return (
    <Button variant="outline" size="sm" className="h-9 gap-1.5" nativeButton={false} render={<a href={href} download />} title="Download these rows as an Excel sheet">
      <Download className="size-3.5" aria-hidden="true" />
      {label}
    </Button>
  );
}
