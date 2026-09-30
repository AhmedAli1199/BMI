"use client";

import { createContext, useCallback, useContext, useMemo, useOptimistic, useTransition } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  type FilterDef,
  type FilterValue,
  type FilterValues,
  type SortState,
  parseFilters,
  parseSort,
  withChanges,
} from "@/lib/data-view/schema";

type Ctx = {
  defs: FilterDef[];
  values: FilterValues;
  sort: SortState;
  defaultSort: SortState;
  /** Facet counts per filter key -> option -> rows. */
  facets: Record<string, Record<string, number>>;
  params: URLSearchParams;
  update: (changes: Record<string, FilterValue>) => void;
  pending: boolean;
};

const DataViewContext = createContext<Ctx | null>(null);

export function useDataView(): Ctx {
  const ctx = useContext(DataViewContext);
  if (!ctx) throw new Error("useDataView must be used inside <DataView>");
  return ctx;
}

/** Owns a table's URL state. Every control inside (sidebar, chips, sort
 * headers, search, pagination) reads and writes through here, so they
 * always agree, and the table dims while the next result loads. */
export function DataView({
  defs,
  defaultSort,
  facets = {},
  shallow = false,
  children,
}: {
  defs: FilterDef[];
  defaultSort: SortState;
  facets?: Record<string, Record<string, number>>;
  /** Rows are filtered in the browser - change the URL without asking the server for the page again. */
  shallow?: boolean;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();
  const [pending, startTransition] = useTransition();
  // Controls reflect a click immediately; the URL (and results) follow.
  const [qs, setOptimisticQs] = useOptimistic(search.toString());
  const params = useMemo(() => new URLSearchParams(qs), [qs]);
  const values = useMemo(() => parseFilters(defs, params), [defs, params]);
  const sort = useMemo(() => parseSort(params, defaultSort), [params, defaultSort]);

  const update = useCallback(
    (changes: Record<string, FilterValue>) => {
      const next = withChanges(params, changes).toString();
      const url = next ? `${pathname}?${next}` : pathname;
      if (shallow) {
        window.history.replaceState(null, "", url);
        return;
      }
      startTransition(() => {
        setOptimisticQs(next);
        router.replace(url, { scroll: false });
      });
    },
    [params, pathname, router, shallow, setOptimisticQs]
  );

  const value = useMemo(
    () => ({ defs, values, sort, defaultSort, facets, params, update, pending }),
    [defs, values, sort, defaultSort, facets, params, update, pending]
  );
  return <DataViewContext.Provider value={value}>{children}</DataViewContext.Provider>;
}

/** Sidebar + results. Below `lg` the sidebar collapses to a "Filters"
 * button that opens it as a drawer (see FilterSidebar). */
export function DataViewLayout({ sidebar, children }: { sidebar: React.ReactNode; children: React.ReactNode }) {
  const { pending } = useDataView();
  return (
    <div className="grid items-start gap-5 lg:grid-cols-[16.5rem_minmax(0,1fr)]">
      {sidebar}
      <div
        className={`flex min-w-0 flex-col gap-3 transition-opacity duration-150 ${pending ? "pointer-events-none opacity-60" : ""}`}
        aria-busy={pending}
      >
        {children}
      </div>
    </div>
  );
}
